"""
TrialMatch AI Screening Data Models

Pydantic models for patient screening requests, assessments, and results.
These models structure the patient-to-criteria matching process.
"""

from enum import Enum
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, validator

from .criteria import CriterionModel, CriterionType


class AssessmentStatus(str, Enum):
    """Status of criterion assessment for a specific patient"""
    MEETS = "meets"
    DOES_NOT_MEET = "does_not_meet"
    INSUFFICIENT_DATA = "insufficient_data"


class ConfidenceLevel(str, Enum):
    """Confidence level in the assessment determination"""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class OverallStatus(str, Enum):
    """Overall trial eligibility status across all criteria"""
    LIKELY_ELIGIBLE = "likely_eligible"
    LIKELY_INELIGIBLE = "likely_ineligible"
    NEEDS_REVIEW = "needs_review"


class PatientSummary(BaseModel):
    """
    De-identified patient summary for screening against trial criteria.
    Contains all relevant clinical information needed for eligibility assessment.

    IMPORTANT: This should only contain de-identified data. Never include:
    - Patient names, dates of birth, medical record numbers
    - Social security numbers, phone numbers, email addresses
    - Specific medical facility names or locations that could identify the patient

    Example:
    {
        "patient_id": "PT-00123",
        "age": 58,
        "sex": "Male",
        "diagnoses": ["Type 2 Diabetes Mellitus", "Hypertension"],
        "medications": [
            {"name": "metformin", "dose": "500mg", "frequency": "twice daily"},
            {"name": "lisinopril", "dose": "10mg", "frequency": "once daily"}
        ],
        "lab_values": {
            "HbA1c": {"value": 7.2, "unit": "%", "date": "2024-02-15"},
            "eGFR": {"value": 92, "unit": "mL/min/1.73m2", "date": "2024-02-15"}
        },
        "comorbidities": ["Hypertension"],
        "surgical_history": ["Appendectomy (1998)"],
        "allergies": ["Penicillin"],
        "free_text_notes": "Patient reports good medication adherence. No recent hospitalizations."
    }
    """

    patient_id: str = Field(..., description="De-identified patient identifier (e.g., 'PT-00123')")
    age: Optional[int] = Field(None, ge=0, le=150, description="Age in years")
    sex: Optional[str] = Field(None, description="Biological sex: 'Male', 'Female', 'Other', or null if unknown")
    diagnoses: List[str] = Field(default_factory=list, description="List of confirmed diagnoses")
    medications: List[Dict[str, str]] = Field(
        default_factory=list,
        description="List of current medications with name, dose, frequency. Example: {'name': 'metformin', 'dose': '500mg', 'frequency': 'twice daily'}"
    )
    lab_values: Dict[str, Dict[str, Any]] = Field(
        default_factory=dict,
        description="Lab values keyed by test name. Example: {'HbA1c': {'value': 7.2, 'unit': '%', 'date': '2024-02-15'}}"
    )
    comorbidities: List[str] = Field(default_factory=list, description="List of concurrent medical conditions")
    surgical_history: List[str] = Field(default_factory=list, description="Past surgical procedures with approximate dates")
    allergies: List[str] = Field(default_factory=list, description="Known allergies (medications, foods, other)")
    free_text_notes: Optional[str] = Field(None, description="Additional clinical notes or observations")

    @validator('patient_id')
    def validate_patient_id(cls, v):
        """Ensure patient_id doesn't contain obviously identifying information"""
        forbidden_patterns = ['dob', 'birth', 'date', 'ssn', 'mrn', 'medical', 'record', 'name', '@']
        if any(pattern.lower() in v.lower() for pattern in forbidden_patterns):
            raise ValueError(
                f"patient_id '{v}' appears to contain identifying information. "
                "Use a de-identified identifier like 'PT-123' or a hash."
            )
        return v

    @validator('free_text_notes')
    def validate_free_text_notes(cls, v):
        """Ensure free text doesn't contain obvious identifiers"""
        if v is None:
            return v
        text_lower = v.lower()
        if any(phrase in text_lower for phrase in ['patient name', 'born', 'dob', 'ssn', 'mrn', 'hospital']):
            raise ValueError(
                "free_text_notes appear to contain identifying information. "
                "Only include de-identified clinical data."
            )
        return v

    class Config:
        use_enum_values = False


