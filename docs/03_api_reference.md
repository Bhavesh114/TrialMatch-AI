# API Reference
## TrialMatch AI — Clinical Trial Eligibility Screener

**Document Version:** 1.0
**Last Updated:** 2026-03-24
**Status:** Final - MVP v1.0
**Audience:** Backend engineers, frontend engineers, API consumers

---

## Overview

TrialMatch API is a RESTful service for clinical trial eligibility screening. The API follows OpenAPI 3.0 specification and uses JSON for all request/response bodies.

**Base URL:**
- Development: `http://localhost:8000/api`
- Staging: `https://api-staging.trialmatch.app/api`
- Production: `https://api.trialmatch.app/api`

**Protocol:** HTTPS (TLS 1.2+) required for production

---

## Authentication and Session Management

### Session-Based (No API Keys in MVP)

The API uses HTTP-only session cookies for authentication. Each user session is identified by a unique session ID stored in a secure, HTTP-only cookie.

**Session Lifecycle:**

```
1. User accesses frontend → Browser receives Set-Cookie: session_id=...
2. Every API request → Browser automatically includes session cookie
3. Backend validates session cookie on each request
4. Session timeout: 30 minutes of inactivity
5. Logout → Backend clears session; browser cookie expires
```

**Header Requirements:**

No custom Authorization header required. Session ID is automatically managed by the browser via HTTP-only cookies.

```
GET /health
Host: api.trialmatch.app
Cookie: session_id=abc123def456...
```

**Example: Setting a Session (Backend Response)**

```http
HTTP/1.1 200 OK
Set-Cookie: session_id=abc123def456; HttpOnly; Secure; SameSite=Strict; Max-Age=1800
Content-Type: application/json

{
  "protocol": { ... }
}
```

### Session Validation Rules

- Session ID is 43 characters (base64-encoded 32 bytes)
- Invalid or expired session: Returns `401 Unauthorized`
- Session timeout warning sent to frontend at 25-minute mark (5 minutes before expiry)
- Logout endpoint: `POST /api/logout` clears session

---

## Rate Limiting

**Rate Limit Policy:**
- 100 requests per session per hour
- Applies to all endpoints except `/health`
- Limit counter resets hourly (sliding window)

**Rate Limit Headers:**

```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 87
X-RateLimit-Reset: 1711270800  (Unix timestamp)
```

**Exceeding Limit (429 Response):**

```http
HTTP/1.1 429 Too Many Requests
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1711270800
Content-Type: application/json

{
  "error": "Rate limit exceeded. Please try again later.",
  "retry_after_seconds": 3600
}
```

**Mitigation:**
- Multiple concurrent API calls count toward rate limit
- Each session has independent rate limit bucket
- New session (new browser tab) = new rate limit bucket

---

## Error Handling

### Error Response Format

All error responses follow this standard format:

```json
{
  "error": "Human-readable error message",
  "error_code": "SPECIFIC_ERROR_CODE",
  "request_id": "req-uuid-123",
  "timestamp": "2026-03-24T10:30:00Z"
}
```

**error_code meanings:**

| Code | HTTP Status | Meaning | Retry? |
|------|-------------|---------|--------|
| `INVALID_REQUEST` | 400 | Malformed request, missing required fields | No |
| `FILE_TOO_LARGE` | 413 | PDF exceeds 50 MB limit | No |
| `UNSUPPORTED_FILE_TYPE` | 415 | File is not a PDF | No |
| `MALWARE_DETECTED` | 400 | File failed security scan | No |
| `SESSION_EXPIRED` | 401 | Session timeout or invalid session ID | Yes (new session) |
| `EXTRACTION_FAILED` | 500 | PDF text extraction failed | Yes |
| `EXTRACTION_TIMEOUT` | 504 | Extraction took >120 seconds | Yes |
| `SCREENING_FAILED` | 500 | Screening evaluation failed | Yes |
| `SCREENING_TIMEOUT` | 504 | Screening took >90 seconds | Yes |
| `REPORT_GENERATION_FAILED` | 500 | PDF report generation failed | Yes |
| `RATE_LIMIT_EXCEEDED` | 429 | Rate limit hit | Yes (after wait) |
| `INSUFFICIENT_DATA_PROVIDED` | 400 | Required fields missing (no patient data or criteria) | No |

