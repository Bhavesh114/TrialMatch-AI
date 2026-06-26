# Data Models Reference
## TrialMatch AI — Clinical Trial Eligibility Screener

**Document Version:** 1.0
**Last Updated:** 2026-03-24
**Status:** Final - MVP v1.0
**Audience:** Backend engineers, frontend engineers, QA

---

## Overview

This document defines all data models used in TrialMatch AI. Models are defined in three layers:
1. **Backend (Pydantic):** Python validation and serialization
2. **Frontend (TypeScript):** Component props and state types
3. **API (JSON):** Serialized request/response bodies

---

## Backend Data Models (Pydantic - Python)

### Core Clinical Models

#### CriterionModel
Represents a single inclusion or exclusion criterion extracted from a protocol.

```python
from pydantic import BaseModel
from typing import Optional, List

class CriterionModel(BaseModel):
    """A single eligibility criterion from a clinical trial protocol."""

    criterion_id: str
        # Format: I1, I2, ... for inclusion; E1, E2, ... for exclusion
        # Example: "I1", "E5"
        # Validation: Must match regex ^[IE]\d+$

    type: Literal["inclusion", "exclusion"]
        # Must match prefix of criterion_id (I* → inclusion, E* → exclusion)

    description: str
        # Plain language, 1-2 sentences
        # Suitable for reading aloud or in reports
        # Example: "Patients aged 18-75 years at time of enrollment"
        # Validation: 10-500 characters

    category: Literal[
        "demographics",
        "diagnosis",
        "lab_values",
        "medications",
        "medical_history",
        "procedures",
        "functional_status",
        "other"
    ]
        # Categorization helps with organization and filtering
        # Required to be exactly one of the 8 categories

    data_points_needed: List[str]
        # Specific data elements needed to evaluate criterion
        # Example: ["age", "date_of_birth"]
        # Example: ["HbA1c_value", "HbA1c_date"]
        # Each item should be specific, not generic
        # Validation: Min 0 items (can be empty for "other"), max 20 items

    logic: Optional[str] = None
        # AND/OR/NOT logic, temporal requirements
        # Example: "18 ≤ age ≤ 75"
        # Example: "Age 50-75 AND eGFR ≥60"
        # Example: "Diagnosed within 6 months"
        # NULL if criterion is simple/standalone
        # Validation: Max 500 characters

    class Config:
        json_schema_extra = {
            "example": {
                "criterion_id": "I1",
                "type": "inclusion",
                "description": "Age 18-75 years at enrollment",
                "category": "demographics",
                "data_points_needed": ["age"],
                "logic": "18 ≤ age ≤ 75"
            }
        }
```

---

#### CriteriaExtractionResult
Complete result of extracting criteria from a protocol.

```python
from datetime import datetime

class CriteriaExtractionResult(BaseModel):
    """Result of LLM-based criteria extraction from a clinical trial protocol."""

    criteria: List[CriterionModel]
        # Array of extracted criteria
        # Minimum: 0 (empty protocol or extraction failure)
        # Maximum: 80 (safety limit to prevent token explosion)

    protocol_metadata: dict
        # Metadata extracted from protocol text
        # Fields (all optional):
        # {
        #   "title": str (trial title)
        #   "version": str (protocol version)
        #   "nct_number": str (NCT number, e.g., NCT05123456)
        #   "sponsor": str (sponsor name)
        #   "estimated_enrollment": int
        #   "primary_outcome": str
        #   "study_duration_months": int
        # }
        # Example:
        # {
        #   "title": "A Phase II Study of Drug X in Type 2 Diabetes",
        #   "version": "2.0",
        #   "nct_number": "NCT05123456",
        #   "sponsor": "Pharma Inc.",
        #   "estimated_enrollment": 200
        # }

    text_confidence: float
        # Confidence in text extraction quality (0.0 - 1.0)
        # 0.98+ : Searchable PDF with clear text
        # 0.85-0.97 : Searchable PDF with some noise
        # 0.65-0.84 : Scanned PDF with OCR
        # <0.65 : Low quality; user warned

    extraction_time_ms: int
        # Time to run extraction in milliseconds
        # Typical: 5,000-12,000 ms
        # Validation: >0, <120,000 (120 seconds)

    extracted_at: datetime
        # ISO8601 timestamp of extraction
        # Example: 2026-03-24T10:30:00Z

    class Config:
        json_schema_extra = {
            "example": {
                "criteria": [
                    {
                        "criterion_id": "I1",
                        "type": "inclusion",
                        "description": "Age 18-75 years",
                        "category": "demographics",
                        "data_points_needed": ["age"],
                        "logic": "18 ≤ age ≤ 75"
                    }
                ],
                "protocol_metadata": {
                    "title": "A Phase II Study of Drug X",
                    "version": "2.0",
                    "nct_number": "NCT05123456"
                },
                "text_confidence": 0.98,
                "extraction_time_ms": 5200,
                "extracted_at": "2026-03-24T10:30:00Z"
            }
        }
```

