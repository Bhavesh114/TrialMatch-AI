# Technical Architecture Document
## TrialMatch AI — Clinical Trial Eligibility Screener

**Document Version:** 1.0
**Last Updated:** 2026-03-24
**Status:** Final - MVP v1.0
**Audience:** Engineering, DevOps, Tech Leads

---

## System Overview

### Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            USER (Web Browser)                               │
│                                                                              │
│  Chrome/Firefox/Safari (Modern ES2020+)                                     │
│  HTTP-Only Session Cookie (HTTPS only)                                      │
└────────────┬───────────────────────────────────────────────────────────────┘
             │ HTTPS (TLS 1.2+)
             │ CORS enabled for frontend domain
             ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        FRONTEND TIER (React + Vite)                         │
│                      Deployed on Vercel CDN (CloudFront)                    │
│                                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │
│  │  Home Page   │  │ Extract Page │  │ Screen Page  │  │ Report Page  │   │
│  │ (Upload PDF) │  │ (Criteria    │  │ (Patient In) │  │ (Results +   │   │
│  │              │  │  Review)     │  │              │  │  Export PDF) │   │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘   │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                      React Context (State)                          │   │
│  │  - Protocol metadata + PDF path                                     │   │
│  │  - Extracted criteria (editable)                                    │   │
│  │  - Patient summary                                                  │   │
│  │  - Screening results (cacheable)                                    │   │
│  │  - UI state (current page, loading, errors)                         │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                     API Client (Fetch/Axios)                        │   │
│  │  - Session ID management (from HTTP-only cookie)                    │   │
│  │  - Error handling + user-friendly messages                          │   │
│  │  - Request/response transformation                                  │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└────────────┬───────────────────────────────────────────────────────────────┘
             │ HTTPS
             │ /api/* endpoints
             ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│           BACKEND TIER (FastAPI + Python / AWS Lambda / Railway)            │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    FastAPI Application                              │   │
│  │                                                                      │   │
│  │  ┌──────────────────────────────────────────────────────────────┐  │   │
│  │  │                     Router Layer                             │  │   │
│  │  │                                                              │  │   │
│  │  │  POST /api/extract-criteria  ─→ extract_router.py           │  │   │
│  │  │  POST /api/screen-patient    ─→ screen_router.py            │  │   │
│  │  │  POST /api/export-report     ─→ report_router.py            │  │   │
│  │  │  GET  /health                ─→ health check                 │  │   │
│  │  │                                                              │  │   │
│  │  └──────────────────────────────────────────────────────────────┘  │   │
│  │                           ▼ ▼ ▼                                     │   │
│  │  ┌──────────────────────────────────────────────────────────────┐  │   │
│  │  │                   Service Layer                              │  │   │
│  │  │                                                              │  │   │
│  │  │  ┌─────────────────┐  ┌─────────────────┐                  │  │   │
│  │  │  │ pdf_parser.py   │  │ criteria_       │                  │  │   │
│  │  │  │                 │  │ extractor.py    │                  │  │   │
│  │  │  │ - PyMuPDF       │  │                 │                  │  │   │
│  │  │  │ - Tesseract OCR │  │ - LLM prompt    │                  │  │   │
│  │  │  │ - S3 fetch      │  │ - JSON parsing  │                  │  │   │
│  │  │  └─────────────────┘  └─────────────────┘                  │  │   │
│  │  │                                                              │  │   │
│  │  │  ┌─────────────────┐  ┌─────────────────┐                  │  │   │
│  │  │  │ patient_        │  │ report_         │                  │  │   │
│  │  │  │ screener.py     │  │ generator.py    │                  │  │   │
│  │  │  │                 │  │                 │                  │  │   │
│  │  │  │ - LLM prompt    │  │ - ReportLab PDF │                  │  │   │
│  │  │  │ - Confidence    │  │ - Table layout  │                  │  │   │
│  │  │  │ - Missing data  │  │ - Sanitization  │                  │  │   │
│  │  │  └─────────────────┘  └─────────────────┘                  │  │   │
│  │  │                                                              │  │   │
│  │  └──────────────────────────────────────────────────────────────┘  │   │
│  │                           ▼                                        │   │
│  │  ┌──────────────────────────────────────────────────────────────┐  │   │
│  │  │                  Dependency Layer                            │  │   │
│  │  │                                                              │  │   │
│  │  │  - Session manager (in-memory)                              │  │   │
│  │  │  - Config loader                                            │  │   │
│  │  │  - AWS client (S3, Secrets Manager)                         │  │   │
│  │  │  - Anthropic client (Claude API)                            │  │   │
│  │  │  - Logging                                                  │  │   │
│  │  │  - Error handlers                                           │  │   │
│  │  │                                                              │  │   │
│  │  └──────────────────────────────────────────────────────────────┘  │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                   Middleware Stack                                  │   │
│  │                                                                      │   │
│  │  - Session middleware (validate HTTP-only cookie)                   │   │
│  │  - CORS middleware (strict domain whitelist)                        │   │
│  │  - Request size limiter (max 10 MB payload)                         │   │
│  │  - Error handler (sanitize 5xx responses)                           │   │
│  │  - Logging middleware (audit trail, no patient data)                │   │
│  │                                                                      │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└────────────┬───────────────────────────────────────────────────────────────┘
             │
             ├─────────────────────────────────────────┬─────────────────┐
             ▼                                         ▼                 ▼
┌──────────────────────┐  ┌──────────────────┐  ┌──────────────────┐
│  AWS Secrets Manager │  │   Anthropic      │  │   AWS S3         │
│                      │  │   Claude API     │  │                  │
│ - API Keys           │  │   (External)     │  │ - Temp PDFs      │
│ - Stored encrypted   │  │   - Extraction   │  │ - Auto-delete    │
│ - Rotated annually   │  │   - Screening    │  │   24h            │
│                      │  │   - Rate limits  │  │ - Encrypted      │
│                      │  │   - Token mgmt   │  │ - Access logs    │
└──────────────────────┘  └──────────────────┘  └──────────────────┘
```

---

## Component-Level Architecture

### Frontend Architecture

**Framework Stack:**
- Framework: React 18+ (Vite build tool)
- Styling: Tailwind CSS + CSS Modules for component-scoped styles
- State management: React Context API (no Redux for MVP simplicity)
- PDF preview: react-pdf with fallback to iframe
- Form handling: Native HTML forms + controlled components
- HTTP client: Fetch API with custom wrapper for error handling

**Component Tree:**

```
<App>
├─ <ScreeningContext.Provider>
│
├─ <Routes>
│  ├─ "/"
│  │  └─ <Home>
│  │     └─ <ProtocolUpload>
│  │
│  ├─ "/extract"
│  │  └─ <Extract>
│  │     ├─ <ProtocolPreview>
│  │     └─ <CriteriaReview>
│  │        ├─ <CriteriaList>
│  │        │  └─ <CriterionItem> (editable, deletable)
│  │        └─ <CriteriaActions>
│  │           └─ (Add new, revert, next)
│  │
│  ├─ "/screen"
│  │  └─ <Screen>
│  │     ├─ <PatientInput>
│  │     │  ├─ <FreeTextInput>
│  │     │  └─ <StructuredForm>
│  │     │     ├─ Age input
│  │     │     ├─ Sex dropdown
│  │     │     ├─ Diagnosis input
│  │     │     ├─ Lab values table
│  │     │     ├─ Medications
│  │     │     ├─ Comorbidities checkboxes
│  │     │     └─ (other fields...)
│  │     │
│  │     └─ <ScreeningResults>
│  │        ├─ <OverallEligibility>
│  │        ├─ <CriteriaBreakdown>
│  │        │  └─ <CriteriaAssessmentCard> (multiple)
│  │        │     ├─ Criterion description
│  │        │     ├─ Status badge
│  │        │     ├─ Confidence meter
│  │        │     ├─ Reasoning text
│  │        │     └─ Missing data (if applicable)
│  │        └─ <MissingDataSummary>
│  │
│  └─ "/report"
│     └─ <Report>
│        ├─ <ReportPreview>
│        │  (formatted table view)
│        └─ <ExportButton>
│           └─ (PDF download)
│
└─ <ErrorBoundary>
   └─ (catches React errors)
```

**State Management (React Context):**

```typescript
ScreeningContext = {
  protocol: {
    id: string (UUID)
    title: string
    version: string
    nctNumber?: string
    sponsor?: string
    extractedAt: ISO8601 timestamp
    textConfidence: number (0-100)
    s3Path: string (temporary)
  },

  criteria: [
    {
      id: string (I1, I2, E1...)
      type: "inclusion" | "exclusion"
      description: string
      category: string
      dataPointsNeeded: string[]
      logic: string
      edited: boolean (true if user modified)
    }
  ],

  patientSummary: {
    freeText: string | null
    structured: {
      age?: number
      sex?: string
      primaryDiagnosis?: string
      secondaryDiagnoses?: string[]
      currentMeds?: string[]
      comorbidities?: string[]
      labValues?: [{name, value, unit, date}]
      functionalStatus?: string
      procedures?: string[]
      allergies?: string[]
      pregnancyStatus?: string
      additionalNotes?: string
    } | null
    piiWarning?: boolean
  },

  screeningResults?: {
    overallStatus: "ELIGIBLE" | "NOT_ELIGIBLE" | "REQUIRES_REVIEW"
    criteriaAssessments: [
      {
        criterionId: string
        status: "MEETS" | "DOES_NOT_MEET" | "INSUFFICIENT_DATA"
        confidence: "high" | "medium" | "low"
        reasoning: string
        missingData?: string[]
        overridden?: boolean (if coordinator changed it)
      }
    ]
    missingDataAggregated: {name, count, criterion_ids}[]
    screenedAt: ISO8601 timestamp
  },

  uiState: {
    currentPage: "home" | "extract" | "screen" | "report"
    loading: boolean
    error?: string
    progress?: {stage: string, percent: number}
    lastAction: string
  },

  actions: {
    setProtocol(metadata)
    setCriteria(criteria)
    updateCriterion(id, updatedFields)
    deleteCriterion(id)
    addCriterion(criterion)
    revertCriteria()
    setPatientSummary(summaryData)
    setScreeningResults(results)
    setUIState(updates)
    clearSession()
  }
}
```

**Routing:**
- React Router v6 with nested routes
- No page reload on navigation (SPA behavior)
- URL history maintained (back button works)
- Deep linking not supported (MVP assumption: linear workflow)

**Data Flow (Per-Page):**

```
Home Page:
  User upload PDF
  → ProtocolUpload component → POST /api/extract-criteria
  → Update context.protocol + criteria
  → Navigate to Extract page

Extract Page:
  Display criteria from context
  → User edits/deletes/adds criteria (all local)
  → User clicks Next
  → Navigate to Screen page (criteria persisted in context)

Screen Page:
  Display criteria list
  → User inputs patient data (free text OR form)
  → User clicks Screen
  → POST /api/screen-patient (context.criteria + patient summary)
  → Update context.screeningResults
  → Display results (ScreeningResults component)

Report Page:
  Display screening results + PDF preview
  → User clicks Download PDF
  → POST /api/export-report (context.protocol + criteria + results)
  → Browser receives blob
  → Trigger download (filename: TrialMatch_Screening_[...].pdf)
```

**Styling Strategy:**
- Base styles: Tailwind CSS utility classes
- Theme: Light mode (no dark mode in MVP)
- Colors:
  - Primary: Blue (#2563EB)
  - Success: Green (#16A34A) for MEETS badges
  - Danger: Red (#DC2626) for DOES_NOT_MEET badges
  - Warning: Yellow (#CA8A04) for INSUFFICIENT_DATA badges
  - Neutral: Gray (#6B7280)
- Responsive design: Mobile-first (600px min width)

---

### Backend Architecture

**Framework Stack:**
- Framework: FastAPI (Python 3.9+)
- ASGI server: Uvicorn (development) / AWS Lambda / Railway
- Database: None (stateless MVP)
- Session storage: In-memory (lost on restart; acceptable for MVP)
- Async support: async/await throughout for I/O-bound operations

**Router Layer (API Endpoints):**

```python
# routers/extract.py
POST /api/extract-criteria
  Request:
    - file: UploadFile (PDF)
    - headers: {Authorization: session_id}

  Processing:
    1. Validate file (size, type, malware scan)
    2. Store in S3 temporarily
    3. Extract text via PyMuPDF/OCR
    4. Call LLM extraction prompt
    5. Parse JSON response
    6. Store in session

  Response:
    - protocol: {id, title, version, s3Path, textConfidence}
    - criteria: [CriterionModel]
    - errors?: [string]

# routers/screen.py
POST /api/screen-patient
  Request:
    - criteria: [CriterionModel] (from extraction)
    - patientSummary: {freeText OR structured}
    - headers: {Authorization: session_id}

  Processing:
    1. Sanitize patient summary (remove PII)
    2. Call LLM screening prompt
    3. Parse JSON response
    4. Calculate overall eligibility
    5. Aggregate missing data
    6. Store in session

  Response:
    - overallStatus: enum
    - criteriaAssessments: [CriterionAssessmentModel]
    - missingDataAggregated: [...]

# routers/report.py
POST /api/export-report
  Request:
    - headers: {Authorization: session_id}

  Processing:
    1. Retrieve protocol + criteria + results from session
    2. Generate PDF via ReportLab
    3. Sanitize (no PII in output)
    4. Return as blob

  Response:
    - PDF file (application/pdf)

# routers/health.py
GET /health
  Response:
    - status: "ok" | "degraded"
    - checks: {s3: ok, anthropic_api: ok, ...}
```

**Service Layer:**

```python
# services/pdf_parser.py
class PDFParser:
  def extract_text_from_pdf(file_path: str) -> (str, float):
    """
    Extract text from PDF using PyMuPDF with OCR fallback.
    Returns (text, confidence_score).
    """
    try:
      text = pymupdf.extract_text(file_path)
      if len(text) > 30:  # Assume PDF is searchable
        return (text, 0.98)
    except:
      pass

    # Fallback to OCR
    text = tesseract.image_to_string(file_path)
    confidence = estimate_ocr_confidence(file_path)
    return (text, confidence)

# services/criteria_extractor.py
class CriteriaExtractor:
  def extract_criteria(protocol_text: str) -> [CriterionModel]:
    """
    Call Claude API with extraction prompt.
    Return structured criteria.
    """
    response = anthropic.messages.create(
      model="claude-sonnet-4",
      system=EXTRACTION_PROMPT,
      messages=[{
        role: "user",
        content: protocol_text
      }]
    )

    json_response = parse_json_from_response(response)
    criteria = [CriterionModel(**c) for c in json_response]
    return criteria

# services/patient_screener.py
class PatientScreener:
  def screen_patient(
    criteria: [CriterionModel],
    patient_summary: str
  ) -> ScreeningResult:
    """
    Call Claude API with screening prompt.
    Return per-criterion assessments.
    """
    prompt_text = format_screening_prompt(criteria, patient_summary)
    response = anthropic.messages.create(
      model="claude-sonnet-4",
      system=SCREENING_PROMPT,
      messages=[{
        role: "user",
        content: prompt_text
      }]
    )

    assessments = parse_json_from_response(response)
    overall_status = calculate_overall_eligibility(assessments)
    missing_data = aggregate_missing_data(assessments)

    return ScreeningResult(
      overall_status=overall_status,
      criteria_assessments=assessments,
      missing_data=missing_data
    )

# services/report_generator.py
class ReportGenerator:
  def generate_pdf_report(
    protocol: ProtocolModel,
    criteria: [CriterionModel],
    results: ScreeningResult
  ) -> bytes:
    """
    Generate PDF report using ReportLab.
    Return PDF as bytes.
    """
    doc = SimpleDocTemplate(...)
    elements = []

    # Add title, metadata
    # Add overall status
    # Add criteria table (status, reasoning, confidence)
    # Add missing data section
    # Add disclaimers and footers

    doc.build(elements)
    return pdf_bytes
```

**Data Models (Pydantic):**

```python
# models/criteria.py
class CriterionModel(BaseModel):
  criterion_id: str  # I1, I2, E1, E2, ...
  type: Literal["inclusion", "exclusion"]
  description: str
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
  data_points_needed: list[str]
  logic: str | None  # AND/OR/temporal conditions

class CriteriaExtractionResult(BaseModel):
  criteria: list[CriterionModel]
  protocol_metadata: dict  # title, version, nct_number, etc.
  text_confidence: float  # 0-1
  extraction_time_ms: int

# models/screening.py
class CriterionAssessment(BaseModel):
  criterion_id: str
  status: Literal["MEETS", "DOES_NOT_MEET", "INSUFFICIENT_DATA"]
  confidence: Literal["high", "medium", "low"]
  reasoning: str  # 2-3 sentences
  missing_data: list[str] | None

class ScreeningResult(BaseModel):
  overall_status: Literal["ELIGIBLE", "NOT_ELIGIBLE", "REQUIRES_REVIEW"]
  criteria_assessments: list[CriterionAssessment]
  missing_data_aggregated: list[{
    name: str,
    count: int,
    criterion_ids: list[str]
  }]
  screening_time_ms: int

class PatientSummary(BaseModel):
  # Either free_text OR structured, not both required
  free_text: str | None = None

  structured: dict | None = None  # {age, sex, diagnosis, ...}
```

**Dependency Injection:**

```python
# config.py
class Config:
  ANTHROPIC_API_KEY: str  # from Secrets Manager
  AWS_REGION: str = "us-east-1"
  S3_BUCKET: str = "trialmatch-pdfs"
  SESSION_TIMEOUT_MINUTES: int = 30
  MAX_PDF_SIZE_MB: int = 50
  EXTRACTION_TIMEOUT_SECONDS: int = 120
  SCREENING_TIMEOUT_SECONDS: int = 90

# dependencies.py
class SessionManager:
  """In-memory session store (not persistent)."""
  def __init__(self):
    self.sessions: dict[str, SessionData] = {}

  def create_session(self) -> str:
    session_id = secrets.token_urlsafe(32)
    self.sessions[session_id] = SessionData(created_at=now())
    return session_id

  def get_session(self, session_id: str) -> SessionData | None:
    session = self.sessions.get(session_id)
    if session and session.is_expired():
      del self.sessions[session_id]
      return None
    return session

  def update_session(self, session_id: str, updates: dict):
    session = self.get_session(session_id)
    if session:
      session.update(updates)

# main.py
@app.dependency
def get_session_manager() -> SessionManager:
  return SessionManager()

@app.dependency
def get_anthropic_client() -> anthropic.Anthropic:
  api_key = get_secret("anthropic-api-key")
  return anthropic.Anthropic(api_key=api_key)
```

**Middleware Stack:**

```python
# middleware/session.py
class SessionMiddleware:
  """Validate session ID from HTTP-only cookie."""
  async def __call__(self, request: Request, call_next):
    session_id = request.cookies.get("session_id")
    if not session_id:
      session_id = generate_session_id()
      response = await call_next(request)
      response.set_cookie(
        "session_id",
        session_id,
        httponly=True,
        secure=True,
        samesite="strict",
        max_age=1800  # 30 minutes
      )
      return response
    else:
      request.state.session_id = session_id
      return await call_next(request)

# middleware/cors.py
CORSMiddleware(
  app,
  allow_origins=["https://trialmatch.vercel.app"],  # Frontend domain only
  allow_credentials=True,
  allow_methods=["GET", "POST"],
  allow_headers=["Content-Type"],
)

# middleware/rate_limit.py
class RateLimitMiddleware:
  """100 requests per hour per session."""
  async def __call__(self, request: Request, call_next):
    session_id = request.state.session_id
    if session_id not in rate_limiter:
      rate_limiter[session_id] = []

    now = time.time()
    requests_in_hour = [
      r for r in rate_limiter[session_id] if r > now - 3600
    ]

    if len(requests_in_hour) >= 100:
      return JSONResponse(
        {"error": "Rate limit exceeded"},
        status_code=429
      )

    rate_limiter[session_id] = requests_in_hour + [now]
    return await call_next(request)

# middleware/error_handler.py
@app.exception_handler(Exception)
async def exception_handler(request, exc):
  log.error(f"Unhandled error: {exc}")  # Log server-side
  return JSONResponse(
    {"error": "An unexpected error occurred. Please try again."},
    status_code=500  # Generic user message
  )
```

---

## LLM Integration Architecture

### Two-Stage Prompting Strategy

**Design Philosophy:**
- Stage 1 (Extraction): Read protocol → Output structured criteria
- Stage 2 (Screening): Read criteria + patient data → Output structured assessments
- Both stages designed for clarity, exhaustiveness, and auditability
- Emphasis on transparency: show reasoning, don't hide complexity

**Stage 1: Criteria Extraction**

```python
EXTRACTION_PROMPT = """
You are a clinical trial protocol analyst. Your task is to extract all inclusion and exclusion criteria from a clinical trial protocol.

For EVERY inclusion and exclusion criterion mentioned in the protocol, extract and return a JSON array with this structure:

[
  {
    "criterion_id": "I1",
    "type": "inclusion",
    "description": "Plain language description of the criterion (1-2 sentences)",
    "category": "demographics|diagnosis|lab_values|medications|medical_history|procedures|functional_status|other",
    "data_points_needed": ["age", "date_of_birth"],
    "logic": "Simple description of any AND/OR/temporal logic (e.g., 'Age 18-65 AND no prior chemotherapy')"
  },
  {
    "criterion_id": "E1",
    "type": "exclusion",
    ...
  }
]

IMPORTANT GUIDELINES:
1. Be EXHAUSTIVE. Missing a criterion means patients could be incorrectly enrolled. Err on the side of inclusion.
2. Do NOT infer criteria not explicitly stated. If something is not in the protocol, do not assume it.
3. For compound criteria (e.g., "Age 50-75 AND no CVD OR well-controlled HTN"), capture the entire logic in the logic field.
4. For temporal criteria (e.g., "diagnosed within last 6 months"), note the timeframe in logic.
5. For ambiguous criteria, extract as-is and note ambiguity in description.
6. Number inclusion criteria as I1, I2, I3... and exclusion criteria as E1, E2, E3...
7. Ensure no duplicate criteria (same meaning stated twice).
8. For each criterion, specify exactly what data is needed to evaluate it in data_points_needed.

Return ONLY valid JSON. No other text.
"""

# Call structure:
response = client.messages.create(
  model="claude-sonnet-4",
  max_tokens=4000,
  system=EXTRACTION_PROMPT,
  messages=[{
    role: "user",
    content: f"Extract criteria from this protocol:\n\n{protocol_text}"
  }]
)

# Response parsing:
try:
  criteria = json.loads(response.content[0].text)
  # Validate structure
except json.JSONDecodeError:
  # Fallback: user shown error, can retry
```

**Extraction Prompt Design Decisions:**
- Use explicit JSON structure (not natural language enumeration)
- Emphasize exhaustiveness over brevity ("missing a criterion means patients could be incorrectly enrolled")
- Prohibit inference ("do NOT infer criteria not explicitly stated")
- Teach LLM to capture compound logic (AND/OR/temporal)
- Number criteria consistently (I1, I2, E1, E2) for audit trail

**Edge Cases in Extraction:**

| Case | Handling |
|------|----------|
| Ambiguous criterion (e.g., "good renal function") | Extracted as-is; screening returns INSUFFICIENT_DATA unless specific data provided |
| Criterion with implicit conditions | If explicit, captured; if implicit (e.g., "target population: diabetics"), may be missed → coordinator adds manually |
| Temporal criterion without explicit window (e.g., "recently diagnosed") | Captured with note; screening asks for specific date |
| Criterion referencing appendix | Captured as written ("See Appendix B"); coordinator must manually add content if needed |
| Contradictory criteria | Captured both; coordinator flag during review |

---

**Stage 2: Patient Screening**

```python
SCREENING_PROMPT = """
You are a clinical research screening assistant. Your task is to evaluate whether a patient meets, does not meet, or has insufficient data for each eligibility criterion.

For each criterion provided, assess the patient summary and return a JSON array with this structure:

[
  {
    "criterion_id": "I1",
    "status": "MEETS|DOES_NOT_MEET|INSUFFICIENT_DATA",
    "confidence": "high|medium|low",
    "reasoning": "2-3 sentence explanation citing specific evidence from patient summary",
    "missing_data": ["specific data needed", "e.g., date of diagnosis"]
  }
]

CRITICAL GUIDELINES:
1. Return INSUFFICIENT_DATA if in doubt. The coordinator will verify.
2. Do NOT assume or infer patient data. If it's not in the summary, you can't know.
3. For MEETS: evidence is clear and patient meets all conditions in criterion.
4. For DOES_NOT_MEET: evidence shows patient fails criterion (explicitly or by contradiction).
5. For INSUFFICIENT_DATA: data needed to judge is missing; specify exactly what in missing_data.
6. Confidence calibration:
   - HIGH: criterion is clear AND patient data is complete for that criterion
   - MEDIUM: criterion is clear but data incomplete, OR criterion ambiguous but data complete
   - LOW: both criterion and patient data are ambiguous
7. Reasoning must cite specific numbers/values from patient summary (e.g., "HbA1c 8.2% exceeds limit of 8.0%").
8. Never return MEETS for ambiguous criteria without clear supporting evidence.

Return ONLY valid JSON. No other text.
"""

# Call structure:
formatted_criteria = format_criteria_for_screening(criteria)
prompt_text = f"""
Evaluate this patient against the following criteria:

{formatted_criteria}

Patient Summary:
{patient_summary}

Return assessments in JSON format.
"""

response = client.messages.create(
  model="claude-sonnet-4",
  max_tokens=4000,
  system=SCREENING_PROMPT,
  messages=[{
    role: "user",
    content: prompt_text
  }]
)

# Response parsing:
assessments = json.loads(response.content[0].text)
```

**Screening Prompt Design Decisions:**
- Emphasize INSUFFICIENT_DATA as safe choice ("If in doubt, return INSUFFICIENT_DATA")
- Explicitly prohibit inference ("Do NOT assume or infer patient data")
- Calibrate confidence by criterion clarity × patient data completeness
- Require specific evidence in reasoning (numbers, not generalizations)
- Teach LLM to specify missing data precisely

**Confidence Calibration:**

| Criterion Clarity | Patient Data | Confidence | Example |
|---|---|---|---|
| Clear (explicit threshold) | Complete (all data for criterion) | HIGH | "Criterion: HbA1c <8%. Patient: HbA1c 7.8%. MEETS with HIGH confidence." |
| Clear | Incomplete (some data missing) | MEDIUM | "Criterion: HbA1c <8% with recent labs. Patient: HbA1c 7.8% but lab date unknown. MEETS with MEDIUM confidence (need lab date)." |
| Ambiguous | Complete | MEDIUM | "Criterion: 'stable disease' (subjective). Patient: No active treatment, stable on meds. INSUFFICIENT_DATA with MEDIUM confidence (need imaging or clinical assessment)." |
| Ambiguous | Incomplete | LOW | "Criterion: 'good functional status' (vague). Patient: Limited data. INSUFFICIENT_DATA with LOW confidence (need specific performance status)." |

**Reasoning Quality Requirements:**
- Must cite specific values from patient summary (not generalizations)
- Must explain logic (not just verdict)
- Must note assumptions or limitations
- Examples:
  - Good: "Patient HbA1c 8.2% exceeds criterion limit of 8.0% by 0.2 percentage points; DOES_NOT_MEET."
  - Bad: "HbA1c too high."
  - Good: "Criterion requires eGFR >60. Patient eGFR not provided in summary; INSUFFICIENT_DATA (need recent renal panel)."
  - Bad: "No eGFR data."

---

### Token Budget and Cost Management

**Token Budgeting Strategy:**

| Stage | Typical Input Tokens | Typical Output Tokens | Total per Call | Example Cost (Sonnet 4) |
|-------|---|---|---|---|
| Extraction (50-page protocol) | 12,000 | 1,500 | 13,500 | $0.27 |
| Screening (20 criteria, patient summary) | 3,500 | 1,200 | 4,700 | $0.09 |
| Per-patient screening (avg) | ~$0.09 | — | — | $0.09 |
| Report export (PDF text gen) | 2,000 | 500 | 2,500 | $0.05 |

**Cost Estimates:**
- 100 protocols extracted: 100 × $0.27 = $27
- 1,000 patients screened (10 per protocol): 1,000 × $0.09 = $90
- Total monthly estimate (assume 50 active trials, 500 patient screenings): ~$50-100/month

**Cost Control:**
- Cache extracted criteria (don't re-extract same protocol)
- Reuse criteria across multiple patient screenings (free, just re-prompt)
- Set API quota alerts (budget: $500/month; alert at $250)
- No batch optimization needed for MVP (requests are already small)

---

### Error Handling in LLM Integration

**Retry Strategy:**
- Request timeout (>60 sec for extraction, >90 sec for screening): Retry once after 5 seconds
- API error (5xx response): Retry up to 3 times with exponential backoff (5s, 10s, 20s)
- Rate limit (429): Wait and retry (Claude handles backoff)
- Invalid JSON response: Don't retry (likely prompt issue); show error to user with option to retry

**Fallback Behavior:**
- Extraction failure after retries: "Criteria extraction failed. Try a shorter/clearer protocol, or contact support."
- Screening failure after retries: "Screening failed. Your patient data and criteria are saved. Try again in a few moments."
- No fallback to simpler model (no Claude 3.5 Sonnet fallback to Opus); explicit failure is better than degraded accuracy

**Prompt Versioning:**
- Extraction prompt: v1.0 (current) in `prompts/extraction.py`
- Screening prompt: v1.0 (current) in `prompts/screening.py`
- Version tracked as comment in prompt definition
- Changes to prompts require evaluation (see Testing Strategy doc)
- Historical versions retained for audit

---

## Data Models (Detailed)

### Pydantic Models (Backend)

```python
# models/criteria.py

class CriterionModel(BaseModel):
  """Represents a single inclusion or exclusion criterion."""

  criterion_id: str
    # Format: I1, I2, ... for inclusion; E1, E2, ... for exclusion

  type: Literal["inclusion", "exclusion"]

  description: str
    # Plain language description, 1-2 sentences
    # Example: "HbA1c ≤ 8.0% at time of enrollment"

  category: Literal[
    "demographics",    # Age, sex, gender, location
    "diagnosis",       # Primary/secondary diagnosis, indication
    "lab_values",      # Blood tests, imaging, vital signs
    "medications",     # Current/prior medications
    "medical_history", # Prior illnesses, surgeries, hospitalizations
    "procedures",      # Prior procedures, interventions
    "functional_status", # Performance status, ADL
    "other"            # Anything else
  ]

  data_points_needed: list[str]
    # Specific data needed to evaluate criterion
    # Example: ["HbA1c_value", "HbA1c_date"]

  logic: str | None = None
    # AND/OR/temporal conditions
    # Example: "Age 50-75 AND no prior chemotherapy"
    # Example: "Diagnosed within 6 months"

# models/screening.py

class PatientSummary(BaseModel):
  """Patient demographic and clinical data."""

  free_text: str | None = None
    # Unstructured clinical notes
    # Example: "55-year-old female with Type 2 Diabetes..."

  structured: dict | None = None
    # Or structured format (if provided)
    # {
    #   "age": 55,
    #   "sex": "Female",
    #   "primary_diagnosis": "Type 2 Diabetes Mellitus",
    #   "lab_values": [
    #     {"name": "HbA1c", "value": 8.2, "unit": "%", "date": "2024-03-10"}
    #   ],
    #   "medications": ["Metformin 1000mg BID"],
    #   "comorbidities": ["Hypertension"]
    # }

class CriterionAssessment(BaseModel):
  """Assessment of patient against one criterion."""

  criterion_id: str
    # Link back to original criterion

  status: Literal["MEETS", "DOES_NOT_MEET", "INSUFFICIENT_DATA"]

  confidence: Literal["high", "medium", "low"]
    # Calibrated by criterion clarity + patient data completeness

  reasoning: str
    # 2-3 sentences citing specific evidence
    # Example: "Patient HbA1c 8.2% exceeds criterion threshold of 8.0%."

  missing_data: list[str] | None = None
    # If status = INSUFFICIENT_DATA, what's needed
    # Example: ["eGFR result (within last 3 months)"]

class ScreeningResult(BaseModel):
  """Complete screening assessment for one patient."""

  overall_status: Literal["ELIGIBLE", "NOT_ELIGIBLE", "REQUIRES_REVIEW"]
    # ELIGIBLE: all inclusion MEETS, no exclusion DOES_NOT_MEET, no INSUFFICIENT_DATA
    # NOT_ELIGIBLE: any inclusion DOES_NOT_MEET OR any exclusion DOES_NOT_MEET
    # REQUIRES_REVIEW: any INSUFFICIENT_DATA (regardless of other assessments)

  criteria_assessments: list[CriterionAssessment]
    # One assessment per criterion

  missing_data_aggregated: list[dict]
    # Deduplicated list of missing data across all INSUFFICIENT_DATA criteria
    # [{
    #   "name": "Recent HbA1c value",
    #   "count": 3,  # Needed by 3 criteria
    #   "criterion_ids": ["I2", "E1", "E3"]
    # }]

  screening_time_ms: int
    # Time in milliseconds to run screening

  screened_at: datetime
    # Timestamp of screening

class CriteriaExtractionResult(BaseModel):
  """Result of criteria extraction from protocol."""

  criteria: list[CriterionModel]

  protocol_metadata: dict
    # {
    #   "title": "A Phase II Study of...",
    #   "version": "3.0",
    #   "nct_number": "NCT05123456",
    #   "sponsor": "Pharma Inc.",
    #   "estimated_enrollment": 200
    # }

  text_confidence: float
    # 0.0-1.0; confidence in text extraction quality
    # >0.95: searchable PDF with clear text
    # 0.80-0.95: scanned PDF with decent OCR
    # <0.80: scanned/low-quality PDF; user warned

  extraction_time_ms: int

  extracted_at: datetime
```

### TypeScript Interfaces (Frontend)

```typescript
// types/Protocol.ts

export interface Protocol {
  id: string  // UUID
  title: string
  version?: string
  nctNumber?: string
  sponsor?: string
  s3Path: string
  textConfidence: number  // 0-1
  extractedAt: string  // ISO8601
}

// types/Criterion.ts

export interface Criterion {
  criterion_id: string  // I1, I2, E1, E2...
  type: 'inclusion' | 'exclusion'
  description: string
  category: CriteriaCategory
  data_points_needed: string[]
  logic?: string
  edited?: boolean
}

export type CriteriaCategory =
  | 'demographics'
  | 'diagnosis'
  | 'lab_values'
  | 'medications'
  | 'medical_history'
  | 'procedures'
  | 'functional_status'
  | 'other'

// types/Patient.ts

export interface PatientSummary {
  freeText?: string
  structured?: {
    age?: number
    sex?: string
    primaryDiagnosis?: string
    secondaryDiagnoses?: string[]
    currentMeds?: string[]
    labValues?: LabValue[]
    comorbidities?: string[]
    functionalStatus?: string
    procedures?: string[]
    allergies?: string[]
    pregnancyStatus?: string
    additionalNotes?: string
  }
  piiWarning?: boolean
}

export interface LabValue {
  name: string
  value: number
  unit: string
  date?: string
}

// types/Screening.ts

export interface CriterionAssessment {
  criterion_id: string
  status: 'MEETS' | 'DOES_NOT_MEET' | 'INSUFFICIENT_DATA'
  confidence: 'high' | 'medium' | 'low'
  reasoning: string
  missing_data?: string[]
  overridden?: boolean
}

export interface ScreeningResult {
  overall_status: 'ELIGIBLE' | 'NOT_ELIGIBLE' | 'REQUIRES_REVIEW'
  criteria_assessments: CriterionAssessment[]
  missing_data_aggregated: {
    name: string
    count: number
    criterion_ids: string[]
  }[]
  screened_at: string
}
```

---

## API Contract

### Endpoint: POST /api/extract-criteria

**Purpose:** Upload protocol PDF and extract eligibility criteria.

**Request:**
```
POST /api/extract-criteria
Content-Type: multipart/form-data
Cookie: session_id=...

Body:
  file: (PDF file, binary)
```

**Response (200 OK):**
```json
{
  "protocol": {
    "id": "proto-uuid-123",
    "title": "A Phase II Study of Drug X in Type 2 Diabetes",
    "version": "2.0",
    "nct_number": "NCT05123456",
    "sponsor": "Pharma Inc.",
    "s3_path": "s3://trialmatch-pdfs/proto-uuid-123.pdf",
    "text_confidence": 0.98,
    "extracted_at": "2026-03-24T10:30:00Z"
  },
  "criteria": [
    {
      "criterion_id": "I1",
      "type": "inclusion",
      "description": "Age 18-75 years at time of enrollment",
      "category": "demographics",
      "data_points_needed": ["age", "date_of_birth"],
      "logic": "18 ≤ age ≤ 75"
    },
    {
      "criterion_id": "I2",
      "type": "inclusion",
      "description": "Confirmed diagnosis of Type 2 Diabetes Mellitus",
      "category": "diagnosis",
      "data_points_needed": ["diagnosis", "diagnosis_date"],
      "logic": null
    },
    {
      "criterion_id": "I3",
      "type": "inclusion",
      "description": "HbA1c between 7.0% and 10.5% at screening",
      "category": "lab_values",
      "data_points_needed": ["HbA1c_value", "HbA1c_date"],
      "logic": "7.0 ≤ HbA1c ≤ 10.5"
    },
    {
      "criterion_id": "E1",
      "type": "exclusion",
      "description": "Type 1 Diabetes Mellitus or secondary diabetes",
      "category": "diagnosis",
      "data_points_needed": ["diabetes_type"],
      "logic": null
    }
  ],
  "text_confidence": 0.98,
  "extraction_time_ms": 5200
}
```

**Error Response (400 Bad Request):**
```json
{
  "error": "File must be a PDF under 50 MB"
}
```

**Error Response (413 Payload Too Large):**
```json
{
  "error": "File exceeds 50 MB limit"
}
```

**Error Response (500 Internal Server Error):**
```json
{
  "error": "Extraction failed. Please try again or contact support."
}
```

---

### Endpoint: POST /api/screen-patient

**Purpose:** Evaluate patient against extracted criteria.

**Request:**
```
POST /api/screen-patient
Content-Type: application/json
Cookie: session_id=...

Body:
{
  "criteria": [
    {
      "criterion_id": "I1",
      "type": "inclusion",
      "description": "Age 18-75 years",
      ...
    }
  ],
  "patient_summary": {
    "free_text": "55-year-old female, Type 2 Diabetes Mellitus diagnosed 2019, HbA1c 8.2% (2024-03-10), BMI 31.4, current meds: Metformin 1000mg BID, Lisinopril 10mg daily, comorbidities: hypertension (controlled), mild osteoarthritis, no history of CVD or cancer, not pregnant, no penicillin allergy"
  }
  // OR:
  "patient_summary": {
    "structured": {
      "age": 55,
      "sex": "Female",
      "primary_diagnosis": "Type 2 Diabetes Mellitus",
      "lab_values": [
        {
          "name": "HbA1c",
          "value": 8.2,
          "unit": "%",
          "date": "2024-03-10"
        }
      ],
      ...
    }
  }
}
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
      "reasoning": "Patient has confirmed Type 2 Diabetes Mellitus diagnosed in 2019.",
      "missing_data": null
    },
    {
      "criterion_id": "I3",
      "status": "DOES_NOT_MEET",
      "confidence": "high",
      "reasoning": "Patient HbA1c 8.2% exceeds upper limit of 8.0% specified in criterion.",
      "missing_data": null
    },
    {
      "criterion_id": "E1",
      "status": "MEETS",
      "confidence": "high",
      "reasoning": "Patient has Type 2 Diabetes, not Type 1 or secondary diabetes; exclusion not triggered.",
      "missing_data": null
    }
  ],
  "missing_data_aggregated": [],
  "screened_at": "2026-03-24T10:35:00Z",
  "screening_time_ms": 3100
}
```

**Error Response (400 Bad Request):**
```json
{
  "error": "No patient summary provided (either free_text or structured required)"
}
```

**Error Response (500 Internal Server Error):**
```json
{
  "error": "Screening failed. Please try again in a few moments."
}
```

---

### Endpoint: POST /api/export-report

**Purpose:** Generate and download PDF screening report.

**Request:**
```
POST /api/export-report
Content-Type: application/json
Cookie: session_id=...

Body:
{
  // Session ID from cookie; no body required for MVP
  // (alternative: could include custom report options)
}
```

**Response (200 OK):**
```
Content-Type: application/pdf
Content-Disposition: attachment; filename="TrialMatch_Screening_NCT05123456_2026-03-24_103500.pdf"

[Binary PDF content]
```

**Error Response (404 Not Found):**
```json
{
  "error": "No screening results found in session. Please complete screening first."
}
```

**Error Response (500 Internal Server Error):**
```json
{
  "error": "Report generation failed. Please try again."
}
```

---

## Failure Modes and Fallback Strategies

### Critical Failure: Anthropic API Unavailable

**Failure Mode:** Claude API down or rate limited (429 Too Many Requests).

**Impact:** Extraction and screening cannot proceed.

**Detection:** API returns 5xx or 429 response.

**Fallback Strategy:**
1. First request timeout/error: Retry immediately (once)
2. Second failure: Exponential backoff (5 sec wait, retry)
3. Third failure: Show user error message, offer manual extraction or retry in background

**User Experience:**
- "Extraction service temporarily unavailable. Please try again in a few moments."
- (No data loss; user can retry when service recovers)

---

### Important Failure: S3 Unavailable

**Failure Mode:** S3 upload fails (PDF storage).

**Impact:** Cannot store temporary protocol PDFs.

**Detection:** Boto3 S3 client raises exception.

**Fallback Strategy:**
1. Retry upload once after 5 seconds
2. If still failing: Store PDF in memory temporarily (not persistent across restarts)
3. If memory storage used: Warn user that extraction will be lost if service restarts

**User Experience:**
- "PDF storage temporarily unavailable. Working with in-memory copy (data will be lost if you navigate away)."
- Force re-upload on session restart

---

### Data Persistence Failure: Session Lost (Backend Restart)

**Failure Mode:** Backend restarts; in-memory sessions cleared.

**Impact:** User's current work (criteria edits, patient input, results) lost.

**Detection:** Not preventable; user will see session timeout or need to restart.

**Design Decision:** Acceptable for MVP (no database, session-only). Production would require persistent session store.

**User Experience:**
- Redirect to home page: "Your session expired. Please start over."
- Emphasize: Export reports before closing app

**Mitigation:**
- Session timeout warning at 25 minutes (before 30 min timeout)
- Encourage PDF export ("Download your report now")

---

### PDF Parsing Failure: OCR Quality Too Low

**Failure Mode:** Scanned PDF has poor quality; OCR confidence <80%.

**Impact:** Extracted text may be inaccurate; criteria may be wrong or incomplete.

**Detection:** text_confidence score <0.80.

**Fallback Strategy:**
1. Show warning to user: "Text extraction confidence is low (45%). Please carefully review extracted criteria."
2. User can:
   - Manually correct criteria before screening
   - Upload higher-quality version
   - Proceed with low confidence (at own risk)

**User Experience:**
- Yellow warning banner with option to re-upload or proceed

---

### Logical Failure: LLM Returns Invalid JSON

**Failure Mode:** Claude response is not valid JSON (unlikely but possible).

**Impact:** Extraction or screening cannot parse response.

**Detection:** json.loads() fails.

**Fallback Strategy:**
1. Log error with response text for debugging
2. Do NOT retry (likely prompt issue, not transient)
3. Show user error: "Extraction response format invalid. Please try again or contact support."

**User Experience:**
- Clear error message; user can retry or contact support

---

### Logical Failure: Missing Criteria in Extraction

**Failure Mode:** LLM misses a criterion mentioned in protocol.

**Impact:** Patient screening incomplete; could miss ineligibility.

**Detection:** Cannot be detected automatically; found during manual review or in production.

**Mitigation:**
- Prompt emphasizes exhaustiveness: "Missing a criterion means patients could be incorrectly enrolled"
- Coordinator reviews criteria before screening (can add missing criteria)
- Evaluation testing measures extraction completeness >90%

---

## Performance Considerations and Bottlenecks

### Identified Bottlenecks

**1. LLM API Latency**
- Current: ~5-10 seconds per extraction, ~3-5 seconds per screening
- Bottleneck: Anthropic Claude API network latency + model inference time
- Optimization: Caching (extract once, reuse for multiple patients); batch processing (future)
- Not optimizable in MVP without model changes

**2. PDF Text Extraction**
- Current: ~1-2 seconds for searchable PDF; ~5-10 seconds for OCR
- Bottleneck: PyMuPDF performance; Tesseract OCR for large scanned PDFs
- Optimization: Use faster OCR library (Paddleocr); chunk pages and parallel process
- Acceptable for MVP

**3. Frontend Rendering (Large Results)**
- Current: ~500ms for 80 criteria results
- Bottleneck: React re-render with large arrays
- Optimization: Virtualization (show only visible criteria); memoization; lazy loading
- Not needed for MVP (<30 criteria typical)

**4. PDF Report Generation**
- Current: ~5-8 seconds for complex report with tables
- Bottleneck: ReportLab rendering and page layout
- Optimization: Simpler template; pre-rendered components (future)
- Acceptable for MVP

---

### Performance Targets

| Operation | Target | Acceptable | Current Estimate |
|---|---|---|---|
| PDF Upload | <5s | <10s | ~2s (network dependent) |
| Text Extraction | <15s | <30s | ~5-10s |
| Criteria Extraction (LLM) | <30s | <60s | ~5-10s |
| Patient Screening (LLM) | <15s | <30s | ~3-5s |
| Report Generation | <10s | <15s | ~5-8s |
| Total workflow (protocol → report) | <90s | <150s | ~30-50s (typical) |

---

### Scalability Path (MVP → Phase 2+)

**MVP Bottlenecks (Single Session):**
- In-memory session storage → Not scalable to 100s of concurrent users
- Single-threaded extraction/screening → Sequential processing only
- No caching → Re-prompts for identical protocols

**Phase 2+ Improvements:**

1. **Session Persistence:**
   - Add PostgreSQL/DynamoDB for session storage
   - Allows recovery from restarts
   - Enables user accounts and multi-session workflows

2. **Caching Layer:**
   - Cache extracted criteria in Redis
   - Same protocol → instant retrieval
   - Save 5-10 seconds per reuse

3. **Async Task Queue:**
   - Extraction/screening as background tasks (Celery or AWS SQS)
   - Frontend polls for results
   - Non-blocking UI; support many concurrent requests

4. **Batch Screening:**
   - Process 10+ patients per API call
   - Reduction in API overhead
   - Support CSV import use case

5. **Multi-Trial Matching:**
   - Patient profile → search across trial database
   - ClinicalTrials.gov API integration
   - Pre-screen before extraction

---

## Infrastructure Design (AWS)

### Compute

**Lambda (for stateless API tier):**
- Function: `trialmatch-extract`, `trialmatch-screen`, `trialmatch-report`
- Memory: 1024 MB (sufficient for PDF parsing + LLM calls)
- Timeout: 120 seconds (meets extraction timeout requirement)
- Concurrency: Unreserved (auto-scale with traffic)
- Runtime: Python 3.9+

**Alternative: ECS Fargate (if choosing containerized backend):**
- Container image: FastAPI + uvicorn
- vCPU: 0.5-1 vCPU
- Memory: 1 GB
- Task count: 1-5 (auto-scaling based on CPU/memory)
- Load balancer: ALB (Application Load Balancer)

**Recommendation:** Lambda for MVP (lower operational overhead); Fargate for Phase 2+ (persistent connections, caching).

---

### Storage

**S3 (Temporary PDF Storage):**
- Bucket: `trialmatch-pdfs-[environment]` (dev, staging, prod)
- Encryption: Server-side (SSE-S3)
- Versioning: Disabled
- Lifecycle policy:
  ```json
  {
    "Rules": [
      {
        "Id": "delete-after-24h",
        "Status": "Enabled",
        "Expiration": { "Days": 1 },
        "NoncurrentVersionExpiration": { "NoncurrentDays": 1 }
      }
    ]
  }
  ```
- Access logging: Enabled (CloudTrail for audit)
- Block public access: Enabled
- CORS: Disabled (Lambda accesses, not frontend)

---

### Secrets Management

**AWS Secrets Manager:**
- Secret: `trialmatch/anthropic-api-key`
- Rotation: Manual (annual or on key compromise)
- Access: IAM role for Lambda/Fargate (principle of least privilege)
- Encryption: AWS KMS default key

**Alternative (Development Only):**
- `.env` file (never committed; use `.env.example` as template)
- Environment variables (set in Lambda via AWS console)

---

### CDN and Frontend Hosting

**Vercel (Frontend):**
- Deployment: Git push to main branch → automatic deploy
- CDN: Vercel's global CDN (Cloudflare)
- SSL: Auto-issued Let's Encrypt
- Caching:
  - HTML (index.html): Cache-Control max-age=0 (no cache, revalidate)
  - JS/CSS: Cache-Control max-age=31536000 (1 year, content-hashed)
- Serverless functions: Not used (all logic in FastAPI backend)

**Alternative: CloudFront (if hosting on own infra):**
- Origin: S3 bucket with React build artifacts
- Caching behavior:
  - `/index.html` → Cache-Control no-cache
  - `/js/*`, `/css/*` → Cache-Control max-age=31536000
- Compression: Enable gzip
- Geo-restriction: None (or restricted to US/EU for HIPAA)

---

### Logging and Monitoring

**CloudWatch (Logs and Metrics):**
- Log groups:
  - `/aws/lambda/trialmatch-extract`
  - `/aws/lambda/trialmatch-screen`
  - `/aws/lambda/trialmatch-report`
- Retention: 30 days (default)
- Log filters:
  - Error detection (ERROR, EXCEPTION keywords)
  - Performance metrics (extraction_time_ms, screening_time_ms)
  - Rate limit hits (429 responses)
- Alarms:
  - Error rate >1%: SNS notification
  - P99 latency >60s: CloudWatch alarm
  - API rate limit: CloudWatch alarm

**Custom Metrics:**
```python
# CloudWatch metrics to track
import boto3
cloudwatch = boto3.client('cloudwatch')

cloudwatch.put_metric_data(
  Namespace='TrialMatch',
  MetricData=[
    {
      'MetricName': 'ExtractionTime',
      'Value': extraction_time_ms,
      'Unit': 'Milliseconds'
    },
    {
      'MetricName': 'ScreeningTime',
      'Value': screening_time_ms,
      'Unit': 'Milliseconds'
    },
    {
      'MetricName': 'ExtractionErrors',
      'Value': 1 if error else 0,
      'Unit': 'Count'
    }
  ]
)
```

---

### IAM Roles and Policies

**Lambda Execution Role:**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:GetObject",
        "s3:DeleteObject"
      ],
      "Resource": "arn:aws:s3:::trialmatch-pdfs-*/*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue"
      ],
      "Resource": "arn:aws:secretsmanager:*:*:secret:trialmatch/*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:*:*:*"
    }
  ]
}
```

---

## Deployment Architecture

### CI/CD Pipeline (GitHub Actions)

```yaml
# .github/workflows/deploy.yml

