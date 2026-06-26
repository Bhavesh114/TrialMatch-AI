"""
TrialMatch AI Criteria Extraction Service

Handles Stage 1 of screening: extracting structured eligibility criteria from protocol text.

Uses Claude API with specialized prompts to:
1. Parse protocol text for criteria
2. Identify criterion type (inclusion/exclusion)
3. Detect compound logic (AND/OR conditions)
4. Assign data point requirements
5. Calculate confidence scores
6. Cache results for repeated requests
"""

import logging
import hashlib
import time
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta

from anthropic import Anthropic, APIError, RateLimitError

from ..config import config
from ..models.criteria import CriterionModel, CriteriaExtractionResult, CriterionType, ExtractionWarning
from ..prompts.extraction import (
    EXTRACTION_SYSTEM_PROMPT,
    build_extraction_user_prompt,
    parse_extraction_response
)


logger = logging.getLogger(__name__)


# ============================================================================
# SIMPLE IN-MEMORY CACHE
# ============================================================================

class ExtractionCache:
    """
    Simple in-memory cache for extracted criteria.
    Keyed by protocol hash. Expires after configured TTL.
    """

    def __init__(self, ttl_minutes: int = 1440):
        """
        Initialize cache.

        Args:
            ttl_minutes: Time-to-live for cache entries in minutes
        """
        self.cache = {}
        self.ttl_minutes = ttl_minutes

    def get(self, protocol_hash: str) -> Optional[CriteriaExtractionResult]:
        """
        Retrieve cached extraction result.

        Args:
            protocol_hash: Hash of protocol text

        Returns:
            Cached result or None if not found/expired
        """
        if protocol_hash not in self.cache:
            return None

        entry, timestamp = self.cache[protocol_hash]
        age_minutes = (datetime.utcnow() - timestamp).total_seconds() / 60

        if age_minutes > self.ttl_minutes:
            del self.cache[protocol_hash]
            logger.debug(f"Cache entry expired for {protocol_hash}")
            return None

        logger.debug(f"Cache hit for {protocol_hash}")
        return entry

    def set(self, protocol_hash: str, result: CriteriaExtractionResult) -> None:
        """
        Store extraction result in cache.

        Args:
            protocol_hash: Hash of protocol text
            result: Extraction result to cache
        """
        self.cache[protocol_hash] = (result, datetime.utcnow())
        logger.debug(f"Cached extraction result for {protocol_hash}")

    def clear(self) -> None:
        """Clear all cached entries"""
        self.cache.clear()
        logger.info("Extraction cache cleared")


# ============================================================================
# CRITERIA EXTRACTOR
# ============================================================================