---

### Patient and Screening Models

#### PatientSummary
Patient demographic and clinical data (de-identified).

```python
from typing import Optional, List, Dict, Any

class LabValue(BaseModel):
    """Single lab test result."""

    name: str
        # Test name: HbA1c, eGFR, Creatinine, ALT, etc.
        # Validation: 1-100 characters

    value: float
        # Numeric result
        # Example: 8.2 (for HbA1c), 78 (for eGFR)

    unit: str
        # Unit of measurement: %, mL/min, mg/dL, U/L, etc.
        # Validation: 1-20 characters

    date: Optional[str] = None
        # ISO8601 date of test (YYYY-MM-DD)
        # Optional; if missing, assume recent
        # Example: "2024-03-10"

    class Config:
        json_schema_extra = {
            "example": {
                "name": "HbA1c",
                "value": 8.2,
                "unit": "%",
                "date": "2024-03-10"
            }
        }

class StructuredPatientData(BaseModel):
    """Structured patient data fields."""

    age: Optional[int] = None
        # Age in years
        # Validation: 18-120

    sex: Optional[str] = None
        # Male, Female, Other
        # Validation: Must be one of those three

    primary_diagnosis: Optional[str] = None
        # Main diagnosis (e.g., Type 2 Diabetes Mellitus)
        # Validation: Max 200 characters

    secondary_diagnoses: Optional[List[str]] = None
        # Additional diagnoses
        # Example: ["Hypertension", "Osteoarthritis"]
        # Validation: Max 10 diagnoses

    current_medications: Optional[List[str]] = None
        # Current meds with dosages (free text)
        # Example: ["Metformin 1000mg BID", "Lisinopril 10mg daily"]
        # Validation: Max 30 medications

    lab_values: Optional[List[LabValue]] = None
        # Recent lab results
        # Validation: Max 50 lab values

    comorbidities: Optional[List[str]] = None
        # Pre-existing conditions
        # Example: ["Hypertension", "Kidney disease"]
        # Validation: Max 20 comorbidities

    functional_status: Optional[str] = None
        # Performance status: Independent, Assisted, Dependent
        # Validation: One of those three

    procedures: Optional[List[str]] = None
        # Prior procedures/surgeries
        # Example: ["Appendectomy (2005)", "Knee replacement (2020)"]
        # Validation: Max 20 procedures

    allergies: Optional[List[str]] = None
        # Drug/food allergies
        # Example: ["Penicillin", "Sulfa"]
        # Validation: Max 10 allergies

    pregnancy_status: Optional[str] = None
        # Not pregnant, Pregnant, Unknown
        # Validation: One of those three

    additional_notes: Optional[str] = None
        # Any additional information
        # Validation: Max 500 characters

    class Config:
        json_schema_extra = {
            "example": {
                "age": 55,
                "sex": "Female",
                "primary_diagnosis": "Type 2 Diabetes Mellitus",
                "current_medications": ["Metformin 1000mg BID"],
                "lab_values": [
                    {"name": "HbA1c", "value": 8.2, "unit": "%", "date": "2024-03-10"}
                ],
                "comorbidities": ["Hypertension"]
            }
        }

class PatientSummary(BaseModel):
    """Patient clinical data (de-identified)."""

    free_text: Optional[str] = None
        # Unstructured clinical notes
        # Example: "55-year-old female with Type 2 Diabetes. HbA1c 8.2%..."
        # Validation: Max 5,000 characters

    structured: Optional[StructuredPatientData] = None
        # Structured form fields

    # Validation: Either free_text OR structured must be provided (not both optional)
    # At least one must be non-null

    @validator("*")
    def at_least_one_summary(cls, v):
        """Ensure either free_text or structured is provided."""
        # Custom validation in actual implementation
        pass

    class Config:
        json_schema_extra = {
            "example": {
                "free_text": "55-year-old female, Type 2 Diabetes, HbA1c 8.2%, on Metformin"
            }
            # OR
            # "example": {
            #     "structured": {
            #         "age": 55,
            #         "primary_diagnosis": "Type 2 Diabetes Mellitus"
            #     }
            # }
        }
```