### HTTP Status Code Summary

| Status | Meaning |
|--------|---------|
| 200 | Success (all operations completed) |
| 201 | Created (resource created successfully) |
| 400 | Bad Request (invalid input, validation failure) |
| 401 | Unauthorized (session invalid or expired) |
| 413 | Payload Too Large (file or request body exceeds limit) |
| 415 | Unsupported Media Type (wrong file type) |
| 429 | Too Many Requests (rate limit exceeded) |
| 500 | Internal Server Error (unhandled exception, LLM API failure) |
| 504 | Gateway Timeout (operation timed out) |

---

## Endpoints

### 1. POST /api/extract-criteria

**Purpose:** Upload a clinical trial protocol PDF and extract eligibility criteria using LLM analysis.

**Request:**

```http
POST /api/extract-criteria HTTP/1.1
Host: api.trialmatch.app
Content-Type: multipart/form-data
Cookie: session_id=...

Content:
  file: <binary PDF content>
```

**cURL Example:**

```bash
curl -X POST https://api.trialmatch.app/api/extract-criteria \
  -H "Cookie: session_id=abc123..." \
  -F "file=@protocol.pdf"
```

**JavaScript (Fetch) Example:**

```javascript
const formData = new FormData();
formData.append('file', pdfFile);  // HTMLInputElement

const response = await fetch('/api/extract-criteria', {
  method: 'POST',
  credentials: 'include',  // Auto-include session cookie
  body: formData
});

const result = await response.json();
```

**Request Constraints:**

| Constraint | Value | Description |
|---|---|---|
| File format | PDF only | .pdf extension, application/pdf MIME type |
| Max file size | 50 MB | Larger files rejected with 413 Payload Too Large |
| Timeout | 120 seconds | Extraction must complete within 120 sec; returns 504 if exceeded |
| Content-Type | multipart/form-data | Required for file upload |

**Response (200 OK):**

```json
{
  "protocol": {
    "id": "proto-550e8400-e29b-41d4-a716-446655440000",
    "title": "A Phase II Randomized, Double-Blind, Placebo-Controlled Study of Drug X in Type 2 Diabetes Mellitus",
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
      "description": "Patients aged 18 to 75 years (inclusive) at the time of enrollment",
      "category": "demographics",
      "data_points_needed": [
        "age",
        "date_of_birth"
      ],
      "logic": "18 ≤ age ≤ 75"
    },
    {
      "criterion_id": "I2",
      "type": "inclusion",
      "description": "Diagnosis of Type 2 Diabetes Mellitus confirmed by medical history at least 12 weeks prior to enrollment",
      "category": "diagnosis",
      "data_points_needed": [
        "diabetes_type",
        "diagnosis_date"
      ],
      "logic": "Type 2 DM diagnosed >12 weeks ago"
    },
    {
      "criterion_id": "I3",
      "type": "inclusion",
      "description": "HbA1c between 7.0% and 10.5% at screening visit",
      "category": "lab_values",
      "data_points_needed": [
        "HbA1c_value",
        "HbA1c_date"
      ],
      "logic": "7.0 ≤ HbA1c ≤ 10.5"
    },
    {
      "criterion_id": "E1",
      "type": "exclusion",
      "description": "Type 1 Diabetes Mellitus or secondary diabetes (e.g., due to pancreatitis, cystic fibrosis)",
      "category": "diagnosis",
      "data_points_needed": [
        "diabetes_type"
      ],
      "logic": null
    },
    {
      "criterion_id": "E2",
      "type": "exclusion",
      "description": "Acute coronary syndrome, myocardial infarction, or stroke within 6 months prior to screening",
      "category": "medical_history",
      "data_points_needed": [
        "cardiovascular_events",
        "event_dates"
      ],
      "logic": "No CVD events within 6 months"
    }
  ],
  "text_confidence": 0.98,
  "extraction_time_ms": 5200
}
```

**Response Field Descriptions:**