name: Deploy TrialMatch

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.9'
      - name: Install backend dependencies
        run: pip install -r backend/requirements.txt
      - name: Run backend tests
        run: pytest backend/tests/
      - uses: actions/setup-node@v3
        with:
          node-version: '18'
      - name: Install frontend dependencies
        run: npm install --prefix frontend
      - name: Run frontend tests
        run: npm run test --prefix frontend
      - name: Lint backend
        run: flake8 backend/app/
      - name: Lint frontend
        run: npm run lint --prefix frontend

  deploy-backend:
    needs: test
    runs-on: ubuntu-latest
    if: github.event_name == 'push' && github.ref == 'refs/heads/main'
    steps:
      - uses: actions/checkout@v3
      - name: Deploy to AWS Lambda / Fargate
        run: |
          # Script: deploy.sh
          ./scripts/deploy_backend.sh ${{ secrets.AWS_REGION }}
        env:
          AWS_ACCESS_KEY_ID: ${{ secrets.AWS_ACCESS_KEY_ID }}
          AWS_SECRET_ACCESS_KEY: ${{ secrets.AWS_SECRET_ACCESS_KEY }}

  deploy-frontend:
    needs: test
    runs-on: ubuntu-latest
    if: github.event_name == 'push' && github.ref == 'refs/heads/main'
    steps:
      - uses: actions/checkout@v3
      - name: Deploy to Vercel
        run: npm run deploy --prefix frontend
        env:
          VERCEL_TOKEN: ${{ secrets.VERCEL_TOKEN }}
