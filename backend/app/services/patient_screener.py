"""
TrialMatch AI Patient Screener Service

Handles Stage 2 of screening: evaluating a patient against trial criteria.

Uses Claude API with specialized prompts to:
1. Evaluate each criterion individually
2. Determine MEETS / DOES_NOT_MEET / INSUFFICIENT_DATA status
3. Cite specific evidence from patient data
4. Identify missing data that would help evaluation
5. Generate follow-up questions for clinicians
6. Calculate overall trial eligibility
"""

import logging
import time
from typing import List, Dict, Any
from datetime import datetime

from anthropic import Anthropic, APIError, RateLimitError

from ..config import config
from ..models.criteria import CriterionModel
from ..models.screening import (
    PatientSummary,
    ScreeningResult,
    OverallStatus,
    CriterionAssessment,
    AssessmentStatus,
    ConfidenceLevel
)
from ..prompts.screening import (
    SCREENING_SYSTEM_PROMPT,
    build_screening_user_prompt,
    parse_screening_response
)


logger = logging.getLogger(__name__)


class PatientScreener:
    """
    Main patient screening service.

    Workflow:
    1. Accept patient summary + criteria list
    2. Build screening prompt
    3. Call Claude API for per-criterion assessment
    4. Parse and validate assessments
    5. Calculate overall eligibility status
    6. Aggregate missing data and generate follow-ups
    7. Return complete screening result
    """

    def __init__(self):
        """Initialize screener with Anthropic client"""
        self.client = Anthropic(api_key=config.ANTHROPIC_API_KEY)
        self.max_retries = config.MAX_RETRY_ATTEMPTS
        self.initial_retry_delay = config.INITIAL_RETRY_DELAY_SECONDS

    def screen_patient(
        self,
        patient_summary: PatientSummary,
        criteria: List[CriterionModel],
        protocol_id: str = ""
    ) -> ScreeningResult:
        """
        Screen a patient against trial criteria.

        Args:
            patient_summary: De-identified patient data
            criteria: List of criteria to evaluate
            protocol_id: Protocol ID for tracking

        Returns:
            ScreeningResult with per-criterion assessments and overall status

        Raises:
            ValueError: If screening fails after retries
            APIError: If Claude API is unavailable
        """

        logger.info(
            f"Starting patient screening. Patient: {patient_summary.patient_id}, "
            f"Criteria: {len(criteria)}"
        )

        # [IMPLEMENTATION]: Build screening prompt
        criteria_dicts = [c.model_dump() for c in criteria]
        patient_dict = patient_summary.model_dump()
        user_prompt = build_screening_user_prompt(criteria_dicts, patient_dict)

        # [IMPLEMENTATION]: Call Claude with retry logic
        try:
            raw_response = self._call_claude_screening(user_prompt)
        except (APIError, RateLimitError) as e:
            logger.error(f"Claude API error during screening: {e}")
            raise ValueError(
                "Failed to screen patient due to API issue. Please try again. "
                f"Error: {str(e)}"
            )

        # [IMPLEMENTATION]: Parse screening response
        try:
            assessment_dicts = parse_screening_response(raw_response)
        except ValueError as e:
            logger.error(f"Failed to parse screening response: {e}")
            raise ValueError(
                f"Failed to parse screening results. Error: {str(e)}"
            )

        # [IMPLEMENTATION]: Create CriterionAssessment objects
        assessments = []
        for assess_dict in assessment_dicts:
            try:
                # [IMPLEMENTATION]: Map string values to enum values
                status_str = assess_dict.get('status', 'insufficient_data')
                confidence_str = assess_dict.get('confidence', 'medium')

                assessment = CriterionAssessment(
                    criterion_id=assess_dict.get('criterion_id'),
                    status=AssessmentStatus(status_str),
                    confidence=ConfidenceLevel(confidence_str),
                    reasoning=assess_dict.get('reasoning', ''),
                    missing_data=assess_dict.get('missing_data', []),
                    evidence_cited=assess_dict.get('evidence_cited', [])
                )
                assessments.append(assessment)
            except Exception as e:
                logger.warning(f"Failed to create assessment: {e}")
                continue

        # [IMPLEMENTATION]: Validate we have assessments for all criteria
        missing_assessments = self._validate_assessment_completeness(assessments, criteria)
        if missing_assessments:
            logger.warning(f"Missing assessments for criteria: {missing_assessments}")

        # [IMPLEMENTATION]: Calculate overall eligibility status
        overall_status = self._calculate_overall_status(assessments)

        # [IMPLEMENTATION]: Aggregate missing data across criteria
        missing_data_summary = self._aggregate_missing_data(assessments)

        # [IMPLEMENTATION]: Generate follow-up questions
        follow_up_questions = self._generate_follow_up_questions(assessments)

        # [IMPLEMENTATION]: Build screening result
        screening_id = self._generate_screening_id()

        result = ScreeningResult(
            screening_id=screening_id,
            protocol_id=protocol_id,
            patient_id=patient_summary.patient_id,
            overall_status=overall_status,
            assessments=assessments,
            missing_data_summary=missing_data_summary,
            follow_up_questions=follow_up_questions,
            assessed_at=datetime.utcnow()
        )

        logger.info(
            f"Screening complete. Patient {patient_summary.patient_id} → {overall_status.value}. "
            f"Assessments: {len(assessments)}, Missing data: {len(missing_data_summary)}"
        )

        return result

    def _call_claude_screening(self, user_prompt: str) -> str:
        """
        Call Claude API with screening prompt and retry logic.

        Args:
            user_prompt: Formatted screening prompt

        Returns:
            Raw response text from Claude

        Raises:
            APIError: If all retries fail
        """

        last_error = None

        for attempt in range(self.max_retries):
            try:
                logger.debug(f"Screening API call (attempt {attempt + 1}/{self.max_retries})")

                # [IMPLEMENTATION]: Call Claude with structured response
                message = self.client.messages.create(
                    model=config.CLAUDE_MODEL,
                    max_tokens=config.MAX_TOKENS_SCREENING,
                    system=SCREENING_SYSTEM_PROMPT,
                    messages=[
                        {
                            "role": "user",
                            "content": user_prompt
                        }
                    ],
                    timeout=45  # 45 second timeout for screening
                )

                response_text = message.content[0].text
                logger.debug(f"Received screening response: {len(response_text)} chars")

                return response_text

            except RateLimitError as e:
                # [IMPLEMENTATION]: Handle rate limiting
                last_error = e
                if attempt < self.max_retries - 1:
                    wait_time = self.initial_retry_delay * (2 ** attempt)
                    logger.warning(
                        f"Rate limited during screening. Waiting {wait_time}s before retry"
                    )
                    time.sleep(wait_time)

            except APIError as e:
                # [IMPLEMENTATION]: Handle other API errors
                last_error = e
                if attempt < self.max_retries - 1:
                    logger.warning(f"Screening API error: {e}. Retrying...")
                    time.sleep(self.initial_retry_delay * (attempt + 1))

        raise last_error or APIError("Unknown API error during screening")

    def _calculate_overall_status(self, assessments: List[CriterionAssessment]) -> OverallStatus:
        """
        Calculate overall trial eligibility from individual assessments.

        Logic:
        1. If ANY exclusion criterion is DOES_NOT_MEET → LIKELY_INELIGIBLE
        2. If ALL criteria are MEETS → LIKELY_ELIGIBLE
        3. Otherwise → NEEDS_REVIEW (mixed or uncertain)

        Args:
            assessments: Per-criterion assessments

        Returns:
            Overall eligibility status
        """

        # [IMPLEMENTATION]: Separate by status
        meets_count = 0
        does_not_meet_count = 0
        insufficient_count = 0

        for assessment in assessments:
            if assessment.status == AssessmentStatus.MEETS:
                meets_count += 1
            elif assessment.status == AssessmentStatus.DOES_NOT_MEET:
                does_not_meet_count += 1
            else:
                insufficient_count += 1

        # [IMPLEMENTATION]: Apply logic
        if does_not_meet_count > 0:
            # Any failed criterion makes patient ineligible
            logger.info(
                f"Overall status: LIKELY_INELIGIBLE ({does_not_meet_count} failed criteria)"
            )
            return OverallStatus.LIKELY_INELIGIBLE

        elif insufficient_count > 0:
            # Missing data prevents definitive eligibility
            logger.info(
                f"Overall status: NEEDS_REVIEW ({insufficient_count} insufficient data)"
            )
            return OverallStatus.NEEDS_REVIEW

        elif meets_count == len(assessments):
            # All criteria satisfied
            logger.info(
                f"Overall status: LIKELY_ELIGIBLE (all {meets_count} criteria met)"
            )
            return OverallStatus.LIKELY_ELIGIBLE

        else:
            # Fallback: uncertain
            logger.info("Overall status: NEEDS_REVIEW (mixed results)")
            return OverallStatus.NEEDS_REVIEW

    def _aggregate_missing_data(self, assessments: List[CriterionAssessment]) -> List[str]:
        """
        Aggregate missing data items across all criteria.

        Returns unique missing data items ordered by frequency.

        Args:
            assessments: Per-criterion assessments

        Returns:
            Deduplicated list of missing data items
        """

        # [IMPLEMENTATION]: Collect all missing data items
        missing_data_dict = {}
        for assessment in assessments:
            for item in assessment.missing_data:
                if item not in missing_data_dict:
                    missing_data_dict[item] = 0
                missing_data_dict[item] += 1

        # [IMPLEMENTATION]: Sort by frequency (most needed first)
        sorted_items = sorted(
            missing_data_dict.items(),
            key=lambda x: x[1],
            reverse=True
        )

        missing_data_summary = [item for item, _ in sorted_items]

        logger.info(f"Aggregated {len(missing_data_summary)} unique missing data items")

        return missing_data_summary

    def _generate_follow_up_questions(
        self,
        assessments: List[CriterionAssessment]
    ) -> List[str]:
        """
        Generate follow-up questions for clinicians to clarify uncertain assessments.

        Questions are derived from:
        - Criteria with INSUFFICIENT_DATA status
        - Missing data items
        - Low confidence assessments

        Args:
            assessments: Per-criterion assessments

        Returns:
            List of follow-up question strings
        """

        questions = []

        # [IMPLEMENTATION]: Add questions for each INSUFFICIENT_DATA assessment
        for assessment in assessments:
            if assessment.status == AssessmentStatus.INSUFFICIENT_DATA:
                if assessment.missing_data:
                    # [IMPLEMENTATION]: Convert missing data to question format
                    for missing_item in assessment.missing_data[:1]:  # Use first missing item
                        question = f"What is the patient's {missing_item.lower()}? "
                        question += f"(Required for criterion {assessment.criterion_id})"
                        questions.append(question)

        # [IMPLEMENTATION]: Add questions for low-confidence assessments
        for assessment in assessments:
            if assessment.confidence == ConfidenceLevel.LOW:
                question = f"Criterion {assessment.criterion_id}: Can you clarify/confirm "
                question += f"whether the patient {assessment.reasoning[:30].lower()}...?"
                questions.append(question)

        # [IMPLEMENTATION]: Remove duplicates while preserving order
        seen = set()
        unique_questions = []
        for q in questions:
            if q not in seen:
                seen.add(q)
                unique_questions.append(q)

        logger.info(f"Generated {len(unique_questions)} follow-up questions")

        return unique_questions[:10]  # Limit to 10 most important

    def _validate_assessment_completeness(
        self,
        assessments: List[CriterionAssessment],
        criteria: List[CriterionModel]
    ) -> List[str]:
        """
        Validate that all criteria have corresponding assessments.

        Args:
            assessments: Per-criterion assessments
            criteria: Original criteria list

        Returns:
            List of criterion IDs missing assessments (empty if all covered)
        """

        # [IMPLEMENTATION]: Extract assessed criterion IDs
        assessed_ids = {a.criterion_id for a in assessments}
        expected_ids = {c.criterion_id for c in criteria}

        # [IMPLEMENTATION]: Find missing assessments
        missing = expected_ids - assessed_ids

        if missing:
            logger.warning(f"Missing assessments for: {missing}")

        return sorted(list(missing))

    def _generate_screening_id(self) -> str:
        """
        Generate unique screening ID.

        Format: SCR-YYYYMMDD-XXXXXX (timestamp + random)

        Returns:
            Unique screening ID
        """

        from datetime import datetime
        import random
        import string

        date_str = datetime.utcnow().strftime("%Y%m%d")
        random_str = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

        return f"SCR-{date_str}-{random_str}"
