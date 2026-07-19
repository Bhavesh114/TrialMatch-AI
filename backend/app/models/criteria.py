"""
TrialMatch AI Criteria Data Models

Pydantic models for representing clinical trial eligibility criteria and extraction results.
These models enforce strict typing and validation for criteria data structures.
"""

from enum import Enum
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, validator


class CriterionType(str, Enum):
    """Classification of criterion as inclusion or exclusion"""
    INCLUSION = "inclusion"
    EXCLUSION = "exclusion"


class CriterionCategory(str, Enum):
    """Semantic categories for grouping related criteria"""
    DEMOGRAPHIC = "demographic"
    DIAGNOSIS = "diagnosis"
    DISEASE_SEVERITY = "disease_severity"
    LAB_VALUES = "lab_values"
    COMORBIDITY = "comorbidity"
    MEDICATION = "medication"
    ORGAN_FUNCTION = "organ_function"
    PREGNANCY_STATUS = "pregnancy_status"
    PRIOR_TREATMENT = "prior_treatment"
    SURGERY_HISTORY = "surgery_history"
    CONTRAINDICATION = "contraindication"
    OTHER = "other"


class DataPoint(BaseModel):
    """
    Represents a single data point needed to evaluate a criterion.
    Examples: age, HbA1c value, LVEF percentage, diagnosis name
    """
    name: str = Field(..., description="Name of the data point (e.g., 'age', 'HbA1c')")
    type: str = Field(..., description="Data type: 'numeric', 'categorical', 'date', 'boolean'")
    unit: Optional[str] = Field(None, description="Unit if applicable (e.g., 'mg/dL', 'years')")
    required: bool = Field(default=True, description="Whether this data point is required to evaluate the criterion")


class LogicExpression(BaseModel):
    """
    Represents compound logic in criteria (e.g., "age >= 18 AND age <= 65 AND diagnosis = Type 2 Diabetes").
    Parsed from natural language to structured form for evaluation.
    """
    expression: str = Field(..., description="Human-readable logic expression")
    conditions: List[Dict[str, Any]] = Field(default_factory=list, description="List of parsed conditions")
    operators: List[str] = Field(default_factory=list, description="Logical operators: 'AND', 'OR', 'NOT'")
    complexity: str = Field(default="simple", description="'simple' (single condition) or 'compound' (multiple)")


class CriterionModel(BaseModel):
    """
    Represents a single clinical trial eligibility criterion extracted from protocol.

    Example (Inclusion):
    {
        "criterion_id": "I1",
        "type": "inclusion",
        "description": "Diagnosed with Type 2 Diabetes Mellitus for at least 6 months",
        "category": "diagnosis",
        "source_text": "Patients must have a confirmed diagnosis of Type 2 DM for at least 6 months",
        "data_points_needed": [{"name": "diagnosis", "type": "categorical"}, {"name": "diagnosis_duration", "type": "numeric", "unit": "months"}],
        "logic": {"expression": "diagnosis = 'Type 2 Diabetes' AND duration >= 6 months", "complexity": "compound"},
        "confidence": 0.95,
        "notes": ""
    }
    """

    criterion_id: str = Field(..., description="Unique identifier (e.g., 'I1', 'E2'). Format: [I|E] + number")
    type: CriterionType = Field(..., description="Whether this is an inclusion or exclusion criterion")
    description: str = Field(..., description="Clear, concise description of the criterion")
    category: CriterionCategory = Field(default=CriterionCategory.OTHER, description="Semantic category for grouping")
    source_text: Optional[str] = Field(None, description="Original text from the protocol document")
    data_points_needed: List[DataPoint] = Field(default_factory=list, description="Data points required to evaluate this criterion")
    logic: Optional[LogicExpression] = Field(None, description="Structured representation of any compound logic")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Extraction confidence score (0-1)")
    notes: Optional[str] = Field(None, description="Additional clarifications or edge cases for this criterion")

    @validator('criterion_id')
    def validate_criterion_id(cls, v):
        """Ensure criterion_id follows format I/E + number"""
        if not (v.startswith('I') or v.startswith('E')):
            raise ValueError(f"criterion_id must start with 'I' or 'E', got '{v}'")
        if len(v) < 2 or not v[1:].isdigit():
            raise ValueError(f"criterion_id must be format I/E + number, got '{v}'")
        return v

    @validator('description')
    def validate_description(cls, v):
        """Ensure description is not empty and reasonable length"""
        if not v or len(v.strip()) == 0:
            raise ValueError("description cannot be empty")
        if len(v) > 1000:
            raise ValueError("description cannot exceed 1000 characters")
        return v.strip()

    class Config:
        use_enum_values = False


class ExtractionWarning(BaseModel):
    """
    Represents a warning or note during extraction process.
    Examples: scanned PDF detected, low confidence on criterion, ambiguous language found
    """
    severity: str = Field(..., description="'info', 'warning', or 'error'")
    code: str = Field(..., description="Machine-readable warning code (e.g., 'SCANNED_PDF', 'LOW_CONFIDENCE')")
    message: str = Field(..., description="Human-readable warning message")


class CriteriaExtractionResult(BaseModel):
    """
    Complete result of extracting criteria from a protocol PDF.
    Returned by POST /api/extract-criteria endpoint.

    Example:
    {
        "protocol_id": "xyz789",
        "trial_name": "LANDMARK-2 Heart Failure Study",
        "criteria": [I1, I2, ..., E1, E2, ...],
        "extraction_confidence": 0.89,
        "extraction_method": "pymupdf",
        "page_count": 42,
        "warnings": [
            {"severity": "info", "code": "PAGE_COUNT", "message": "Protocol spans 42 pages"}
        ],
        "extracted_at": "2024-03-24T10:30:00Z",
        "inclusion_count": 10,
        "exclusion_count": 9
    }
    """

    protocol_id: str = Field(..., description="Unique identifier for this protocol (hash-based or UUID)")
    trial_name: Optional[str] = Field(None, description="Name of the clinical trial if detected")
    criteria: List[CriterionModel] = Field(..., description="List of extracted criteria")
    extraction_confidence: float = Field(ge=0.0, le=1.0, description="Overall confidence score for extraction (0-1)")
    extraction_method: str = Field(default="pymupdf", description="'pymupdf', 'ocr', or 'hybrid'")
    page_count: int = Field(default=0, description="Total number of pages in the PDF")
    warnings: List[ExtractionWarning] = Field(default_factory=list, description="List of warnings during extraction")
    extracted_at: datetime = Field(default_factory=datetime.utcnow, description="Timestamp of extraction")
    inclusion_count: int = Field(default=0, description="Count of inclusion criteria")
    exclusion_count: int = Field(default=0, description="Count of exclusion criteria")

    @validator('criteria')
    def validate_criteria_not_empty(cls, v):
        """Ensure at least one criterion was extracted"""
        if not v or len(v) == 0:
            raise ValueError("At least one criterion must be extracted from the protocol")
        return v

    @validator('protocol_id')
    def validate_protocol_id(cls, v):
        """Ensure protocol_id is not empty"""
        if not v or len(v.strip()) == 0:
            raise ValueError("protocol_id cannot be empty")
        return v

    def __init__(self, **data):
        """Custom initialization to auto-calculate inclusion/exclusion counts"""
        super().__init__(**data)
        self.inclusion_count = sum(1 for c in self.criteria if c.type == CriterionType.INCLUSION)
        self.exclusion_count = sum(1 for c in self.criteria if c.type == CriterionType.EXCLUSION)

    class Config:
        use_enum_values = False