```typescript
protocol: {
  id: string                    // UUID for this protocol in session
  title: string                 // Trial title extracted from protocol
  version: string | null        // Protocol version if found
  nct_number: string | null     // NCT number if found (e.g., NCT05123456)
  sponsor: string | null        // Trial sponsor name if found
  estimated_enrollment: number | null  // Expected enrollment size
  s3_path: string              // S3 URI (temporary storage)
  text_confidence: number       // 0.0-1.0; 0.98 = searchable PDF, 0.65 = scanned/low-quality
  extracted_at: string         // ISO8601 timestamp
}

criteria: array[
  {
    criterion_id: string        // I1, I2, I3... or E1, E2, E3...
    type: string               // "inclusion" or "exclusion"
    description: string        // Plain language, 1-2 sentences
    category: string           // demographics, diagnosis, lab_values, medications, medical_history, procedures, functional_status, other
    data_points_needed: string[] // Specific data needed to evaluate criterion
    logic: string | null       // AND/OR/temporal logic if applicable
  }
]

text_confidence: number         // Overall text extraction confidence (same as protocol.text_confidence)
extraction_time_ms: number      // Time to extract criteria in milliseconds
```

**Response (400 Bad Request - Invalid File Type):**

```json
{
  "error": "File must be a PDF. You uploaded: image/jpeg",
  "error_code": "UNSUPPORTED_FILE_TYPE",
  "request_id": "req-123abc",
  "timestamp": "2026-03-24T10:30:00Z"
}
```

**Response (413 Payload Too Large):**

```json
{
  "error": "File size exceeds 50 MB limit. Your file: 62 MB",
  "error_code": "FILE_TOO_LARGE",
  "request_id": "req-123abc",
  "timestamp": "2026-03-24T10:30:00Z"
}
```

**Response (500 Internal Server Error - Malware):**

```json
{
  "error": "PDF failed security scan. Please verify file source and try again.",
  "error_code": "MALWARE_DETECTED",
  "request_id": "req-123abc",
  "timestamp": "2026-03-24T10:30:00Z"
}
```

**Response (500 Internal Server Error - Extraction Failed):**

```json
{
  "error": "Criteria extraction failed. Please try again or contact support.",
  "error_code": "EXTRACTION_FAILED",
  "request_id": "req-123abc",
  "timestamp": "2026-03-24T10:30:00Z"
}
```

**Response (504 Gateway Timeout):**

```json
{
  "error": "Extraction took too long (>120 seconds). Try a shorter protocol or contact support.",
  "error_code": "EXTRACTION_TIMEOUT",
  "request_id": "req-123abc",
  "timestamp": "2026-03-24T10:30:00Z"
}
```

**Notes:**
- Text extraction confidence <0.80 (scanned PDFs) shown to user with warning
- Temporary S3 files auto-deleted after 24 hours
- Protocol metadata (title, NCT number) optional; extracted if available in protocol text

---

### 2. POST /api/screen-patient

**Purpose:** Evaluate a patient against extracted criteria to determine eligibility.

**Request:**

```http
POST /api/screen-patient HTTP/1.1
Host: api.trialmatch.app
Content-Type: application/json
Cookie: session_id=...

{
  "criteria": [ ... ],          // Array of CriterionModel (from extraction)
  "patient_summary": { ... }    // PatientSummary (free_text OR structured)
}
```

**Request Schema:**

```json
{
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
  "patient_summary": {
    "free_text": "55-year-old female with Type 2 Diabetes diagnosed 2019. HbA1c 8.2% (as of March 2024), BMI 31.4. Current medications: Metformin 1000mg twice daily, Lisinopril 10mg once daily. Comorbidities: hypertension (well-controlled), mild osteoarthritis. No prior cardiovascular events. No history of cancer or organ transplant. Currently not pregnant. Allergic to penicillin."
  }
  // OR:
  "patient_summary": {
    "structured": {
      "age": 55,
      "sex": "Female",
      "primary_diagnosis": "Type 2 Diabetes Mellitus",
      "secondary_diagnoses": ["Hypertension"],
      "current_medications": ["Metformin 1000mg BID", "Lisinopril 10mg daily"],
      "lab_values": [
        {
          "name": "HbA1c",
          "value": 8.2,
          "unit": "%",
          "date": "2024-03-10"
        },
        {
          "name": "eGFR",
          "value": 78,
          "unit": "mL/min",
          "date": "2024-03-10"
        }
      ],
      "comorbidities": ["Hypertension", "Osteoarthritis"],
      "functional_status": "Independent",
      "procedures": [],
      "allergies": ["Penicillin"],
      "pregnancy_status": "Not pregnant",
      "additional_notes": "Well-controlled hypertension on current regimen"
    }
  }
}
```