---

#### CriterionAssessment
Assessment of patient against one criterion.

```python
class CriterionAssessment(BaseModel):
    """Assessment of patient against one eligibility criterion."""

    criterion_id: str
        # Link back to original criterion (I1, E2, etc.)
        # Validation: Must match regex ^[IE]\d+$

    status: Literal["MEETS", "DOES_NOT_MEET", "INSUFFICIENT_DATA"]
        # MEETS: Patient clearly meets criterion
        # DOES_NOT_MEET: Patient clearly does not meet criterion
        # INSUFFICIENT_DATA: Data needed to assess criterion is missing

    confidence: Literal["high", "medium", "low"]
        # HIGH: Criterion clear + patient data complete
        # MEDIUM: Criterion clear but data incomplete, OR criterion ambiguous but data complete
        # LOW: Both criterion and patient data ambiguous

    reasoning: str
        # 2-3 sentence explanation citing specific evidence
        # MUST cite actual values from patient summary
        # Example: "Patient HbA1c 8.2% exceeds criterion limit of 8.0%."
        # Validation: 10-500 characters

    missing_data: Optional[List[str]] = None
        # If status = INSUFFICIENT_DATA, what specific data is needed
        # Example: ["Recent HbA1c value", "Lab date"]
        # If status ≠ INSUFFICIENT_DATA, this must be NULL
        # Validation: Max 10 items if provided

    class Config:
        json_schema_extra = {
            "example": {
                "criterion_id": "I1",
                "status": "MEETS",
                "confidence": "high",
                "reasoning": "Patient age 55 falls within criterion range of 18-75 years.",
                "missing_data": null
            }
        }
```

---

#### ScreeningResult
Complete screening assessment for one patient against all criteria.

```python
class MissingDataItem(BaseModel):
    """Aggregated missing data item."""

    name: str
        # Name of the missing data
        # Example: "Recent HbA1c value"

    count: int
        # Number of criteria requiring this data
        # Example: 3 (three criteria all need HbA1c)

    criterion_ids: List[str]
        # Which criteria need this data
        # Example: ["I3", "E1", "E2"]

class OverallSummary(BaseModel):
    """Overall screening summary."""

    eligible_count: int
        # Number of criteria with MEETS

    ineligible_count: int
        # Number with DOES_NOT_MEET

    insufficient_data_count: int
        # Number with INSUFFICIENT_DATA

    primary_ineligibility_reason: Optional[str] = None
        # If overall_status = NOT_ELIGIBLE, brief explanation
        # Example: "HbA1c (8.2%) exceeds upper limit of 8.0%"
        # NULL if overall_status = ELIGIBLE or REQUIRES_REVIEW

class ScreeningResult(BaseModel):
    """Complete screening result for one patient."""

    overall_status: Literal["ELIGIBLE", "NOT_ELIGIBLE", "REQUIRES_REVIEW"]
        # ELIGIBLE: All inclusion criteria MEETS, no exclusion DOES_NOT_MEET, no INSUFFICIENT_DATA
        # NOT_ELIGIBLE: ≥1 inclusion DOES_NOT_MEET OR ≥1 exclusion DOES_NOT_MEET
        # REQUIRES_REVIEW: ≥1 INSUFFICIENT_DATA (need coordinator investigation)

    criteria_assessments: List[CriterionAssessment]
        # One assessment per criterion
        # Validation: Min 1, max 80

    missing_data_aggregated: List[MissingDataItem]
        # De-duplicated list of all missing data across all INSUFFICIENT_DATA criteria
        # Empty list if no missing data

    overall_summary: OverallSummary
        # High-level summary of results

    screening_time_ms: int
        # Time to run screening in milliseconds
        # Typical: 3,000-8,000 ms
        # Validation: >0, <120,000

    screened_at: datetime
        # ISO8601 timestamp of screening
        # Example: 2026-03-24T10:35:00Z

    class Config:
        json_schema_extra = {
            "example": {
                "overall_status": "ELIGIBLE",
                "criteria_assessments": [
                    {
                        "criterion_id": "I1",
                        "status": "MEETS",
                        "confidence": "high",
                        "reasoning": "Patient age 55 within range 18-75.",
                        "missing_data": null
                    }
                ],
                "missing_data_aggregated": [],
                "overall_summary": {
                    "eligible_count": 3,
                    "ineligible_count": 0,
                    "insufficient_data_count": 0,
                    "primary_ineligibility_reason": null
                },
                "screening_time_ms": 3100,
                "screened_at": "2026-03-24T10:35:00Z"
            }
        }
```