```

---

## Security Architecture

### No-Persistence Model

**Core Principle:** No patient data persisted anywhere (not even temporarily).

**Implementation:**
1. Session data in-memory only (Lambda/Fargate memory, not database)
2. PDF uploaded → S3 → deleted after 24h (S3 lifecycle policy)
3. Patient summary → sent to LLM → discarded after response
4. Screening results → returned to frontend → stored in session → discarded on logout
5. Audit logs → de-identified only (timestamp, trial ID, status, no patient data or clinical details)

**Enforcement:**
- No ORM or database connections (no persistent storage)
- Request validation: PII detection regex warns user before screening
- API calls: Patient data sent encrypted (HTTPS); API response discarded
- Error messages: Sanitized (no sensitive data in logs)

---

### Input Validation and Sanitization

**PDF Upload:**
- Validation: File type (must be PDF), size (max 50 MB)
- Malware scan: ClamAV or AWS Macie
- Rejection: Unsupported formats, corrupted files

**Patient Summary (Text):**
- Validation: Max 5,000 characters
- Sanitization: HTML tags removed (no XSS), PII regex detection (warning shown)
- Before LLM: Placeholder removal for confidence (if PII detected, substitute "PATIENT" for names, etc.)

**Patient Summary (Form):**
- Validation: Age must be integer 18-120; dropdown selections only; field length limits
- Sanitization: HTML tags removed; numbers validated as numeric
- Before LLM: Convert to narrative text

---

### API Security

**HTTPS Enforcement:**
- All endpoints HTTPS only (TLS 1.2+)
- HTTP redirect to HTTPS

**CORS Configuration:**
```python
CORSMiddleware(
  app,
  allow_origins=["https://trialmatch.vercel.app"],  # Frontend domain only
  allow_credentials=True,
  allow_methods=["GET", "POST"],
  allow_headers=["Content-Type"],
  expose_headers=["X-Process-Time"],
  max_age=3600
)
```

**Session Management:**
- Session ID: 128-bit random token (secrets.token_urlsafe(32))
- Cookie: HTTP-only, Secure (HTTPS), SameSite=Strict
- Validation: Every request must have valid session ID
- Timeout: 30 minutes inactivity; automatic logout

**Request Validation:**
- Max request body size: 10 MB
- Request timeout: 120 seconds
- Rate limit: 100 requests per session per hour
- Invalid requests: 400 Bad Request (never expose internal error details)

---

## Sign-Off

| Role | Name | Date | Signature |
|------|------|------|-----------|
| CTO / Tech Lead | [Name] | 2026-03-24 | — |
| DevOps Lead | [Name] | 2026-03-24 | — |
| Security Lead | [Name] | 2026-03-24 | — |

---

**END OF TECHNICAL ARCHITECTURE DOCUMENT**