**Request Field Definitions:**

```typescript
criteria: CriterionModel[]     // Required; min 1, max 80 criteria
patient_summary: {
  free_text?: string           // Option 1: Unstructured clinical notes (max 5000 chars)
  structured?: {               // Option 2: Structured form fields
    age?: number               // 18-120
    sex?: string               // Male, Female, Other
    primary_diagnosis?: string
    secondary_diagnoses?: string[]
    current_medications?: string[]  // "Name dose frequency" format
    lab_values?: LabValue[]
    comorbidities?: string[]
    functional_status?: string  // Independent, Assisted, Dependent
    procedures?: string[]
    allergies?: string[]
    pregnancy_status?: string   // Not pregnant, Pregnant, Unknown
    additional_notes?: string   // Any other info (max 500 chars)
  }
}

// LabValue structure:
type LabValue = {
  name: string                 // Test name (HbA1c, eGFR, etc.)
  value: number                // Numeric result
  unit: string                 // Unit (%, mL/min, etc.)
  date?: string                // ISO8601 date (optional; if missing, assumes recent)
}
```

**cURL Example (Free-Text):**

```bash
curl -X POST https://api.trialmatch.app/api/screen-patient \
  -H "Content-Type: application/json" \
  -H "Cookie: session_id=abc123..." \
  -d '{
    "criteria": [ ... ],
    "patient_summary": {
      "free_text": "55-year-old female with Type 2 Diabetes..."
    }
  }'
```

**JavaScript (Fetch) Example (Structured):**

```javascript
const patientData = {
  criteria: extractedCriteria,  // From previous extraction call
  patient_summary: {
    structured: {
      age: 55,
      sex: "Female",
      primary_diagnosis: "Type 2 Diabetes Mellitus",
      lab_values: [
        { name: "HbA1c", value: 8.2, unit: "%", date: "2024-03-10" }
      ]
    }
  }
};

const response = await fetch('/api/screen-patient', {
  method: 'POST',
  credentials: 'include',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(patientData)
});

const result = await response.json();
```

**Response (200 OK):**

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
    }
  ],
  "missing_data_aggregated": [],
  "overall_summary": {
    "eligible_count": 4,
    "ineligible_count": 1,
    "insufficient_data_count": 0,
    "primary_ineligibility_reason": "HbA1c (8.2%) exceeds upper limit of 8.0%"
  },
  "screened_at": "2026-03-24T10:35:00Z",
  "screening_time_ms": 3100
}
```

**Response Field Descriptions:**

```typescript
overall_status: "ELIGIBLE" | "NOT_ELIGIBLE" | "REQUIRES_REVIEW"
  // ELIGIBLE: All inclusion criteria MEETS, no exclusion DOES_NOT_MEET, no INSUFFICIENT_DATA
  // NOT_ELIGIBLE: >=1 inclusion DOES_NOT_MEET OR >=1 exclusion DOES_NOT_MEET
  // REQUIRES_REVIEW: >=1 INSUFFICIENT_DATA (need coordinator investigation)

criteria_assessments: {
  criterion_id: string           // I1, I2, E1, etc.
  status: "MEETS" | "DOES_NOT_MEET" | "INSUFFICIENT_DATA"
  confidence: "high" | "medium" | "low"
  reasoning: string              // 2-3 sentences with specific evidence
  missing_data: string[] | null  // If status = INSUFFICIENT_DATA, list specific needed data
}[]

missing_data_aggregated: {
  name: string                   // Specific data needed (e.g., "HbA1c value from last 3 months")
  count: number                  // Number of criteria requiring this data
  criterion_ids: string[]        // Which criteria need this data (e.g., ["I3", "E2"])
}[]