---

### Session and Request Models

#### ScreeningRequest
Request to screen patient against criteria.

```python
class ScreeningRequest(BaseModel):
    """Request to screen a patient."""

    criteria: List[CriterionModel]
        # Array of criteria from extraction
        # Validation: Min 1, max 80

    patient_summary: PatientSummary
        # Patient data (de-identified)
        # Validation: At least free_text or structured provided

    class Config:
        json_schema_extra = {
            "example": {
                "criteria": [
                    {
                        "criterion_id": "I1",
                        "type": "inclusion",
                        "description": "Age 18-75",
                        "category": "demographics",
                        "data_points_needed": ["age"],
                        "logic": "18 ≤ age ≤ 75"
                    }
                ],
                "patient_summary": {
                    "free_text": "55-year-old female..."
                }
            }
        }
```

---

#### ReportRequest and ReportData
Request and content for PDF report generation.

```python
class ReportRequest(BaseModel):
    """Request to generate a screening report."""

    # No required fields; uses session data
    # Future: could allow custom report options

    class Config:
        json_schema_extra = {
            "example": {}
        }

class ReportData(BaseModel):
    """Data to include in PDF report."""

    protocol_title: str
    protocol_version: Optional[str]
    nct_number: Optional[str]
    patient_summary: str  # De-identified, as entered by coordinator
    overall_status: str
    criteria_assessments: List[CriterionAssessment]
    missing_data: List[str]
    generated_at: datetime
    report_filename: str
```

---

#### HealthCheckResponse
Response from /health endpoint.

```python
class HealthCheck(BaseModel):
    """Service health status."""

    status: Literal["ok", "degraded", "critical"]
        # ok: All systems operational
        # degraded: Some services down but API still functions
        # critical: Service unavailable

    version: str
        # API version (e.g., "1.0.0")

    timestamp: datetime
        # ISO8601 timestamp

    checks: dict
        # Health status of each dependency
        # {
        #   "anthropic_api": "ok" | "error",
        #   "s3": "ok" | "error",
        #   "memory": "ok" | "error"
        # }

    class Config:
        json_schema_extra = {
            "example": {
                "status": "ok",
                "version": "1.0.0",
                "checks": {
                    "anthropic_api": "ok",
                    "s3": "ok",
                    "memory": "ok"
                },
                "timestamp": "2026-03-24T10:30:00Z"
            }
        }
```

---

## Frontend Data Models (TypeScript)

### Core Types

