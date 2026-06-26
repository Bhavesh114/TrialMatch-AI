"""
TrialMatch AI Prompt Engineering for Patient Screening

This module contains the LLM prompts and response parsing for Stage 2:
evaluating a patient against extracted trial eligibility criteria.

The screening process evaluates each criterion individually, determining:
- MEETS: Patient data satisfies the criterion
- DOES_NOT_MEET: Patient data fails to satisfy the criterion
- INSUFFICIENT_DATA: Cannot determine without additional patient information
"""

from typing import List, Dict, Any
import json
import logging


logger = logging.getLogger(__name__)


# ============================================================================
# SYSTEM PROMPT FOR PATIENT SCREENING
# ============================================================================

SCREENING_SYSTEM_PROMPT = """You are an expert clinical trial eligibility screener. Your task is to evaluate whether a patient meets or does not meet clinical trial eligibility criteria based on their clinical data.

CRITICAL INSTRUCTION: When in doubt about patient data, ALWAYS select "insufficient_data" rather than guessing or assuming values. This protects patient safety by flagging what clinicians must review.

YOUR EVALUATION PROCESS:
For each criterion:
1. Identify what patient data is REQUIRED to evaluate it
2. Check if that data is available in the patient summary
3. If available, compare patient data to criterion thresholds
4. Determine status: MEETS, DOES_NOT_MEET, or INSUFFICIENT_DATA
5. Rate your confidence (high/medium/low)
6. Provide reasoning citing specific patient data

ASSESSMENT RULES:

MEETS - Patient clearly satisfies the criterion:
- All required data is available
- Patient values are within acceptable ranges OR match required conditions
- No contradictory information exists
- Confidence: Usually "high"

DOES_NOT_MEET - Patient clearly violates the criterion:
- Data is available showing patient does NOT meet the criterion
- Patient values fall outside acceptable ranges OR fail to match required conditions
- Exclusion criteria are triggered
- Confidence: Usually "high"

INSUFFICIENT_DATA - Cannot determine eligibility:
- Required data is NOT provided in patient summary
- Data is outdated (e.g., lab value from 2 years ago when recent result needed)
- Contradictory information makes evaluation impossible
- Data is qualitative/unclear (e.g., "adequate renal function" without specific eGFR)
- Important dates/timings cannot be determined
- Confidence: Usually "medium" (but could be "high" if clearly missing)

CONFIDENCE SCORING:
- HIGH: Clear data, specific thresholds, unambiguous comparison
- MEDIUM: Some interpretation required, or partially available data
- LOW: Very unclear, contradictory information, significant assumptions needed

EXAMPLE EVALUATIONS:

Inclusion Criterion: "Age 18-65 years"
Patient age: 45
Status: MEETS | Confidence: HIGH
Reasoning: "Patient is 45 years old, which falls within the required age range of 18-65."
Evidence: ["Age: 45 years"]

Exclusion Criterion: "eGFR < 30 mL/min/1.73m2 (severe renal impairment)"
Patient data: "eGFR 92 mL/min/1.73m2 from 2024-02-15"
Status: MEETS (does NOT meet exclusion) | Confidence: HIGH
Reasoning: "Patient has eGFR of 92, which is well above the 30 threshold for severe renal impairment. Patient is therefore eligible."
Evidence: ["eGFR: 92 mL/min/1.73m2"]

Inclusion Criterion: "Diagnosis of Type 2 Diabetes for at least 6 months"
Patient data: "Diagnosed with Type 2 DM in 2018" (but current date context is available)
Status: MEETS | Confidence: HIGH
Reasoning: "Patient was diagnosed in 2018, exceeding the 6-month minimum requirement."
Evidence: ["Diagnosis: Type 2 Diabetes (since 2018)"]

Inclusion Criterion: "LVEF >= 50% by recent echocardiogram"
Patient data: "History of heart failure, no recent echo results provided"
Status: INSUFFICIENT_DATA | Confidence: MEDIUM
Reasoning: "Patient has heart failure history but no recent LVEF measurement is available. A current echocardiogram is required to determine eligibility."
Missing: ["LVEF percentage from recent echocardiogram (within 3 months)"]

OUTPUT FORMAT: Return ONLY valid JSON array (no markdown, no extra text).
Each assessment must include all required fields.
"""


# ============================================================================
# USER PROMPT BUILDER
# ============================================================================