overall_summary: {
  eligible_count: number         // Number of criteria with MEETS
  ineligible_count: number       // Number with DOES_NOT_MEET
  insufficient_data_count: number // Number with INSUFFICIENT_DATA
  primary_ineligibility_reason: string | null  // Top reason for NOT_ELIGIBLE (if applicable)
}

screened_at: string              // ISO8601 timestamp
screening_time_ms: number        // Time to run screening in milliseconds
```

**Response (400 Bad Request - Missing Patient Data):**

```json
{
  "error": "No patient summary provided. Include either free_text or structured patient data.",
  "error_code": "INSUFFICIENT_DATA_PROVIDED",
  "request_id": "req-123abc",
  "timestamp": "2026-03-24T10:30:00Z"
}
```

**Response (400 Bad Request - No Criteria):**

```json
{
  "error": "No criteria provided. Run extraction first and provide criteria array.",
  "error_code": "INSUFFICIENT_DATA_PROVIDED",
  "request_id": "req-123abc",
  "timestamp": "2026-03-24T10:30:00Z"
}
```

**Response (500 Internal Server Error):**

```json
{
  "error": "Screening evaluation failed. Please try again in a few moments.",
  "error_code": "SCREENING_FAILED",
  "request_id": "req-123abc",
  "timestamp": "2026-03-24T10:30:00Z"
}
```

**Response (504 Gateway Timeout):**

```json
{
  "error": "Screening took too long (>90 seconds). Please try again.",
  "error_code": "SCREENING_TIMEOUT",
  "request_id": "req-123abc",
  "timestamp": "2026-03-24T10:30:00Z"
}
```

**Notes:**
- Confidence calibration: HIGH (clear criterion + complete data), MEDIUM (ambiguous criterion OR incomplete data), LOW (both ambiguous)
- If in doubt about criterion, LLM returns INSUFFICIENT_DATA (safe approach)
- Patient data is sanitized for PII before being sent to LLM

---

### 3. POST /api/export-report

**Purpose:** Generate a PDF report of screening results for download.

**Request:**

```http
POST /api/export-report HTTP/1.1
Host: api.trialmatch.app
Content-Type: application/json
Cookie: session_id=...

{}  // Empty body; uses session data
```

**JavaScript (Fetch) Example:**

```javascript
const response = await fetch('/api/export-report', {
  method: 'POST',
  credentials: 'include',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({})
});

// Trigger download
const blob = await response.blob();
const url = window.URL.createObjectURL(blob);
const a = document.createElement('a');
a.href = url;
a.download = `TrialMatch_Screening_${trialID}_${date}.pdf`;
a.click();
window.URL.revokeObjectURL(url);
```

**Response (200 OK):**

```http
HTTP/1.1 200 OK
Content-Type: application/pdf
Content-Disposition: attachment; filename="TrialMatch_Screening_NCT05123456_2026-03-24_103500.pdf"
Content-Length: 45678

[Binary PDF content]
```

**Response Headers:**

```
Content-Type: application/pdf
Content-Disposition: attachment; filename="TrialMatch_Screening_[TRIALID]_[DATE]_[TIMESTAMP].pdf"
Content-Length: [size in bytes]
Cache-Control: no-cache, no-store, must-revalidate
```

**Filename Format:**
- `TrialMatch_Screening_[TRIAL_ID]_[DATE]_[TIMESTAMP].pdf`
- Example: `TrialMatch_Screening_NCT05123456_2026-03-24_103500.pdf`
- TRIAL_ID: NCT number if available, else "UNKNOWN"
- DATE: YYYY-MM-DD
- TIMESTAMP: HHMMSS (24-hour)

**PDF Content:**

The generated PDF includes:

```
┌─────────────────────────────────────────────────────────┐
│  TrialMatch AI - Clinical Trial Eligibility Screening   │
│                    Report                               │
└─────────────────────────────────────────────────────────┘

Protocol Information:
  Title: [Protocol title from extraction]
  Version: [Version number]
  NCT Number: [NCT number if available]
  Sponsor: [Sponsor name if available]

Screening Summary:
  Overall Status: [ELIGIBLE / NOT_ELIGIBLE / REQUIRES_REVIEW]
  Screening Date: [ISO8601 timestamp]

Patient Summary:
  [De-identified patient summary as entered by coordinator]