```typescript
// types/Protocol.ts

export interface Protocol {
  id: string                    // UUID
  title: string                 // Trial title
  version?: string              // Protocol version
  nctNumber?: string            // NCT number
  sponsor?: string              // Sponsor name
  s3Path: string                // S3 temporary storage path
  textConfidence: number        // 0-1
  extractedAt: string           // ISO8601
}

// types/Criterion.ts

export type CriteriaCategory =
  | 'demographics'
  | 'diagnosis'
  | 'lab_values'
  | 'medications'
  | 'medical_history'
  | 'procedures'
  | 'functional_status'
  | 'other'

export interface Criterion {
  criterion_id: string          // I1, I2, E1, E2...
  type: 'inclusion' | 'exclusion'
  description: string
  category: CriteriaCategory
  data_points_needed: string[]
  logic?: string                // AND/OR logic
  edited?: boolean              // If user modified it
}

// types/Patient.ts

export interface LabValue {
  name: string                  // Test name
  value: number                 // Numeric result
  unit: string                  // Unit of measurement
  date?: string                 // ISO8601 date
}

export interface StructuredPatientData {
  age?: number
  sex?: string                  // Male, Female, Other
  primaryDiagnosis?: string
  secondaryDiagnoses?: string[]
  currentMedications?: string[]
  labValues?: LabValue[]
  comorbidities?: string[]
  functionalStatus?: string     // Independent, Assisted, Dependent
  procedures?: string[]
  allergies?: string[]
  pregnancyStatus?: string      // Not pregnant, Pregnant, Unknown
  additionalNotes?: string
}

export interface PatientSummary {
  freeText?: string
  structured?: StructuredPatientData
  piiWarning?: boolean          // If PII detected
}

// types/Screening.ts

export interface CriterionAssessment {
  criterion_id: string
  status: 'MEETS' | 'DOES_NOT_MEET' | 'INSUFFICIENT_DATA'
  confidence: 'high' | 'medium' | 'low'
  reasoning: string
  missing_data?: string[]
  overridden?: boolean          // If coordinator changed it
}

export interface MissingDataItem {
  name: string
  count: number
  criterion_ids: string[]
}

export interface OverallSummary {
  eligible_count: number
  ineligible_count: number
  insufficient_data_count: number
  primary_ineligibility_reason?: string
}

export interface ScreeningResult {
  overall_status: 'ELIGIBLE' | 'NOT_ELIGIBLE' | 'REQUIRES_REVIEW'
  criteria_assessments: CriterionAssessment[]
  missing_data_aggregated: MissingDataItem[]
  overall_summary: OverallSummary
  screened_at: string           // ISO8601
  screening_time_ms: number
}
```

---

### Component Props Types

```typescript
// types/ComponentProps.ts

export interface ProtocolUploadProps {
  onSuccess: (protocol: Protocol) => void
  onError: (error: string) => void
  maxFileSizeMB?: number        // Default 50
}

export interface CriteriaReviewProps {
  protocol: Protocol
  criteria: Criterion[]
  onUpdate: (criteria: Criterion[]) => void
  onNext: () => void
  onCancel: () => void
}

export interface PatientInputProps {
  onSubmit: (summary: PatientSummary) => void
  onCancel: () => void
  inputMode?: 'free-text' | 'structured' | 'both'
}

export interface ScreeningResultsProps {
  result: ScreeningResult
  protocol: Protocol
  criteria: Criterion[]
  onExport: () => void
  onEdit: () => void
}

export interface ReportExportProps {
  protocol: Protocol
  criteria: Criterion[]
  result: ScreeningResult
  onDownload: (filename: string) => void
}
```

---

### Context Types

```typescript
// types/ScreeningContext.ts

export interface ScreeningContextType {
  protocol?: Protocol
  criteria: Criterion[]
  patientSummary?: PatientSummary
  screeningResults?: ScreeningResult
  uiState: UIState

  // Actions
  setProtocol: (protocol: Protocol) => void
  setCriteria: (criteria: Criterion[]) => void
  updateCriterion: (id: string, updates: Partial<Criterion>) => void
  deleteCriterion: (id: string) => void
  addCriterion: (criterion: Criterion) => void
  revertCriteria: () => void
  setPatientSummary: (summary: PatientSummary) => void
  setScreeningResults: (results: ScreeningResult) => void
  setUIState: (updates: Partial<UIState>) => void
  clearSession: () => void
}

export interface UIState {
  currentPage: 'home' | 'extract' | 'screen' | 'report'
  loading: boolean
  error?: string
  progress?: {
    stage: string
    percent: number
  }
  lastAction: string
}
```

---

## JSON Schema Examples

### Complete Extraction Response