def build_screening_user_prompt(
    criteria: List[Dict[str, Any]],
    patient_summary: Dict[str, Any]
) -> str:
    """
    Builds the screening prompt for evaluating a patient against criteria.

    Args:
        criteria: List of criterion dictionaries (from extraction)
        patient_summary: Patient data dictionary

    Returns:
        Formatted prompt string ready for Claude API
    """

    # [IMPLEMENTATION]: Format criteria for readability
    criteria_text = ""
    for criterion in criteria:
        crit_id = criterion.get('criterion_id', 'UNSET')
        crit_type = criterion.get('type', 'unknown').upper()
        description = criterion.get('description', '')
        data_points = criterion.get('data_points_needed', [])

        criteria_text += f"\n{crit_id} [{crit_type}]: {description}\n"

        if data_points:
            criteria_text += "  Data needed: " + ", ".join(
                dp.get('name') for dp in data_points if isinstance(dp, dict)
            ) + "\n"

    # [IMPLEMENTATION]: Format patient data for readability
    patient_text = f"""
Patient ID: {patient_summary.get('patient_id', 'UNKNOWN')}
Age: {patient_summary.get('age', 'NOT PROVIDED')}
Sex: {patient_summary.get('sex', 'NOT PROVIDED')}

Diagnoses: {', '.join(patient_summary.get('diagnoses', [])) or 'NONE LISTED'}

Current Medications:
{_format_medications(patient_summary.get('medications', []))}

Lab Values:
{_format_lab_values(patient_summary.get('lab_values', {}))}

Comorbidities: {', '.join(patient_summary.get('comorbidities', [])) or 'NONE LISTED'}

Surgical History: {', '.join(patient_summary.get('surgical_history', [])) or 'NONE LISTED'}

Allergies: {', '.join(patient_summary.get('allergies', [])) or 'NONE LISTED'}

Additional Notes:
{patient_summary.get('free_text_notes', 'NONE PROVIDED')}
"""

    prompt = f"""Please evaluate the following patient against the trial eligibility criteria.

TRIAL CRITERIA:
{criteria_text}

PATIENT DATA:
{patient_text}

SCREENING INSTRUCTIONS:
1. For each criterion (in order I1, I2... then E1, E2...), determine the assessment status
2. Always cite specific patient data in your reasoning
3. When required data is missing, mark as INSUFFICIENT_DATA - do NOT guess
4. Be conservative: prefer INSUFFICIENT_DATA over making assumptions
5. For compound criteria with multiple conditions, all conditions must be met

RETURN ONLY THE JSON ARRAY - no markdown, no explanation, just the array of assessments.

Expected JSON format: [
  {
    "criterion_id": "I1",
    "status": "meets",
    "confidence": "high",
    "reasoning": "string",
    "missing_data": [],
    "evidence_cited": ["string"]
  }
]
"""

    return prompt


# ============================================================================
# RESPONSE PARSING
# ============================================================================

def parse_screening_response(raw_response: str) -> List[Dict[str, Any]]:
    """
    Parses the raw Claude screening response into assessment data.

    Handles:
    - JSON parsing errors
    - Missing required fields
    - Invalid status/confidence values
    - Incomplete assessments

    Args:
        raw_response: Raw text response from Claude API

    Returns:
        List of validated assessment dictionaries

    Raises:
        ValueError: If response cannot be parsed or is malformed
    """

    # [IMPLEMENTATION]: Strip markdown code blocks if present
    cleaned = raw_response.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned[cleaned.find("\n") + 1:]
        cleaned = cleaned[:cleaned.rfind("```")]
        cleaned = cleaned.strip()

    try:
        # [IMPLEMENTATION]: Parse JSON from cleaned response
        assessments_list = json.loads(cleaned)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse screening response as JSON: {e}")
        raise ValueError(
            f"LLM returned malformed JSON. This may indicate a temporary API issue. Error: {str(e)}"
        )

    if not isinstance(assessments_list, list):
        raise ValueError(
            f"Expected JSON array but got {type(assessments_list).__name__}"
        )

    if len(assessments_list) == 0:
        raise ValueError("No assessments were returned")

    # [IMPLEMENTATION]: Validate each assessment
    validated_assessments = []
    for idx, assessment in enumerate(assessments_list):
        try:
            validated = _validate_assessment_object(assessment, idx)
            validated_assessments.append(validated)
        except ValueError as e:
            logger.warning(f"Invalid assessment {idx}: {e}")
            # Create minimal valid assessment for this criterion
            # This prevents total failure from a single bad assessment
            if 'criterion_id' in assessment:
                validated_assessments.append({
                    'criterion_id': assessment['criterion_id'],
                    'status': 'insufficient_data',
                    'confidence': 'low',
                    'reasoning': 'Assessment validation failed. Manual review required.',
                    'missing_data': ['Manual review needed'],
                    'evidence_cited': []
                })

    logger.info(f"Successfully parsed {len(validated_assessments)} assessments")
    return validated_assessments


