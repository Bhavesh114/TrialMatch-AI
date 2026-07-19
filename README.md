# TrialMatch AI - Clinical Trial Eligibility Screener

![TrialMatch AI](https://img.shields.io/badge/status-production--ready-brightgreen)
![Python](https://img.shields.io/badge/python-3.11+-blue)
![React](https://img.shields.io/badge/react-18.2+-blue)
![FastAPI](https://img.shields.io/badge/fastapi-0.104+-green)

A production-grade AI system for automatically extracting eligibility criteria from clinical trial protocols and screening de-identified patients for trial enrollment.

**[Live Demo](#)** • **[Documentation](#)** • **[API Reference](#)**

---

## Overview

TrialMatch AI streamlines clinical trial patient recruitment by:

1. **Automatic Criteria Extraction**: Upload a protocol PDF → AI extracts structured eligibility criteria
2. **Patient Screening**: Input de-identified patient data → Get immediate eligibility assessment
3. **Professional Reports**: Generate PDF reports for clinical review

**Time Saved**: Convert hours of manual protocol review to seconds.

### Key Features

- ✅ **NCT ID Integration** - Primary flow: paste an NCT ID → criteria pulled directly from ClinicalTrials.gov API v2 (no PDF needed)
- ✅ **PDF Protocol Parsing** - Fallback for sponsor protocols not registered on CT.gov; handles digital and scanned PDFs with OCR
- ✅ **AI-Powered Extraction** - Claude Sonnet 4 extracts structured criteria with confidence scoring
- ✅ **Detailed Assessment** - Per-criterion eligibility with evidence cited and missing data flagged
- ✅ **Editable Criteria** - Clinicians review and modify extracted criteria before screening
- ✅ **De-Identification Focus** - Built to process de-identified data only
- ✅ **PDF Reports** - Professional screening reports for medical records
- ✅ **No Patient Persistence** - Session data cleared on browser close (privacy-first)

---

## System Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Frontend (React + Vite)              │
│  - ProtocolUpload  - CriteriaReview  - PatientInput     │
│  - ScreeningResults - ReportExport   - Pages/Routing    │
│  - Tailwind CSS styling + React Router                  │
└──────────────────────┬──────────────────────────────────┘
                       │
                       │ HTTPS
                       │
┌──────────────────────┴──────────────────────────────────┐
│              Backend API (FastAPI + Python)             │
│                                                          │
│  ┌─ /api/extract-criteria (POST)                        │
│  │  └─ PDF Parsing (PyMuPDF + Tesseract OCR)            │
│  │  └─ Criteria Extraction (Claude API)                 │
│  │  └─ Result: CriteriaExtractionResult JSON            │
│  │                                                       │
│  ├─ /api/screen-patient (POST)                          │
│  │  └─ Patient Validation                               │
│  │  └─ Per-Criterion Evaluation (Claude API)            │
│  │  └─ Result: ScreeningResult JSON                     │
│  │                                                       │
│  └─ /api/export-report (POST)                           │
│     └─ PDF Report Generation (reportlab)                │
│     └─ Result: PDF bytes (streaming download)           │
│                                                          │
│  Dependencies:                                           │
│  - Anthropic SDK (Claude API)                           │
│  - PyMuPDF, Tesseract (PDF parsing)                     │
│  - reportlab (PDF generation)                           │
│  - Pydantic (data validation)                           │
└──────────────────────────────────────────────────────────┘
```

---

## ClinicalTrials.gov API v2 Integration

> **Architecture note (2026-06):** CT.gov's CSV export contains only metadata (30 columns) — it does **not** include eligibility criteria. The JSON API v2 is the correct source and returns the full criteria text pre-split into inclusion/exclusion sections.

Primary input flow:

```
NCT ID  →  GET https://clinicaltrials.gov/api/v2/studies/{nct_id}
        →  .protocolSection.eligibilityModule.eligibilityCriteria  (free text)
        →  .protocolSection.eligibilityModule.minimumAge / maximumAge / sex
        →  Claude extracts structured {criterion_id, type, description} objects
        →  Patient screening
```

PDF upload is preserved as a fallback for:
- Sponsor protocols with additional operational criteria not yet registered on CT.gov
- Amended protocols where CT.gov has not been updated
- Internal/proprietary trial documents

No API key is required for the CT.gov public API.

---

## Tech Stack

### Backend
- **Framework**: FastAPI 0.104
- **Language**: Python 3.11+
- **PDF Processing**: PyMuPDF (pymupdf), Tesseract OCR, pdf2image
- **LLM API**: Anthropic Claude 3.5 Sonnet
- **Data Validation**: Pydantic v2
- **Report Generation**: reportlab
- **Deployment**: Docker, Railway (or AWS Lambda)

### Frontend
- **Framework**: React 18.2 with Hooks
- **Build Tool**: Vite 5.0
- **Styling**: Tailwind CSS 3.3
- **Router**: React Router v6
- **HTTP Client**: Axios
- **Deployment**: Vercel

---

## Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- Docker (recommended for backend)
- Anthropic API key (get at https://console.anthropic.com)

### Local Development

#### Backend Setup
```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

# Install dependencies
pip install -r requirements.txt

# Set environment variables
export ANTHROPIC_API_KEY="your-api-key-here"
export LOG_LEVEL="DEBUG"

# Run server (http://localhost:8000)
python -m uvicorn app.main:app --reload
```

#### Frontend Setup
```bash
cd frontend

# Install dependencies
npm install

# Run dev server (http://localhost:5173)
npm run dev
```

#### Using Docker
```bash
# Build and run backend
docker build -t trialmatch-backend ./backend
docker run -p 8000:8000 \
  -e ANTHROPIC_API_KEY="your-key" \
  trialmatch-backend
```

---

## API Documentation

### POST /api/extract-criteria
Extract eligibility criteria from a protocol PDF.

**Request:**
```http
POST /api/extract-criteria HTTP/1.1
Content-Type: multipart/form-data

file: <PDF bytes>
trial_name: "LANDMARK-2 Heart Failure Study" (optional)
```

**Response:**
```json
{
  "protocol_id": "abc123def456",
  "trial_name": "LANDMARK-2",
  "criteria": [
    {
      "criterion_id": "I1",
      "type": "inclusion",
      "description": "Age 18-75 years",
      "category": "demographic",
      "data_points_needed": [{"name": "age", "type": "numeric"}],
      "confidence": 0.98
    }
  ],
  "extraction_confidence": 0.92,
  "extraction_method": "pymupdf",
  "page_count": 42,
  "warnings": []
}
```

### POST /api/screen-patient
Evaluate a patient against trial criteria.

**Request:**
```json
{
  "patient_summary": {
    "patient_id": "PT-00123",
    "age": 55,
    "diagnoses": ["Type 2 Diabetes"],
    "lab_values": {"HbA1c": {"value": 7.2, "unit": "%"}}
  },
  "criteria": [
    {"criterion_id": "I1", "type": "inclusion", "description": "Age 18-75"}
  ]
}
```

**Response:**
```json
{
  "screening_id": "SCR-20240324-XXXXXX",
  "overall_status": "likely_eligible",
  "assessments": [
    {
      "criterion_id": "I1",
      "status": "meets",
      "confidence": "high",
      "reasoning": "Patient is 55 years old, within 18-75 range.",
      "evidence_cited": ["Age: 55"]
    }
  ],
  "missing_data_summary": [],
  "follow_up_questions": []
}
```

### POST /api/export-report
Generate a PDF report.

**Request:**
```json
{
  "screening_result": { /* ScreeningResult */ },
  "patient_summary": { /* PatientSummary */ },
  "trial_info": {"trial_name": "LANDMARK-2"}
}
```

**Response:**
```
HTTP/1.1 200 OK
Content-Type: application/pdf
Content-Disposition: attachment; filename=TrialMatch_Report_SCR-20240324-XXXXXX.pdf
```

---

## Demo Scenarios

### Demo 1: Type 2 Diabetes Trial
- **Protocol**: `demo/protocols/diabetes_protocol_summary.md`
- **Patient**: `demo/patients/diabetes_patient.json`
- **Expected Result**: Likely Eligible (meets all criteria)

### Demo 2: Heart Failure Trial
- **Protocol**: `demo/protocols/cardiology_protocol_summary.md`
- **Patient**: `demo/patients/cardiology_patient.json`

### Demo 3: Breast Cancer Trial
- **Protocol**: `demo/protocols/oncology_protocol_summary.md`
- **Patient**: `demo/patients/oncology_patient.json`

---

## Data Flow: Two-Stage LLM Pipeline

### Stage 1: Criteria Extraction
1. User uploads protocol PDF
2. Backend parses PDF (PyMuPDF → Tesseract OCR if scanned)
3. Claude analyzes text → Returns structured criteria as JSON
4. Criteria are assigned IDs (I1, I2... E1, E2...)
5. User can edit/add/remove criteria
6. Results cached for same protocol

### Stage 2: Patient Screening
1. User inputs de-identified patient data
2. Claude evaluates each criterion individually
3. Per-criterion assessment: MEETS / DOES_NOT_MEET / INSUFFICIENT_DATA
4. Overall status calculated: LIKELY_ELIGIBLE / LIKELY_INELIGIBLE / NEEDS_REVIEW
5. Missing data and follow-up questions aggregated
6. Report generated (optional PDF download)

---

## Error Handling

### Common Issues

**PDF Upload Fails**
- ✓ Invalid file type (not PDF) → Error message shown
- ✓ File too large (>50 MB) → Rejected with size info
- ✓ Corrupted PDF → Detected and rejected
- ✓ Scanned PDF → Falls back to OCR

**Extraction Fails**
- ✓ Protocol text too short → Error: no criteria found
- ✓ API timeout → Retries with exponential backoff (max 3 attempts)
- ✓ Malformed LLM response → Structured retry with stricter prompt

**Screening Fails**
- ✓ Missing patient data → INSUFFICIENT_DATA status (conservative)
- ✓ Invalid patient ID → Validation error
- ✓ No criteria loaded → Navigation guard prevents submission

---

## Testing

```bash
# Backend tests
cd backend
pytest tests/ -v --cov=app

# Frontend tests (when added)
cd frontend
npm test
```

---

## Deployment

### Railway (Recommended for Backend)
```bash
# 1. Connect GitHub repo to Railway
# 2. Set environment variables in Railway dashboard:
#    - ANTHROPIC_API_KEY
#    - ALLOWED_ORIGINS
#    - etc.
# 3. Deploy via Git push to main branch
```

### Vercel (Frontend)
```bash
# 1. Connect GitHub repo to Vercel
# 2. Set environment:
#    - VITE_API_URL = https://backend-api.railway.app
# 3. Deploy via Git push
```

---

## Important Disclaimers

⚠️ **This tool is for clinical decision support only.** A qualified healthcare professional must:
- Review all extracted criteria against the original protocol
- Validate all screening assessments
- Make final enrollment decisions
- Document clinical reasoning

⚠️ **De-Identification is Required.** Do not enter:
- Patient names, dates of birth, medical record numbers
- Social security numbers or other identifiers
- Specific facility information that could identify patient

⚠️ **No Data Persistence.** Session data is cleared when:
- Browser window is closed
- User navigates away from the app
- 24 hours of inactivity (server-side)

---

## Architecture Decisions

**Why Two-Stage LLM Pipeline?**
- Stage 1 (Extraction): One-time per protocol, heavily cached
- Stage 2 (Screening): Per-patient, individual criterion evaluation
- Reduces API calls and costs vs. monolithic evaluation

**Why Conservative INSUFFICIENT_DATA?**
- Bias toward "missing data" rather than assumptions
- Clinicians must review and clarify borderline cases
- Prevents false negatives due to incomplete data

**Why No Patient Data Persistence?**
- Privacy-first design: no database of patient screening histories
- HIPAA compliance: no persistent PHI storage
- Simpler infrastructure: no auth/access control needed

**Why React + Tailwind + Vite?**
- Fast development experience
- Small bundle size (~250KB gzipped)
- Easy deployment to Vercel
- No complex backend dependencies

---

## Contributing

Contributions welcome! Areas for enhancement:
- [ ] Additional LLM models (OpenAI, etc.)
- [ ] Protocol PDF previewer in UI
- [ ] Advanced patient data parsing (free-text)
- [ ] Integration with EHR systems
- [ ] Multi-language support
- [ ] Audit logging for compliance

---

## License

MIT License - See LICENSE file for details.

---

## Support

- **Issues**: GitHub Issues
- **Documentation**: GitHub Wiki (placeholder)
- **Questions**: Discussions (TBD)

---

## Acknowledgments

- Built with [Anthropic Claude](https://claude.ai)
- Icons from [Heroicons](https://heroicons.com)
- UI components from [Tailwind CSS](https://tailwindcss.com)

---

**Version**: 1.0.0
**Last Updated**: March 2024
**Status**: Production Ready
