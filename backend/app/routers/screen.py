"""
TrialMatch AI Screen Router

FastAPI endpoint for patient screening against trial criteria.

POST /api/screen-patient
- Accepts: ScreeningRequest with patient data + criteria
- Returns: ScreeningResult JSON
- Handles: validation, patient screening, result aggregation
"""

import logging

from fastapi import APIRouter, HTTPException, status

from ..models.screening import (
    ScreeningRequest, ScreeningResult, PatientSummary
)
from ..models.criteria import CriterionModel
from ..services.patient_screener import PatientScreener


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["screening"])

# [IMPLEMENTATION]: Initialize service
screener = PatientScreener()


# ============================================================================
# SCREENING ENDPOINT
# ============================================================================

@router.post(
    "/screen-patient",
    response_model=ScreeningResult,
    status_code=status.HTTP_200_OK,
    summary="Screen Patient Against Trial Criteria",
    description="Evaluate a de-identified patient against clinical trial eligibility criteria"
)
async def screen_patient(
    request: ScreeningRequest
) -> ScreeningResult:
    """
    Screen a patient against trial eligibility criteria.

    Workflow:
    1. Validate request (patient data + criteria)
    2. For each criterion, determine MEETS / DOES_NOT_MEET / INSUFFICIENT_DATA
    3. Cite specific evidence from patient data
    4. Calculate overall trial eligibility status
    5. Aggregate missing data and generate follow-ups
    6. Return complete screening result

    Args:
        request: ScreeningRequest with patient_summary and criteria

    Returns:
        ScreeningResult with per-criterion assessments and overall status

    Raises:
        400: Validation error in request data
        422: Missing required patient data for screening
        500: Screening or API error
    """

    logger.info(
        f"Received screen-patient request. "
        f"Patient: {request.patient_summary.patient_id}, "
        f"Criteria: {len(request.criteria)}"
    )

    # [IMPLEMENTATION]: Validate request data
    try:
        # Validate patient summary
        if not request.patient_summary:
            raise ValueError("Patient summary is required")

        if not request.patient_summary.patient_id:
            raise ValueError("Patient ID must be provided")

        # Validate criteria
        if not request.criteria or len(request.criteria) == 0:
            raise ValueError("At least one criterion must be provided")

        for criterion in request.criteria:
            if not criterion.criterion_id:
                raise ValueError("All criteria must have criterion_id")

    except ValueError as e:
        logger.warning(f"Request validation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid request: {str(e)}"
        )

    # [IMPLEMENTATION]: Check for required patient fields
    # Some patient data is optional, but we warn if very sparse
    patient_data_fields = [
        request.patient_summary.age,
        request.patient_summary.diagnoses,
        request.patient_summary.lab_values
    ]
    provided_fields = sum(1 for field in patient_data_fields if field)

    if provided_fields == 0:
        logger.warning("Patient data is sparse - screening may have many INSUFFICIENT_DATA")

    # [IMPLEMENTATION]: Call screener service
    try:
        screening_result = screener.screen_patient(
            patient_summary=request.patient_summary,
            criteria=request.criteria,
            protocol_id=request.protocol_id or ""
        )

        logger.info(
            f"Screening complete. Status: {screening_result.overall_status.value}, "
            f"Assessments: {len(screening_result.assessments)}, "
            f"Missing data: {len(screening_result.missing_data_summary)}"
        )

        return screening_result

    except ValueError as e:
        logger.error(f"Screening failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Screening failed: {str(e)}"
        )
    except Exception as e:
        logger.exception(f"Unexpected error during screening: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during patient screening. Please try again."
        )


# ============================================================================
# VALIDATION ENDPOINT (OPTIONAL)
# ============================================================================

@router.post(
    "/validate-patient",
    status_code=status.HTTP_200_OK,
    summary="Validate Patient Data",
    description="Check if patient data is valid for screening"
)
async def validate_patient(patient: PatientSummary):
    """
    Validate patient summary data without performing screening.

    Useful for validating patient data before committing to screening request.

    Args:
        patient: PatientSummary to validate

    Returns:
        {"valid": true, "errors": []}
    """

    errors = []

    # [IMPLEMENTATION]: Check patient ID
    if not patient.patient_id or len(patient.patient_id.strip()) == 0:
        errors.append("patient_id is required")

    # [IMPLEMENTATION]: Check for identifying information
    forbidden_patterns = ['dob', 'birth', 'name', 'ssn', 'mrn']
    for pattern in forbidden_patterns:
        if pattern in patient.patient_id.lower():
            errors.append(f"patient_id contains potentially identifying information: {pattern}")

    # [IMPLEMENTATION]: Validate age if provided
    if patient.age is not None:
        if patient.age < 0 or patient.age > 150:
            errors.append("age must be between 0 and 150")

    logger.info(
        f"Patient validation: valid={len(errors) == 0}, "
        f"errors={len(errors)}"
    )

    return {
        "valid": len(errors) == 0,
        "patient_id": patient.patient_id,
        "errors": errors
    }