def _validate_assessment_object(assessment: Dict[str, Any], index: int) -> Dict[str, Any]:
    """
    Validates a single assessment object.

    Args:
        assessment: Assessment dictionary from JSON
        index: Index for error reporting

    Returns:
        Validated assessment dictionary

    Raises:
        ValueError: If required fields are invalid
    """

    # [IMPLEMENTATION]: Check required fields
    required_fields = ['criterion_id', 'status', 'confidence']
    for field in required_fields:
        if field not in assessment:
            raise ValueError(f"Assessment missing required field: {field}")

    # [IMPLEMENTATION]: Validate status field
    valid_statuses = ['meets', 'does_not_meet', 'insufficient_data']
    status = str(assessment.get('status', '')).lower().strip()
    if status not in valid_statuses:
        raise ValueError(
            f"Invalid status '{status}'. Must be one of: {valid_statuses}"
        )

    # [IMPLEMENTATION]: Validate confidence field
    valid_confidences = ['high', 'medium', 'low']
    confidence = str(assessment.get('confidence', '')).lower().strip()
    if confidence not in valid_confidences:
        raise ValueError(
            f"Invalid confidence '{confidence}'. Must be one of: {valid_confidences}"
        )

    # [IMPLEMENTATION]: Extract and validate reasoning
    reasoning = assessment.get('reasoning', '').strip()
    if not reasoning or len(reasoning) < 5:
        raise ValueError("Reasoning is empty or too short")
    if len(reasoning) > 500:
        reasoning = reasoning[:500]

    # [IMPLEMENTATION]: Extract missing_data and evidence_cited
    missing_data = assessment.get('missing_data', [])
    if not isinstance(missing_data, list):
        missing_data = []

    evidence_cited = assessment.get('evidence_cited', [])
    if not isinstance(evidence_cited, list):
        evidence_cited = []

    # [IMPLEMENTATION]: Build validated assessment
    validated = {
        'criterion_id': str(assessment.get('criterion_id')).strip(),
        'status': status,
        'confidence': confidence,
        'reasoning': reasoning,
        'missing_data': missing_data,
        'evidence_cited': evidence_cited
    }

    return validated


# ============================================================================
# HELPER FUNCTIONS FOR PROMPT FORMATTING
# ============================================================================

def _format_medications(medications: List[Dict[str, str]]) -> str:
    """
    Formats medication list for prompt readability.

    Args:
        medications: List of medication dictionaries

    Returns:
        Formatted medication string
    """
    if not medications:
        return "  NONE LISTED"

    formatted = ""
    for med in medications:
        if isinstance(med, dict):
            name = med.get('name', 'UNKNOWN')
            dose = med.get('dose', '')
            frequency = med.get('frequency', '')
            formatted += f"  - {name}"
            if dose:
                formatted += f" {dose}"
            if frequency:
                formatted += f" {frequency}"
            formatted += "\n"

    return formatted if formatted else "  NONE LISTED"


def _format_lab_values(lab_values: Dict[str, Dict[str, Any]]) -> str:
    """
    Formats lab values for prompt readability.

    Args:
        lab_values: Dictionary of lab test results

    Returns:
        Formatted lab values string
    """
    if not lab_values:
        return "  NONE PROVIDED"

    formatted = ""
    for test_name, result in lab_values.items():
        if isinstance(result, dict):
            value = result.get('value', 'UNKNOWN')
            unit = result.get('unit', '')
            date_str = result.get('date', '')
            formatted += f"  - {test_name}: {value}"
            if unit:
                formatted += f" {unit}"
            if date_str:
                formatted += f" (from {date_str})"
            formatted += "\n"

    return formatted if formatted else "  NONE PROVIDED"