```json
{
  "protocol": {
    "id": "proto-550e8400-e29b-41d4-a716-446655440000",
    "title": "A Phase II Randomized, Double-Blind, Placebo-Controlled Study of Drug X in Patients with Type 2 Diabetes Mellitus",
    "version": "2.0",
    "nct_number": "NCT05123456",
    "sponsor": "Pharma Inc.",
    "estimated_enrollment": 200,
    "s3_path": "s3://trialmatch-pdfs-prod/proto-550e8400.pdf",
    "text_confidence": 0.98,
    "extracted_at": "2026-03-24T10:30:00Z"
  },
  "criteria": [
    {
      "criterion_id": "I1",
      "type": "inclusion",
      "description": "Age between 18 and 75 years (inclusive) at time of enrollment",
      "category": "demographics",
      "data_points_needed": ["age", "date_of_birth"],
      "logic": "18 ≤ age ≤ 75"
    },
    {
      "criterion_id": "I2",
      "type": "inclusion",
      "description": "Confirmed diagnosis of Type 2 Diabetes Mellitus for at least 12 weeks prior to enrollment",
      "category": "diagnosis",
      "data_points_needed": ["diabetes_type", "diagnosis_date"],
      "logic": "Type 2 DM diagnosis >12 weeks before enrollment"
    },
    {
      "criterion_id": "I3",
      "type": "inclusion",
      "description": "HbA1c between 7.0% and 10.5% at screening visit",
      "category": "lab_values",
      "data_points_needed": ["HbA1c_value", "HbA1c_date"],
      "logic": "7.0 ≤ HbA1c ≤ 10.5"
    },
    {
      "criterion_id": "I4",
      "type": "inclusion",
      "description": "Estimated Glomerular Filtration Rate (eGFR) ≥60 mL/min/1.73m²",
      "category": "lab_values",
      "data_points_needed": ["eGFR", "eGFR_date"],
      "logic": "eGFR ≥ 60"
    },
    {
      "criterion_id": "E1",
      "type": "exclusion",
      "description": "Type 1 Diabetes Mellitus or secondary diabetes",
      "category": "diagnosis",
      "data_points_needed": ["diabetes_type"],
      "logic": null
    },
    {
      "criterion_id": "E2",
      "type": "exclusion",
      "description": "Acute coronary syndrome, myocardial infarction, or stroke within 6 months prior to screening",
      "category": "medical_history",
      "data_points_needed": ["cardiovascular_events", "event_dates"],
      "logic": "No CVD events within 6 months"
    },
    {
      "criterion_id": "E3",
      "type": "exclusion",
      "description": "Currently pregnant or planning pregnancy during trial period",
      "category": "functional_status",
      "data_points_needed": ["pregnancy_status", "plans_for_pregnancy"],
      "logic": "NOT pregnant AND NOT planning pregnancy"
    }
  ],
  "text_confidence": 0.98,
  "extraction_time_ms": 5200
}
```

### Complete Screening Response

```json
{
  "overall_status": "REQUIRES_REVIEW",
  "criteria_assessments": [
    {
      "criterion_id": "I1",
      "status": "MEETS",
      "confidence": "high",
      "reasoning": "Patient age 55 falls within criterion range of 18-75 years.",
      "missing_data": null
    },
    {
      "criterion_id": "I2",
      "status": "MEETS",
      "confidence": "high",
      "reasoning": "Patient has confirmed Type 2 Diabetes Mellitus diagnosed in 2019, which is more than 12 weeks prior to this evaluation.",
      "missing_data": null
    },
    {
      "criterion_id": "I3",
      "status": "DOES_NOT_MEET",
      "confidence": "high",
      "reasoning": "Patient HbA1c is 8.2%, which exceeds the upper limit of 8.0% specified in the criterion.",
      "missing_data": null
    },
    {
      "criterion_id": "I4",
      "status": "MEETS",
      "confidence": "high",
      "reasoning": "Patient eGFR 78 mL/min/1.73m² exceeds the minimum threshold of 60 mL/min/1.73m².",
      "missing_data": null
    },
    {
      "criterion_id": "E1",
      "status": "MEETS",
      "confidence": "high",
      "reasoning": "Patient has Type 2 Diabetes Mellitus, not Type 1 or secondary diabetes. Exclusion criterion not triggered.",
      "missing_data": null
    },
    {
      "criterion_id": "E2",
      "status": "MEETS",
      "confidence": "high",
      "reasoning": "Patient has no history of acute coronary syndrome, myocardial infarction, or stroke. Exclusion criterion not triggered.",
      "missing_data": null
    },
    {
      "criterion_id": "E3",
      "status": "MEETS",
      "confidence": "high",
      "reasoning": "Patient is female, 55 years old, not pregnant, and has no plans for pregnancy during study period.",
      "missing_data": null
    }
  ],
  "missing_data_aggregated": [],
  "overall_summary": {
    "eligible_count": 5,
    "ineligible_count": 1,
    "insufficient_data_count": 0,
    "primary_ineligibility_reason": "HbA1c (8.2%) exceeds upper limit of 8.0%"
  },
  "screened_at": "2026-03-24T10:35:00Z",
  "screening_time_ms": 3100
}
```

