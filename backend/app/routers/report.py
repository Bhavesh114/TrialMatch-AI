"""
TrialMatch AI Report Router

FastAPI endpoint for generating downloadable PDF reports.

POST /api/export-report
- Accepts: ReportRequest with screening result + metadata
- Returns: PDF file as application/pdf
- Handles: validation, report generation, file streaming
"""

import logging
import io

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse

from ..models.screening import ReportRequest, ReportData
from ..services.report_generator import ReportGenerator


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["reports"])

# [IMPLEMENTATION]: Initialize service
report_generator = ReportGenerator()


# ============================================================================
# REPORT EXPORT ENDPOINT
# ============================================================================

@router.post(
    "/export-report",
    status_code=status.HTTP_200_OK,
    summary="Export Screening Report as PDF",
    description="Generate a downloadable PDF report of the screening results"
)
async def export_report(request: ReportRequest) -> StreamingResponse:
    """
    Generate and export screening results as a professional PDF report.

    The report includes:
    - Trial information and patient ID
    - Overall eligibility status with visual indicator
    - Detailed per-criterion assessment table
    - Expanded reasoning for each criterion
    - Missing data and recommended follow-ups
    - Legal disclaimer and metadata

    Args:
        request: ReportRequest with screening_result, patient_summary, trial_info

    Returns:
        StreamingResponse with PDF file (application/pdf)

    Raises:
        400: Validation error in request data
        500: Report generation error
    """

    logger.info(
        f"Received export-report request. "
        f"Screening: {request.screening_result.screening_id}, "
        f"Patient: {request.patient_summary.patient_id}"
    )

    # [IMPLEMENTATION]: Validate request data
    try:
        if not request.screening_result:
            raise ValueError("screening_result is required")

        if not request.patient_summary:
            raise ValueError("patient_summary is required")

        if not request.trial_info:
            raise ValueError("trial_info is required")

        if 'trial_name' not in request.trial_info:
            raise ValueError("trial_info must include trial_name")

    except ValueError as e:
        logger.warning(f"Report request validation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid report request: {str(e)}"
        )

    # [IMPLEMENTATION]: Generate PDF
    try:
        pdf_bytes = report_generator.generate_report(
            screening_result=request.screening_result,
            patient_summary=request.patient_summary,
            trial_info=request.trial_info
        )

        logger.info(f"Generated PDF report: {len(pdf_bytes)} bytes")

        # [IMPLEMENTATION]: Create streaming response with proper headers
        pdf_buffer = io.BytesIO(pdf_bytes)

        filename = (
            f"TrialMatch_Report_{request.screening_result.screening_id}.pdf"
        )

        return StreamingResponse(
            iter([pdf_bytes]),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "Content-Length": str(len(pdf_bytes))
            }
        )

    except ValueError as e:
        logger.error(f"Report generation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate report: {str(e)}"
        )
    except Exception as e:
        logger.exception(f"Unexpected error during report generation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while generating the report."
        )


# ============================================================================
# REPORT PREVIEW ENDPOINT (OPTIONAL)
# ============================================================================

@router.post(
    "/preview-report",
    status_code=status.HTTP_200_OK,
    summary="Preview Report Data",
    description="Get JSON preview of report content without generating PDF"
)
async def preview_report(request: ReportRequest):
    """
    Preview report data as JSON without generating full PDF.

    Useful for UI preview before generating final PDF.

    Args:
        request: ReportRequest data

    Returns:
        JSON object with report preview content
    """

    logger.info(f"Preview requested for screening {request.screening_result.screening_id}")

    # [IMPLEMENTATION]: Build preview data structure
    preview = {
        "screening_id": request.screening_result.screening_id,
        "protocol_id": request.screening_result.protocol_id,
        "patient_id": request.patient_summary.patient_id,
        "trial_info": request.trial_info,
        "overall_status": request.screening_result.overall_status.value,
        "assessment_count": len(request.screening_result.assessments),
        "missing_data_count": len(request.screening_result.missing_data_summary),
        "follow_up_questions_count": len(request.screening_result.follow_up_questions),
        "summary": {
            "meets": sum(
                1 for a in request.screening_result.assessments
                if a.status.value == "meets"
            ),
            "does_not_meet": sum(
                1 for a in request.screening_result.assessments
                if a.status.value == "does_not_meet"
            ),
            "insufficient_data": sum(
                1 for a in request.screening_result.assessments
                if a.status.value == "insufficient_data"
            )
        }
    }

    logger.info("Report preview generated successfully")

    return preview