class CriterionAssessment(BaseModel):
    """
    Assessment of how a single criterion applies to a patient.

    Example (Meets):
    {
        "criterion_id": "I1",
        "status": "meets",
        "confidence": "high",
        "reasoning": "Patient has confirmed Type 2 Diabetes diagnosis documented in medical record from 2018, exceeding the 6-month requirement.",
        "missing_data": [],
        "evidence_cited": ["Diagnosis: Type 2 Diabetes Mellitus from patient history"]
    }

    Example (Does Not Meet):
    {
        "criterion_id": "E3",
        "status": "does_not_meet",
        "confidence": "high",
        "reasoning": "Patient has stage 3 chronic kidney disease with eGFR of 45 mL/min/1.73m2, which exceeds the exclusion threshold of eGFR < 60.",
        "missing_data": [],
        "evidence_cited": ["eGFR: 45 mL/min/1.73m2"]
    }

    Example (Insufficient Data):
    {
        "criterion_id": "I4",
        "status": "insufficient_data",
        "confidence": "medium",
        "reasoning": "Criterion requires LVEF value. While patient has history of heart failure, no recent echocardiogram result provided.",
        "missing_data": ["LVEF percentage from recent echocardiogram"],
        "evidence_cited": []
    }
    """

    criterion_id: str = Field(..., description="ID of the criterion being assessed (e.g., 'I1')")
    status: AssessmentStatus = Field(..., description="Assessment outcome: meets, does_not_meet, or insufficient_data")
    confidence: ConfidenceLevel = Field(..., description="Confidence level in this assessment")
    reasoning: str = Field(..., description="2-3 sentence explanation of the assessment decision")
    missing_data: List[str] = Field(default_factory=list, description="Data items needed if status is insufficient_data")
    evidence_cited: List[str] = Field(default_factory=list, description="Specific patient data points used in assessment")

    @validator('reasoning')
    def validate_reasoning(cls, v):
        """Ensure reasoning is meaningful"""
        if not v or len(v.strip()) < 10:
            raise ValueError("reasoning must be at least 10 characters")
        if len(v) > 500:
            raise ValueError("reasoning cannot exceed 500 characters")
        return v

    @validator('criterion_id')
    def validate_criterion_id(cls, v):
        """Ensure criterion_id format is valid"""
        if not (v.startswith('I') or v.startswith('E')):
            raise ValueError(f"criterion_id must start with 'I' or 'E', got '{v}'")
        return v

    class Config:
        use_enum_values = False


class ScreeningResult(BaseModel):
    """
    Complete screening result for a patient against a protocol's criteria.
    Returned by POST /api/screen-patient endpoint.

    Example:
    {
        "screening_id": "SCR-20240324-001",
        "protocol_id": "xyz789",
        "patient_id": "PT-00123",
        "overall_status": "likely_eligible",
        "assessments": [...],
        "missing_data_summary": ["Recent HbA1c result (within 3 months)"],
        "follow_up_questions": [
            "What is the patient's current eGFR? (Required for kidney function assessment)"
        ],
        "assessed_at": "2024-03-24T10:35:00Z"
    }
    """

    screening_id: str = Field(..., description="Unique identifier for this screening (e.g., 'SCR-20240324-001')")
    protocol_id: str = Field(..., description="Protocol ID that was screened against")
    patient_id: str = Field(..., description="Patient ID that was screened")
    overall_status: OverallStatus = Field(..., description="Overall trial eligibility: likely_eligible, likely_ineligible, or needs_review")
    assessments: List[CriterionAssessment] = Field(..., description="Per-criterion assessments")
    missing_data_summary: List[str] = Field(default_factory=list, description="Aggregated list of missing data across all criteria")
    follow_up_questions: List[str] = Field(default_factory=list, description="Suggested follow-up questions for clinicians")
    assessed_at: datetime = Field(default_factory=datetime.utcnow, description="Timestamp of screening")

    @validator('assessments')
    def validate_assessments_not_empty(cls, v):
        """Ensure at least one assessment was performed"""
        if not v or len(v) == 0:
            raise ValueError("At least one criterion assessment must be present")
        return v

    class Config:
        use_enum_values = False


class ScreeningRequest(BaseModel):
    """
    Request payload for POST /api/screen-patient.
    Contains patient summary and criteria to screen against.
    """

    patient_summary: PatientSummary = Field(..., description="De-identified patient data")
    criteria: List[CriterionModel] = Field(..., description="List of criteria to evaluate")
    protocol_id: Optional[str] = Field(None, description="Optional protocol ID for tracking")

    @validator('criteria')
    def validate_criteria_not_empty(cls, v):
        """Ensure criteria list is not empty"""
        if not v or len(v) == 0:
            raise ValueError("At least one criterion must be provided for screening")
        return v

    class Config:
        use_enum_values = False


class ReportRequest(BaseModel):
    """
    Request payload for POST /api/export-report.
    Contains all data needed to generate a downloadable PDF report.
    """

    screening_result: ScreeningResult = Field(..., description="Complete screening result")
    patient_summary: PatientSummary = Field(..., description="Patient data used in screening")
    trial_info: Dict[str, str] = Field(..., description="Trial metadata: name, phase, sponsor, etc.")

    class Config:
        use_enum_values = False


class ReportData(BaseModel):
    """
    Complete data structure for report generation.
    Combines screening result with metadata for PDF rendering.
    """

    screening_id: str = Field(..., description="Screening ID")
    protocol_id: str = Field(..., description="Protocol ID")
    patient_id: str = Field(..., description="Patient ID")
    trial_name: str = Field(..., description="Clinical trial name")
    trial_phase: Optional[str] = Field(None, description="Trial phase (I, II, III, IV)")
    trial_sponsor: Optional[str] = Field(None, description="Sponsoring organization")
    overall_status: OverallStatus = Field(..., description="Overall eligibility status")
    assessments: List[CriterionAssessment] = Field(..., description="Criterion assessments")
    missing_data_summary: List[str] = Field(default_factory=list, description="Missing data items")
    follow_up_questions: List[str] = Field(default_factory=list, description="Follow-up questions")
    generated_at: datetime = Field(default_factory=datetime.utcnow, description="Report generation timestamp")
    version: str = Field(default="1.0", description="Report format version")

    class Config:
        use_enum_values = False
