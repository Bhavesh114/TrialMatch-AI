"""
TrialMatch AI Prompt Engineering for Criteria Extraction

This module contains the LLM prompts and response parsing for Stage 1:
extracting structured eligibility criteria from clinical trial protocol text.

The two-stage approach:
1. Extract criteria from protocol → JSON structure
2. Evaluate criteria against patient → eligibility assessment
"""

from typing import List, Dict, Any
import json
import logging


logger = logging.getLogger(__name__)


# ============================================================================
# SYSTEM PROMPT FOR CRITERIA EXTRACTION
# ============================================================================

EXTRACTION_SYSTEM_PROMPT = """You are an expert clinical trial data analyst specializing in extracting eligibility criteria from research protocols.

Your task is to:
1. Read clinical trial protocol text
2. Identify and extract ALL inclusion and exclusion criteria
3. Parse each criterion into structured JSON format
4. Identify compound logic (AND/OR conditions)
5. Determine what patient data is needed to evaluate each criterion
6. Assign confidence scores based on clarity of the criterion text

IMPORTANT INSTRUCTIONS:
- Extract EVERY criterion mentioned, no matter how small or detailed
- Be especially careful with criteria hidden in narrative paragraphs, not just bulleted lists
- Identify COMPOUND criteria (e.g., "age 18-65 AND diagnosed with condition X")
- For each criterion, extract the exact SOURCE TEXT from the protocol
- Flag ambiguous criteria (e.g., "adequate organ function" requires clarification)
- Assign high confidence only when criterion language is specific and measurable
- Assign medium confidence when language is clear but may need interpretation
- Assign low confidence for vague or ambiguous criteria

OUTPUT FORMAT: Return ONLY valid JSON array (no markdown, no extra text).
Each criterion object must have all required fields.

CRITERIA CATEGORIES:
- demographic (age, sex, race, ethnicity)
- diagnosis (confirmed diagnosis of specific condition)
- disease_severity (stage, grade, severity classification)
- lab_values (test results, thresholds)
- comorbidity (concurrent conditions)
- medication (current or prior drug use)
- organ_function (kidney, liver, cardiac function)
- pregnancy_status (pregnancy, lactation status)
- prior_treatment (previous therapies, lines of treatment)
- surgery_history (surgical procedures, timing)
- contraindication (conditions that prohibit enrollment)
- other (miscellaneous)

DATA POINT TYPES:
- numeric: quantitative values (age, test result, dose)
- categorical: discrete values (diagnosis name, sex, medication name)
- date: temporal values (date of diagnosis, procedure date)
- boolean: yes/no values (pregnant status, prior surgery)
"""


# ============================================================================
# USER PROMPT BUILDER
# ============================================================================

def build_extraction_user_prompt(protocol_text: str) -> str:
    """
    Builds the user-facing extraction prompt for a specific protocol.

    Args:
        protocol_text: Raw text from the clinical trial protocol PDF

    Returns:
        Formatted prompt string ready for Claude API
    """

    prompt = f"""Please extract ALL inclusion and exclusion criteria from the following clinical trial protocol text.

PROTOCOL TEXT:
---
{protocol_text}
---

EXTRACTION REQUIREMENTS:
1. Extract EVERY criterion (inclusion and exclusion) mentioned in the protocol
2. For each criterion, identify:
   - Type: "inclusion" or "exclusion"
   - Description: Clear, concise statement of the criterion
   - Category: One of the categories listed in the system instructions
   - Source text: Exact quote from the protocol
   - Data points needed: List of patient data points required to evaluate
   - Logic: If compound criterion (contains AND/OR), extract the logic structure
   - Confidence: 0.0-1.0 based on clarity and specificity

3. Pay special attention to:
   - Age ranges (e.g., "18-65 years old")
   - Lab value thresholds (e.g., "eGFR >= 60")
   - Specific diagnoses with durations (e.g., "diagnosed with Type 2 DM for >=6 months")
   - Concurrent conditions (e.g., "no uncontrolled hypertension")
   - Medication exclusions (e.g., "must not be on ACE inhibitors")
   - Pregnancy/lactation status
   - Prior treatment lines or counts
   - Organ function criteria

4. For COMPOUND criteria, structure like:
   - Expression: "age >= 18 AND age <= 65 AND diagnosis = Type 2 Diabetes"
   - Conditions: [condition1, condition2, condition3, ...]
   - Operators: ["AND", "AND"]
   - Complexity: "compound"

5. Criteria IDs will be assigned in processing (I1, I2... E1, E2...). Leave criterion_id as null.

RETURN ONLY THE JSON ARRAY - no markdown, no explanation, just the array."""

    return prompt


# ============================================================================
# EXPECTED JSON SCHEMA (for documentation)
# ============================================================================

EXTRACTION_JSON_SCHEMA = """
[
  {
    "criterion_id": null,
    "type": "inclusion",
    "description": "string",
    "category": "string",
    "source_text": "string",
    "data_points_needed": [
      {
        "name": "string",
        "type": "numeric|categorical|date|boolean",
        "unit": "string|null",
        "required": true
      }
    ],
    "logic": {
      "expression": "string",
      "conditions": [],
      "operators": [],
      "complexity": "simple|compound"
    },
    "confidence": 0.95,
    "notes": "string|null"
  }
]
"""


# ============================================================================
# RESPONSE PARSING AND VALIDATION
# ============================================================================