Results by Criterion:
  ┌────────────┬─────────────┬──────────┬───────────────┐
  │ Criterion  │ Status      │ Confidence │ Reasoning   │
  ├────────────┼─────────────┼──────────┼───────────────┤
  │ I1: Age    │ MEETS       │ High     │ Age 55 within │
  │ 18-75      │             │          │ range 18-75   │
  │            │             │          │               │
  │ I2: T2DM   │ MEETS       │ High     │ Diagnosed     │
  │ diagnosis  │             │          │ 2019 (>12wks) │
  │            │             │          │               │
  │ I3: HbA1c  │ DOES NOT    │ High     │ HbA1c 8.2%   │
  │ 7-8%       │ MEET        │          │ exceeds 8.0%  │
  │            │             │          │               │
  │ E1: Not    │ MEETS       │ High     │ Type 2 DM,    │
  │ Type 1 DM  │             │          │ not Type 1    │
  └────────────┴─────────────┴──────────┴───────────────┘

Missing Data (If Any):
  [List of data needed for INSUFFICIENT_DATA criteria]

Disclaimer:
  ⚠️  This screening is for efficiency support only and does NOT
  replace clinical judgment by the Study Coordinator and Principal
  Investigator. All eligibility determinations must be verified and
  approved by authorized study personnel before patient enrollment.

  This report is NOT a clinical decision and must NOT be used as the
  sole basis for enrollment decisions.

  Generated by TrialMatch AI on [DATE]
  This is a decision support tool, not a clinical decision.

[Footer with generation timestamp, no PHI]
```

**Response (400 Bad Request - No Results):**

```json
{
  "error": "No screening results found in session. Please complete screening first.",
  "error_code": "INSUFFICIENT_DATA_PROVIDED",
  "request_id": "req-123abc",
  "timestamp": "2026-03-24T10:30:00Z"
}
```

**Response (500 Internal Server Error):**

```json
{
  "error": "Report generation failed. Please try again.",
  "error_code": "REPORT_GENERATION_FAILED",
  "request_id": "req-123abc",
  "timestamp": "2026-03-24T10:30:00Z"
}
```

**Notes:**
- PDF contains no PHI (patient data sanitized)
- Filename includes trial ID for easy file organization
- Report is time-stamped for audit purposes
- Disclaimer always present (not waivable)
- Max PDF size: 5 MB

---

### 4. GET /health

**Purpose:** Health check endpoint for monitoring service availability.

**Request:**

```http
GET /health HTTP/1.1
Host: api.trialmatch.app
```

**Response (200 OK):**

```json
{
  "status": "ok",
  "version": "1.0.0",
  "timestamp": "2026-03-24T10:30:00Z",
  "checks": {
    "database": "ok",          // Not applicable (no DB in MVP)
    "anthropic_api": "ok",     // Claude API accessible
    "s3": "ok",                // AWS S3 accessible
    "memory": "ok"             // Backend memory usage normal
  }
}
```

**Response (503 Service Unavailable - Degraded):**

```json
{
  "status": "degraded",
  "version": "1.0.0",
  "timestamp": "2026-03-24T10:30:00Z",
  "checks": {
    "anthropic_api": "error",  // Claude API down
    "s3": "ok"
  }
}
```

**Response (500 Internal Server Error - Critical):**

```json
{
  "error": "Service unhealthy",
  "status": "critical",
  "timestamp": "2026-03-24T10:30:00Z"
}
```

**Notes:**
- Does not require session cookie (no authentication)
- Used by load balancers and monitoring systems
- Response time: <100ms (no external API calls)

---

## File Size and Format Constraints

### PDF Uploads

| Constraint | Limit | Enforcement |
|---|---|---|
| Maximum file size | 50 MB | Hard limit; returns 413 if exceeded |
| Minimum file size | 1 KB | Soft limit; warns if suspiciously small |
| File format | PDF (.pdf) | Verified by MIME type and magic bytes |
| Encryption | Not allowed | Encrypted PDFs rejected with error |
| Corrupted files | Auto-detected | ClamAV/Macie scans; malware rejected |

### Patient Data

| Constraint | Limit | Enforcement |
|---|---|---|
| Free-text summary | 5,000 characters | Hard limit; returns 400 if exceeded |
| Structured form notes | 500 characters | Hard limit; front-end validation |
| Lab values per patient | 100 entries | Soft limit; no hard enforcement |
| Medications list | 50 entries | Soft limit; no hard enforcement |
| Comorbidities | 50 entries | Soft limit; no hard enforcement |

### Request and Response

| Constraint | Limit |
|---|---|
| Request body size | 10 MB |
| Response body size | Unlimited (files can be large) |
| Request timeout | 120 seconds |
| Response timeout | 120 seconds |

---

## Versioning and Backwards Compatibility

### API Versioning Strategy

**Current Version:** v1 (implicit; no version prefix in URL for MVP)

**Future Versioning (Phase 2+):**
- New major features → new API version
- Backwards compatibility maintained for 2 versions
- Example: `/api/v2/screen-patient` alongside `/api/v1/screen-patient`

**Breaking Changes (Phase 2+):**
- Removal of fields: Requires new API version
- Addition of required fields: Backwards compatible (no version bump)
- Response structure changes: New API version
- Deprecated endpoints: 6-month sunset period

### URL Structure

```
/api/extract-criteria   (v1, no version prefix)
/api/screen-patient     (v1, no version prefix)
/api/export-report      (v1, no version prefix)
```

---

## Caching Strategy

### Backend Caching

**Extraction Results:**
- Criteria for same protocol PDF cached in session for 30 minutes
- Cache key: Protocol ID (UUID)
- Size: ~10 KB per cached extraction
- Invalidation: Session timeout or explicit logout

**Screening Results:**
- Patient screening results cached in session for 30 minutes
- Cache key: Patient summary hash
- Allows re-export without re-running LLM
- Invalidation: Session timeout or explicit logout

### Frontend Caching

**Static Assets (JS, CSS):**
- Cache-Control: max-age=31536000 (1 year for versioned files)
- Content hashing: CSS and JS filenames include content hash
- Cache busting: New deployment → new hash → browser re-fetches

**HTML:**
- Cache-Control: no-cache, must-revalidate
- Always fetches from server; uses ETags for validation

**API Responses:**
- No caching (all responses dynamic based on user input)
- Cache-Control: no-store, must-revalidate

---

## Examples

### Complete Workflow Example

**Step 1: Upload Protocol**

```bash
# Upload protocol PDF
curl -X POST https://api.trialmatch.app/api/extract-criteria \
  -F "file=@protocol.pdf" \
  -b "session_id=xyz..." \
  -o extract_response.json