---

## Data Validation Rules

### Criterion Validation

```python
def validate_criterion(criterion: dict) -> bool:
    """Validate a criterion object."""
    # criterion_id format
    if not re.match(r'^[IE]\d+$', criterion['criterion_id']):
        return False

    # type matches criterion_id prefix
    prefix = criterion['criterion_id'][0]
    expected_type = 'inclusion' if prefix == 'I' else 'exclusion'
    if criterion['type'] != expected_type:
        return False

    # description length
    if not (10 <= len(criterion['description']) <= 500):
        return False

    # category is valid
    valid_categories = {
        'demographics', 'diagnosis', 'lab_values', 'medications',
        'medical_history', 'procedures', 'functional_status', 'other'
    }
    if criterion['category'] not in valid_categories:
        return False

    # data_points_needed is array, not empty for evaluable criteria
    if not isinstance(criterion['data_points_needed'], list):
        return False
    if len(criterion['data_points_needed']) > 20:
        return False

    # logic is optional string
    if criterion.get('logic') is not None:
        if not isinstance(criterion['logic'], str) or len(criterion['logic']) > 500:
            return False

    return True
```

### Patient Summary Validation

```python
def validate_patient_summary(summary: dict) -> bool:
    """Validate patient summary."""
    # At least one summary type provided
    if not summary.get('free_text') and not summary.get('structured'):
        return False

    # If free_text, max 5000 chars
    if summary.get('free_text'):
        if len(summary['free_text']) > 5000:
            return False

    # If structured, validate fields
    if summary.get('structured'):
        struct = summary['structured']

        # Age validation
        if struct.get('age') is not None:
            if not (18 <= struct['age'] <= 120):
                return False

        # Sex validation
        if struct.get('sex') is not None:
            if struct['sex'] not in ['Male', 'Female', 'Other']:
                return False

        # Lab values validation
        if struct.get('lab_values'):
            if len(struct['lab_values']) > 50:
                return False
            for lab in struct['lab_values']:
                if not isinstance(lab['value'], (int, float)):
                    return False

    return True
```

---

## Session Data Lifecycle

### Data Persistence Timeline

```
T+0:  User uploads PDF
      → PDFParser extracts text, stores in S3
      → Backend stores S3 path in session memory
      → Session created with HTTP-only cookie

T+5-10 seconds: LLM extraction completes
      → Criteria stored in session memory
      → S3 file still accessible (will be deleted at T+24h)
      → Session data in-memory (not persistent)

T+10 minutes: User navigates to screening page
      → Criteria loaded from session memory
      → S3 PDF still accessible for preview

T+30 minutes (inactivity timeout): Session expires
      → Session memory cleared
      → S3 file still exists (24h lifecycle)
      → User redirected to home page

T+24 hours: S3 lifecycle policy
      → PDF auto-deleted from S3
      → No data remains

User closes browser before T+30 min: Session expires immediately on tab close
      → Session memory cleared (since it's in-memory only, not persistent)
      → S3 file still deleted at T+24h
```

### Data Clearance on Actions

```
Logout:
  → Clear session memory immediately
  → Clear HTTP-only cookie
  → S3 file deleted at T+24h

Session Timeout (T+30 min):
  → Clear session memory
  → Expire HTTP-only cookie
  → S3 file deleted at T+24h

Page Refresh (while session active):
  → Session memory persists
  → Data available to user (implicit re-load from session)

Browser Tab Close:
  → Session memory lost (no persistence)
  → HTTP-only cookie may persist (depends on browser)
  → S3 file deleted at T+24h

New Protocol Upload (same session):
  → Previous protocol data cleared
  → New protocol loaded
  → Previous S3 file still deleted at T+24h
```

---

## Sign-Off

| Role | Name | Date | Signature |
|------|------|------|-----------|
| Data Model Owner | [Name] | 2026-03-24 | — |
| Backend Lead | [Name] | 2026-03-24 | — |
| Frontend Lead | [Name] | 2026-03-24 | — |

---

**END OF DATA MODELS DOCUMENT**