def parse_extraction_response(raw_response: str) -> List[Dict[str, Any]]:
    """
    Parses the raw Claude response into structured criterion data.

    Handles:
    - JSON parsing errors
    - Missing required fields
    - Invalid data types
    - Malformed criterion structures

    Args:
        raw_response: Raw text response from Claude API

    Returns:
        List of validated criterion dictionaries

    Raises:
        ValueError: If response cannot be parsed or is missing critical data
    """

    # [IMPLEMENTATION]: Strip markdown code blocks if present
    # Response might be wrapped in ```json ... ``` blocks
    cleaned = raw_response.strip()
    if cleaned.startswith("```"):
        # Remove opening ```json or ```
        cleaned = cleaned[cleaned.find("\n") + 1:]
        # Remove closing ```
        cleaned = cleaned[:cleaned.rfind("```")]
        cleaned = cleaned.strip()

    try:
        # [IMPLEMENTATION]: Parse JSON from cleaned response
        criteria_list = json.loads(cleaned)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse extraction response as JSON: {e}")
        logger.debug(f"Raw response: {raw_response[:500]}...")
        raise ValueError(
            f"Failed to parse LLM response as JSON. "
            f"This may indicate the model returned malformed data. Error: {str(e)}"
        )

    if not isinstance(criteria_list, list):
        raise ValueError(
            f"Expected JSON array but got {type(criteria_list).__name__}"
        )

    if len(criteria_list) == 0:
        raise ValueError("No criteria were extracted from the protocol")

    # [IMPLEMENTATION]: Validate each criterion object
    validated_criteria = []
    for idx, criterion in enumerate(criteria_list):
        try:
            validated_criterion = _validate_criterion_object(criterion, idx)
            validated_criteria.append(validated_criterion)
        except ValueError as e:
            logger.warning(f"Skipping criterion {idx} due to validation error: {e}")
            # Continue processing other criteria rather than failing entirely
            # This handles edge cases where LLM returns some malformed criteria

    if len(validated_criteria) == 0:
        raise ValueError(
            "No valid criteria could be extracted after validation. "
            "The protocol may not contain structured eligibility criteria."
        )

    logger.info(f"Successfully parsed {len(validated_criteria)} criteria from extraction response")
    return validated_criteria


def _validate_criterion_object(criterion: Dict[str, Any], index: int) -> Dict[str, Any]:
    """
    Validates a single criterion object and normalizes field values.

    Args:
        criterion: Criterion dictionary from JSON
        index: Index for error reporting

    Returns:
        Validated and normalized criterion dictionary

    Raises:
        ValueError: If required fields are missing or invalid
    """

    # [IMPLEMENTATION]: Check required fields
    required_fields = ['type', 'description', 'category']
    for field in required_fields:
        if field not in criterion or criterion[field] is None:
            raise ValueError(f"Criterion {index} missing required field: {field}")

    # [IMPLEMENTATION]: Validate type field
    valid_types = ['inclusion', 'exclusion']
    criterion_type = criterion.get('type', '').lower().strip()
    if criterion_type not in valid_types:
        raise ValueError(
            f"Criterion {index} invalid type '{criterion_type}'. "
            f"Must be 'inclusion' or 'exclusion'"
        )

    # [IMPLEMENTATION]: Validate and clean description
    description = criterion.get('description', '').strip()
    if not description or len(description) < 5:
        raise ValueError(
            f"Criterion {index} has empty or too-short description"
        )
    if len(description) > 1000:
        logger.warning(
            f"Criterion {index} description exceeds 1000 chars, truncating"
        )
        description = description[:1000]

    # [IMPLEMENTATION]: Validate confidence score
    confidence = criterion.get('confidence', 1.0)
    try:
        confidence = float(confidence)
        if not (0.0 <= confidence <= 1.0):
            raise ValueError()
    except (ValueError, TypeError):
        logger.warning(f"Criterion {index} has invalid confidence, defaulting to 0.5")
        confidence = 0.5

    # [IMPLEMENTATION]: Normalize data_points_needed structure
    data_points = criterion.get('data_points_needed', [])
    if not isinstance(data_points, list):
        data_points = []
    normalized_data_points = []
    for dp in data_points:
        if isinstance(dp, dict) and 'name' in dp:
            normalized_data_points.append({
                'name': str(dp.get('name', '')).strip(),
                'type': str(dp.get('type', 'categorical')).lower(),
                'unit': dp.get('unit'),
                'required': bool(dp.get('required', True))
            })

    # [IMPLEMENTATION]: Normalize logic structure if present
    logic = criterion.get('logic')
    if logic and isinstance(logic, dict):
        logic = {
            'expression': str(logic.get('expression', '')).strip(),
            'conditions': logic.get('conditions', []),
            'operators': [op.upper() for op in logic.get('operators', [])],
            'complexity': logic.get('complexity', 'simple')
        }

    # [IMPLEMENTATION]: Build normalized criterion object
    normalized = {
        'criterion_id': None,  # Will be assigned later
        'type': criterion_type,
        'description': description,
        'category': str(criterion.get('category', 'other')).lower().strip(),
        'source_text': criterion.get('source_text'),
        'data_points_needed': normalized_data_points,
        'logic': logic,
        'confidence': confidence,
        'notes': criterion.get('notes')
    }

    return normalized