# Response contains criteria array
```

**Step 2: Screen Patient (Free-Text)**

```bash
# Screen patient with free-text summary
curl -X POST https://api.trialmatch.app/api/screen-patient \
  -H "Content-Type: application/json" \
  -d '{
    "criteria": [ <extracted criteria from step 1> ],
    "patient_summary": {
      "free_text": "55-year-old female, Type 2 Diabetes, HbA1c 8.2%..."
    }
  }' \
  -b "session_id=xyz..." \
  -o screening_response.json

# Response contains overall_status and criteria_assessments
```

**Step 3: Export Report**

```bash
# Generate and download PDF report
curl -X POST https://api.trialmatch.app/api/export-report \
  -H "Content-Type: application/json" \
  -d '{}' \
  -b "session_id=xyz..." \
  --output "TrialMatch_Screening_$(date +%Y-%m-%d).pdf"

# File downloaded to local disk
```

---

## API Specification (OpenAPI 3.0 YAML)

```yaml
openapi: 3.0.0
info:
  title: TrialMatch AI API
  version: 1.0.0
  description: Clinical Trial Eligibility Screening API

servers:
  - url: https://api.trialmatch.app
    description: Production
  - url: https://api-staging.trialmatch.app
    description: Staging
  - url: http://localhost:8000
    description: Development