class CriteriaExtractor:
    """
    Main criteria extraction service.

    Workflow:
    1. Accept protocol text
    2. Check cache
    3. Call Claude API for extraction
    4. Parse and validate response
    5. Assign criterion IDs
    6. Cache result
    7. Return structured criteria
    """

    def __init__(self):
        """Initialize extractor with Anthropic client and cache"""
        self.client = Anthropic(api_key=config.ANTHROPIC_API_KEY)
        self.cache = ExtractionCache(config.CACHE_EXPIRY_MINUTES) if config.ENABLE_CRITERIA_CACHING else None
        self.max_retries = config.MAX_RETRY_ATTEMPTS
        self.initial_retry_delay = config.INITIAL_RETRY_DELAY_SECONDS

    def extract_criteria(
        self,
        protocol_text: str,
        protocol_id: Optional[str] = None,
        trial_name: Optional[str] = None
    ) -> CriteriaExtractionResult:
        """
        Extract eligibility criteria from protocol text.

        Args:
            protocol_text: Full text of clinical trial protocol
            protocol_id: Optional unique identifier for this protocol
            trial_name: Optional trial name to include in result

        Returns:
            CriteriaExtractionResult with structured criteria

        Raises:
            ValueError: If extraction fails after retries
            APIError: If Claude API is unavailable
        """

        # [IMPLEMENTATION]: Generate protocol hash for caching
        protocol_hash = hashlib.sha256(protocol_text.encode()).hexdigest()

        # [IMPLEMENTATION]: Check cache if enabled
        if self.cache:
            cached_result = self.cache.get(protocol_hash)
            if cached_result:
                logger.info(f"Returning cached extraction for protocol")
                return cached_result

        logger.info(f"Starting criteria extraction. Text length: {len(protocol_text)} chars")

        # [IMPLEMENTATION]: Build extraction prompt
        user_prompt = build_extraction_user_prompt(protocol_text)

        # [IMPLEMENTATION]: Call Claude with retry logic
        try:
            raw_response = self._call_claude_extraction(user_prompt)
        except (APIError, RateLimitError) as e:
            logger.error(f"Claude API error during extraction: {e}")
            raise ValueError(
                "Failed to extract criteria due to API issue. Please try again in a moment. "
                f"Error: {str(e)}"
            )

        # [IMPLEMENTATION]: Parse extraction response
        try:
            criteria_dicts = parse_extraction_response(raw_response)
        except ValueError as e:
            logger.error(f"Failed to parse extraction response: {e}")
            raise ValueError(
                f"Failed to parse trial criteria from response. "
                f"The protocol may not contain standard eligibility criteria. Error: {str(e)}"
            )

        # [IMPLEMENTATION]: Create CriterionModel objects
        criteria_models = []
        for crit_dict in criteria_dicts:
            try:
                model = CriterionModel(**crit_dict)
                criteria_models.append(model)
            except Exception as e:
                logger.warning(f"Failed to create CriterionModel: {e}")
                continue

        if not criteria_models:
            raise ValueError("No valid criteria could be extracted from the protocol")

        # [IMPLEMENTATION]: Assign criterion IDs (I1, I2... E1, E2...)
        criteria_models = self._assign_criterion_ids(criteria_models)

        # [IMPLEMENTATION]: Calculate overall extraction confidence
        extraction_confidence = self._calculate_extraction_confidence(
            criteria_models,
            len(protocol_text)
        )

        # [IMPLEMENTATION]: Build extraction result
        warnings = self._generate_extraction_warnings(criteria_models, protocol_text)

        result = CriteriaExtractionResult(
            protocol_id=protocol_id or protocol_hash[:16],
            trial_name=trial_name,
            criteria=criteria_models,
            extraction_confidence=extraction_confidence,
            extraction_method="llm",
            page_count=0,  # Would be set by PDF parser
            warnings=warnings
        )

        # [IMPLEMENTATION]: Cache result if caching enabled
        if self.cache:
            self.cache.set(protocol_hash, result)

        logger.info(
            f"Extraction complete. {len(criteria_models)} criteria extracted. "
            f"Confidence: {extraction_confidence:.2f}"
        )

        return result

    def _call_claude_extraction(self, user_prompt: str) -> str:
        """
        Call Claude API with extraction prompt and retry logic.

        Implements exponential backoff on rate limits.
        Strict timeout handling.

        Args:
            user_prompt: Formatted extraction prompt

        Returns:
            Raw response text from Claude

        Raises:
            APIError: If all retries fail
        """

        last_error = None

        for attempt in range(self.max_retries):
            try:
                logger.debug(f"Extraction API call (attempt {attempt + 1}/{self.max_retries})")

                # [IMPLEMENTATION]: Call Claude Sonnet with structured response
                message = self.client.messages.create(
                    model=config.CLAUDE_MODEL,
                    max_tokens=config.MAX_TOKENS_EXTRACTION,
                    system=EXTRACTION_SYSTEM_PROMPT,
                    messages=[
                        {
                            "role": "user",
                            "content": user_prompt
                        }
                    ],
                    timeout=30  # 30 second timeout per request
                )

                # [IMPLEMENTATION]: Extract response content
                response_text = message.content[0].text
                logger.debug(f"Received response: {len(response_text)} chars")

                return response_text

            except RateLimitError as e:
                # [IMPLEMENTATION]: Handle rate limiting with exponential backoff
                last_error = e
                if attempt < self.max_retries - 1:
                    wait_time = self.initial_retry_delay * (2 ** attempt)
                    logger.warning(
                        f"Rate limited. Waiting {wait_time}s before retry {attempt + 2}/{self.max_retries}"
                    )
                    time.sleep(wait_time)
                else:
                    logger.error(f"Rate limited and max retries exceeded")

            except APIError as e:
                # [IMPLEMENTATION]: Handle other API errors
                last_error = e
                if attempt < self.max_retries - 1:
                    logger.warning(f"API error: {e}. Retrying...")
                    time.sleep(self.initial_retry_delay * (attempt + 1))
                else:
                    logger.error(f"API error after {self.max_retries} attempts: {e}")

        # [IMPLEMENTATION]: All retries exhausted
        raise last_error or APIError("Unknown API error during extraction")

    def _assign_criterion_ids(self, criteria: List[CriterionModel]) -> List[CriterionModel]:
        """
        Assigns unique criterion IDs in format I1, I2... E1, E2...

        Args:
            criteria: List of criterion models without IDs

        Returns:
            List of criteria with assigned IDs
        """

        # [IMPLEMENTATION]: Separate inclusion and exclusion criteria
        inclusion_criteria = [c for c in criteria if c.type == CriterionType.INCLUSION]
        exclusion_criteria = [c for c in criteria if c.type == CriterionType.EXCLUSION]

        # [IMPLEMENTATION]: Assign IDs
        for idx, criterion in enumerate(inclusion_criteria, 1):
            criterion.criterion_id = f"I{idx}"

        for idx, criterion in enumerate(exclusion_criteria, 1):
            criterion.criterion_id = f"E{idx}"

        logger.info(
            f"Assigned IDs: {len(inclusion_criteria)} inclusion, "
            f"{len(exclusion_criteria)} exclusion criteria"
        )

        # [IMPLEMENTATION]: Return interleaved list (all criteria with IDs)
        return inclusion_criteria + exclusion_criteria

    def _detect_compound_criteria(self, criterion_text: str) -> Optional[Dict[str, Any]]:
        """
        Detects compound logic in criterion text (AND/OR conditions).

        Heuristics:
        - Look for "and", "or" keywords
        - Multiple threshold values
        - Multiple conditions in one sentence

        Args:
            criterion_text: Text of criterion

        Returns:
            Logic expression dict or None if simple criterion
        """

        # [IMPLEMENTATION]: Check for logical operators in text
        text_lower = criterion_text.lower()
        has_and = " and " in text_lower
        has_or = " or " in text_lower

        if not (has_and or has_or):
            return None

        # [IMPLEMENTATION]: Build simple logic representation
        logic = {
            "expression": criterion_text,
            "conditions": [],
            "operators": [],
            "complexity": "compound" if (has_and or has_or) else "simple"
        }

        # [IMPLEMENTATION]: Extract operators
        if has_and:
            logic["operators"].append("AND")
        if has_or:
            logic["operators"].append("OR")

        return logic

    def _calculate_extraction_confidence(
        self,
        criteria: List[CriterionModel],
        text_length: int
    ) -> float:
        """
        Calculates overall extraction confidence.

        Factors:
        - Number of criteria extracted
        - Average confidence per criterion
        - Protocol length adequacy
        - Presence of compound criteria

        Args:
            criteria: Extracted criteria
            text_length: Length of protocol text

        Returns:
            Confidence score 0.0-1.0
        """

        if not criteria:
            return 0.0

        # [IMPLEMENTATION]: Base confidence on number and quality of criteria
        avg_confidence = sum(c.confidence for c in criteria) / len(criteria)

        # [IMPLEMENTATION]: Factor in protocol length
        # Very short protocols may have incomplete extraction
        if text_length < 1000:
            length_factor = 0.7
        elif text_length < 5000:
            length_factor = 0.85
        else:
            length_factor = 1.0

        # [IMPLEMENTATION]: Factor in criterion count
        # More criteria suggest more complete extraction
        if len(criteria) < 5:
            count_factor = 0.8
        elif len(criteria) < 15:
            count_factor = 1.0
        else:
            count_factor = 0.95  # Very high counts may indicate over-extraction

        # [IMPLEMENTATION]: Calculate final confidence
        final_confidence = avg_confidence * length_factor * count_factor
        return max(0.0, min(1.0, final_confidence))

    def _generate_extraction_warnings(
        self,
        criteria: List[CriterionModel],
        protocol_text: str
    ) -> List[ExtractionWarning]:
        """
        Generates warnings about extraction quality/issues.

        Args:
            criteria: Extracted criteria
            protocol_text: Original protocol text

        Returns:
            List of warning objects
        """

        warnings = []

        # [IMPLEMENTATION]: Warn about low confidence criteria
        low_conf_criteria = [c for c in criteria if c.confidence < 0.7]
        if low_conf_criteria:
            warnings.append(ExtractionWarning(
                severity="warning",
                code="LOW_CONFIDENCE_CRITERIA",
                message=f"{len(low_conf_criteria)} criteria have lower confidence. "
                       "Please review these carefully."
            ))

        # [IMPLEMENTATION]: Warn about ambiguous language
        ambiguous_keywords = ["adequate", "appropriate", "reasonable", "clinically significant"]
        ambiguous_count = sum(
            1 for c in criteria
            if any(kw in c.description.lower() for kw in ambiguous_keywords)
        )
        if ambiguous_count > 0:
            warnings.append(ExtractionWarning(
                severity="warning",
                code="AMBIGUOUS_LANGUAGE",
                message=f"{ambiguous_count} criteria contain ambiguous language. "
                       "Clinician review recommended."
            ))

        # [IMPLEMENTATION]: Warn about very large protocols
        if len(protocol_text) > 50000:
            warnings.append(ExtractionWarning(
                severity="info",
                code="LARGE_PROTOCOL",
                message="This is a large protocol. Ensure all criteria were captured."
            ))

        # [IMPLEMENTATION]: Warn if very few criteria extracted
        if len(criteria) < 3:
            warnings.append(ExtractionWarning(
                severity="warning",
                code="FEW_CRITERIA",
                message="Very few criteria extracted. Protocol may not have standard criteria section."
            ))

        return warnings