paths:
  /api/extract-criteria:
    post:
      summary: Extract eligibility criteria from protocol PDF
      operationId: extractCriteria
      requestBody:
        required: true
        content:
          multipart/form-data:
            schema:
              type: object
              properties:
                file:
                  type: string
                  format: binary
                  description: PDF protocol file
      responses:
        '200':
          description: Criteria extraction successful
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ExtractionResponse'
        '400':
          description: Bad request
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'
        '413':
          description: File too large
        '500':
          description: Extraction failed
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'

  /api/screen-patient:
    post:
      summary: Screen patient against criteria
      operationId: screenPatient
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/ScreeningRequest'
      responses:
        '200':
          description: Screening successful
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ScreeningResponse'
        '400':
          description: Invalid request
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'
        '500':
          description: Screening failed
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'

  /api/export-report:
    post:
      summary: Generate PDF screening report
      operationId: exportReport
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
      responses:
        '200':
          description: PDF report generated
          content:
            application/pdf:
              schema:
                type: string
                format: binary
        '400':
          description: No results to export
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'
        '500':
          description: Report generation failed
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'

  /health:
    get:
      summary: Health check
      operationId: healthCheck
      responses:
        '200':
          description: Service healthy
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/HealthResponse'
        '503':
          description: Service degraded
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/HealthResponse'

components:
  schemas:
    Criterion:
      type: object
      required:
        - criterion_id
        - type
        - description
        - category
        - data_points_needed
      properties:
        criterion_id:
          type: string
          example: I1
        type:
          type: string
          enum: [inclusion, exclusion]
        description:
          type: string
        category:
          type: string
          enum: [demographics, diagnosis, lab_values, medications, medical_history, procedures, functional_status, other]
        data_points_needed:
          type: array
          items:
            type: string
        logic:
          type: string
          nullable: true

    ExtractionResponse:
      type: object
      required:
        - protocol
        - criteria
        - text_confidence
      properties:
        protocol:
          type: object
          properties:
            id:
              type: string
            title:
              type: string
            version:
              type: string
              nullable: true
            nct_number:
              type: string
              nullable: true
            sponsor:
              type: string
              nullable: true
            s3_path:
              type: string
            text_confidence:
              type: number
              format: float
            extracted_at:
              type: string
              format: date-time
        criteria:
          type: array
          items:
            $ref: '#/components/schemas/Criterion'
        extraction_time_ms:
          type: integer

    ScreeningRequest:
      type: object
      required:
        - criteria
        - patient_summary
      properties:
        criteria:
          type: array
          items:
            $ref: '#/components/schemas/Criterion'
        patient_summary:
          type: object
          properties:
            free_text:
              type: string
              nullable: true
            structured:
              type: object
              nullable: true

    CriterionAssessment:
      type: object
      required:
        - criterion_id
        - status
        - confidence
        - reasoning
      properties:
        criterion_id:
          type: string
        status:
          type: string
          enum: [MEETS, DOES_NOT_MEET, INSUFFICIENT_DATA]
        confidence:
          type: string
          enum: [high, medium, low]
        reasoning:
          type: string
        missing_data:
          type: array
          items:
            type: string
          nullable: true

    ScreeningResponse:
      type: object
      required:
        - overall_status
        - criteria_assessments
        - screened_at
      properties:
        overall_status:
          type: string
          enum: [ELIGIBLE, NOT_ELIGIBLE, REQUIRES_REVIEW]
        criteria_assessments:
          type: array
          items:
            $ref: '#/components/schemas/CriterionAssessment'
        missing_data_aggregated:
          type: array
          items:
            type: object
        screening_time_ms:
          type: integer
        screened_at:
          type: string
          format: date-time

    ErrorResponse:
      type: object
      required:
        - error
        - error_code
        - timestamp
      properties:
        error:
          type: string
        error_code:
          type: string
        request_id:
          type: string
        timestamp:
          type: string
          format: date-time

    HealthResponse:
      type: object
      required:
        - status
      properties:
        status:
          type: string
          enum: [ok, degraded, critical]
        version:
          type: string
        checks:
          type: object
        timestamp:
          type: string
          format: date-time
```

---

## Sign-Off

| Role | Name | Date | Signature |
|------|------|------|-----------|
| API Owner | [Name] | 2026-03-24 | — |
| Backend Lead | [Name] | 2026-03-24 | — |
| Frontend Lead | [Name] | 2026-03-24 | — |

---

**END OF API REFERENCE DOCUMENT**
