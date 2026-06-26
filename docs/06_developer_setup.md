# Developer Setup Guide
## TrialMatch AI — Clinical Trial Eligibility Screener

**Document Version:** 1.0
**Last Updated:** 2026-03-24
**Status:** Final - MVP v1.0
**Audience:** Backend engineers, frontend engineers, QA, DevOps

---

## Prerequisites

### System Requirements

**Operating System:**
- macOS 12+ (Intel or Apple Silicon)
- Ubuntu 20.04 LTS or later
- Windows 10/11 with WSL2

**Hardware:**
- Disk space: 10 GB minimum (for code, dependencies, PDFs)
- RAM: 8 GB minimum (4 GB for development, 4 GB for background processes)
- Network: Stable internet connection (required for API calls)

### Required Software

**General:**
- Git (v2.30+): `git --version`
- Docker (optional, for containerized backend): `docker --version`

**Backend:**
- Python 3.9 or higher: `python --version` or `python3 --version`
- pip (package manager): `pip --version`
- Virtual environment support (built into Python 3.9+)

**Frontend:**
- Node.js 18+ (LTS): `node --version`
- npm 9+ (included with Node.js): `npm --version`

**Optional Tools:**
- VS Code (recommended editor)
- Postman or Insomnia (for API testing)
- Claude (for prompt development/testing)

### API Keys and Secrets

You will need:

1. **Anthropic API Key**
   - Go to https://console.anthropic.com/
   - Create/copy your API key
   - Keep this secret; do not commit to Git
   - Free tier: $5 credit; pay-as-you-go after

2. **AWS Credentials** (for backend only)
   - AWS Access Key ID
   - AWS Secret Access Key
   - For development, typically local AWS CLI configuration

3. **GitHub Personal Access Token** (optional, for CI/CD)
   - Used for deploying to Vercel/Railway

---

## Project Structure

```
trialmatch-ai/
├── frontend/                     # React app (Vite)
│   ├── src/
│   │   ├── components/           # React components
│   │   │   ├── ProtocolUpload.jsx
│   │   │   ├── CriteriaReview.jsx
│   │   │   ├── PatientInput.jsx
│   │   │   ├── ScreeningResults.jsx
│   │   │   └── ReportExport.jsx
│   │   ├── pages/                # Page-level components
│   │   │   ├── Home.jsx
│   │   │   ├── Extract.jsx
│   │   │   ├── Screen.jsx
│   │   │   └── Report.jsx
│   │   ├── context/              # React Context
│   │   │   └── ScreeningContext.jsx
│   │   ├── utils/                # Utility functions
│   │   │   ├── api.js            # API client
│   │   │   └── validators.js
│   │   ├── App.jsx               # Main component
│   │   ├── main.jsx              # Entry point
│   │   └── index.css             # Global styles
│   ├── package.json
│   ├── vite.config.js
│   ├── .env.example              # Template env file
│   └── .gitignore
│
├── backend/                      # FastAPI (Python)
│   ├── app/
│   │   ├── main.py               # FastAPI app setup
│   │   ├── routers/              # API endpoints
│   │   │   ├── __init__.py
│   │   │   ├── extract.py        # POST /api/extract-criteria
│   │   │   ├── screen.py         # POST /api/screen-patient
│   │   │   ├── report.py         # POST /api/export-report
│   │   │   └── health.py         # GET /health
│   │   ├── services/             # Business logic
│   │   │   ├── __init__.py
│   │   │   ├── pdf_parser.py
│   │   │   ├── criteria_extractor.py
│   │   │   ├── patient_screener.py
│   │   │   └── report_generator.py
│   │   ├── prompts/              # LLM prompts
│   │   │   ├── __init__.py
│   │   │   ├── extraction.py
│   │   │   └── screening.py
│   │   ├── models/               # Pydantic models
│   │   │   ├── __init__.py
│   │   │   ├── criteria.py
│   │   │   └── screening.py
│   │   ├── config.py             # Configuration
│   │   └── dependencies.py       # Dependency injection
│   ├── tests/                    # Test suite
│   │   ├── __init__.py
│   │   ├── conftest.py           # Pytest fixtures
│   │   ├── test_pdf_parser.py
│   │   ├── test_criteria_extractor.py
│   │   ├── test_patient_screener.py
│   │   ├── test_report_generator.py
│   │   └── fixtures/             # Test data
│   │       ├── protocols/
│   │       │   ├── diabetes_protocol.pdf
│   │       │   ├── cardiology_protocol.pdf
│   │       │   └── oncology_protocol.pdf
│   │       └── patients/
│   │           ├── diabetes_patients.json
│   │           └── ...
│   ├── requirements.txt          # Python dependencies
│   ├── requirements-dev.txt      # Dev dependencies (pytest, black, etc.)
│   ├── .env.example              # Template env file
│   ├── .gitignore
│   ├── Dockerfile                # Docker image
│   └── docker-compose.yml        # Local Docker setup
│
├── docs/                         # Documentation
│   ├── 01_system_requirements.md
│   ├── 02_architecture.md
│   ├── 03_api_reference.md
│   ├── 04_prompt_engineering.md
│   ├── 05_data_models.md
│   ├── 06_developer_setup.md
│   ├── 07_user_guide.md
│   ├── 08_compliance_notes.md
│   └── 09_testing_strategy.md
│
├── demo/                         # Demo/test data
│   ├── protocols/                # Sample protocols
│   │   ├── README.md
│   │   ├── diabetes_study_phase2.pdf
│   │   ├── cardiology_hf_study.pdf
│   │   └── oncology_breast_cancer.pdf
│   └── patients/                 # Sample patient data
│       ├── diabetes_sample.json
│       └── cardiology_sample.json
│
├── .github/                      # GitHub Actions
│   └── workflows/
│       └── deploy.yml            # CI/CD pipeline
│
├── README.md                     # Project overview
├── LICENSE                       # License (MIT or similar)
├── .gitignore                    # Git ignore rules
└── CHANGELOG.md                  # Version history
```

---

## Backend Setup

### 1. Clone Repository

```bash
git clone https://github.com/your-org/trialmatch-ai.git
cd trialmatch-ai/backend
```

### 2. Create Virtual Environment

```bash
# Create venv
python3 -m venv venv

# Activate venv
# On macOS/Linux:
source venv/bin/activate

# On Windows (PowerShell):
.\venv\Scripts\Activate.ps1

# On Windows (CMD):
venv\Scripts\activate.bat

# Verify activation (should show (venv) in prompt)
which python  # macOS/Linux
where python  # Windows
```

### 3. Install Dependencies

```bash
# Upgrade pip
pip install --upgrade pip

# Install base dependencies
pip install -r requirements.txt

# Install dev dependencies (for testing, linting, etc.)
pip install -r requirements-dev.txt
```

**requirements.txt contents:**
```
fastapi==0.104.0
uvicorn==0.24.0
pydantic==2.4.0
python-multipart==0.0.6
pymupdf==1.23.0
pytesseract==0.3.10
anthropic==0.7.0
boto3==1.28.0
python-dotenv==1.0.0
```

**requirements-dev.txt contents:**
```
pytest==7.4.0
pytest-asyncio==0.21.0
pytest-cov==4.1.0
black==23.9.0
flake8==6.1.0
mypy==1.5.0
httpx==0.24.0
```

### 4. Set Environment Variables

```bash
# Copy template file
cp .env.example .env

# Edit .env with your actual values
# Required variables:
# ANTHROPIC_API_KEY=sk-ant-...
# AWS_REGION=us-east-1
# AWS_ACCESS_KEY_ID=...
# AWS_SECRET_ACCESS_KEY=...
# S3_BUCKET=trialmatch-pdfs-dev
# ENVIRONMENT=development  # or staging, production
```

**.env.example template:**
```bash
# Anthropic API
ANTHROPIC_API_KEY=your-key-here

# AWS Configuration
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
S3_BUCKET=trialmatch-pdfs-dev

# Application
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=DEBUG
```

### 5. Install System Dependencies (For OCR)

**macOS:**
```bash
brew install tesseract-ocr
```

**Ubuntu/Debian:**
```bash
apt-get update
apt-get install -y tesseract-ocr
```

**Windows:**
Download installer from: https://github.com/UB-Mannheim/tesseract/wiki

### 6. Run Backend Dev Server

```bash
# Option 1: Using uvicorn directly
uvicorn app.main:app --reload --port 8000 --host 0.0.0.0

# Option 2: Using Python -m
python -m uvicorn app.main:app --reload

# Output should show:
# INFO:     Uvicorn running on http://127.0.0.1:8000
# INFO:     Application startup complete
```

**Check health:**
```bash
curl http://localhost:8000/health
# Expected response: {"status":"ok","version":"1.0.0",...}
```

---

## Frontend Setup

### 1. Clone Repository (if not already done)

```bash
git clone https://github.com/your-org/trialmatch-ai.git
cd trialmatch-ai/frontend
```

### 2. Install Dependencies

```bash
npm install
# or: npm ci (for exact versions)
```

### 3. Set Environment Variables

```bash
# Copy template
cp .env.example .env.local

# Edit .env.local
# Required variables:
# VITE_API_URL=http://localhost:8000/api
# VITE_APP_NAME=TrialMatch AI
```

**.env.example template:**
```bash
# API
VITE_API_URL=http://localhost:8000/api

# Application
VITE_APP_NAME=TrialMatch AI
VITE_ENVIRONMENT=development
```

### 4. Run Frontend Dev Server

```bash
# Start Vite dev server
npm run dev

# Output should show:
# > vite
#
# VITE v4.x.x  ready in 234 ms
# ➜  Local:   http://localhost:5173/
# ➜  press h to show help
```

**Access Frontend:**
- http://localhost:5173/

### 5. Frontend Build (for production)

```bash
npm run build
# Creates optimized production build in dist/
```

---

## Running Tests

### Backend Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_pdf_parser.py

# Run specific test function
pytest tests/test_pdf_parser.py::test_extract_text_from_pdf

# Run with verbose output
pytest -v

# Run in watch mode (auto-rerun on changes)
pytest-watch
```

### Frontend Tests

```bash
# Run all tests
npm run test

# Run with coverage
npm run test:coverage

# Run in watch mode
npm run test:watch
```

---

## Code Quality and Linting

### Backend

```bash
# Format code with Black
black app/ tests/

# Lint with Flake8
flake8 app/ tests/

# Type checking with mypy
mypy app/

# All three (pre-commit style)
black app/ && flake8 app/ && mypy app/
```

### Frontend

```bash
# Lint JavaScript/React
npm run lint

# Fix linting issues
npm run lint:fix

# Format code with Prettier
npm run format
```

### Pre-Commit Hook (Optional)

```bash
# Install pre-commit hooks
pip install pre-commit
pre-commit install

# This will run linting/formatting before each commit
```

---

## Development Workflow

### Creating a New Feature

**1. Create Branch**
```bash
git checkout -b feature/short-description
# e.g., feature/add-compound-logic-handling
```

**2. Make Changes**
- Backend: Update services, models, routers
- Frontend: Update components, context
- Tests: Add corresponding tests

**3. Run Tests Locally**
```bash
# Backend
pytest --cov

# Frontend
npm run test

# Both
cd backend && pytest && cd ../frontend && npm run test
```

**4. Lint and Format**
```bash
# Backend
black app/ && flake8 app/ && mypy app/

# Frontend
npm run lint:fix
```

**5. Commit**
```bash
git add .
git commit -m "feat: add compound logic handling to screening"
# Use conventional commits: feat:, fix:, docs:, test:, refactor:, etc.
```

**6. Push and Create PR**
```bash
git push origin feature/short-description
# Create Pull Request on GitHub
```

**7. PR Review and Merge**
- Wait for CI/CD to pass
- Request code review
- Address review feedback
- Merge to main

---

## Adding a New Demo Protocol

### Step 1: Obtain Protocol PDF

Get a de-identified clinical trial protocol PDF (public or demo).

### Step 2: Create Protocol Fixture

```bash
# Place PDF in demo/protocols/
cp my_protocol.pdf demo/protocols/my_protocol.pdf

# Create metadata file
cat > demo/protocols/my_protocol.json << 'EOF'
{
  "nct_number": "NCT12345678",
  "title": "My Protocol Title",
  "sponsor": "My Organization",
  "therapeutic_area": "oncology",  # or diabetes, cardiology
  "estimated_enrollment": 100,
  "phase": "Phase II"
}
EOF
```

### Step 3: Extract Criteria Manually

Use TrialMatch UI or LLM to extract criteria:

```bash
# Option 1: Use running app
# 1. Start backend and frontend
# 2. Upload PDF in UI
# 3. Copy extracted criteria to demo/protocols/my_protocol_criteria.json

# Option 2: Call API directly
curl -X POST http://localhost:8000/api/extract-criteria \
  -F "file=@demo/protocols/my_protocol.pdf" \
  > demo/protocols/my_protocol_extraction.json
```

### Step 4: Create Sample Patient Cases

```bash
cat > demo/patients/my_protocol_patients.json << 'EOF'
[
  {
    "case_id": "case-001",
    "description": "Eligible patient",
    "patient_summary": "55-year-old female with Type 2 Diabetes...",
    "expected_status": "ELIGIBLE",
    "explanation": "Meets all inclusion criteria, no exclusions triggered"
  },
  {
    "case_id": "case-002",
    "description": "Ineligible - high HbA1c",
    "patient_summary": "48-year-old male with Type 2 Diabetes, HbA1c 9.2%...",
    "expected_status": "NOT_ELIGIBLE",
    "explanation": "HbA1c exceeds upper limit of 8.5%"
  },
  {
    "case_id": "case-003",
    "description": "Requires review - missing lab data",
    "patient_summary": "62-year-old female, Type 2 Diabetes, labs pending...",
    "expected_status": "REQUIRES_REVIEW",
    "explanation": "Cannot determine eligibility without recent HbA1c"
  }
]
EOF
```

### Step 5: Update Demo README

```bash
# Edit demo/protocols/README.md
cat >> demo/protocols/README.md << 'EOF'

## My Protocol

- **File:** my_protocol.pdf
- **Therapeutic Area:** Oncology
- **Phase:** Phase II
- **NCT Number:** NCT12345678
- **Enrollment:** 100 patients
- **Sample Cases:** See ../patients/my_protocol_patients.json

### Notes
- Protocol covers inclusion criteria for adults aged 18-75
- Key exclusion: Prior chemotherapy within 2 years
EOF
```

### Step 6: Add to Test Suite

```bash
# Edit tests/fixtures/conftest.py
@pytest.fixture
def my_protocol():
    pdf_path = "demo/protocols/my_protocol.pdf"
    criteria = json.load(open("demo/protocols/my_protocol_criteria.json"))
    return {
        "path": pdf_path,
        "expected_criteria_count": 8,
        "criteria": criteria
    }

# Add test
def test_extract_my_protocol(my_protocol):
    criteria = extract_criteria(my_protocol["path"])
    assert len(criteria) == my_protocol["expected_criteria_count"]
```

---

## Common Development Pitfalls

### Pitfall 1: API Key Not Set

**Symptom:** `anthropic.APIError: API key not provided`

**Solution:**
```bash
# Verify .env file has ANTHROPIC_API_KEY
cat .env | grep ANTHROPIC_API_KEY

# Or set directly
export ANTHROPIC_API_KEY=sk-ant-...

# Restart backend
```

### Pitfall 2: Port Already in Use

**Symptom:** `Address already in use`

**Solution:**
```bash
# Find process using port 8000
lsof -i :8000  # macOS/Linux
netstat -ano | findstr :8000  # Windows

# Kill process
kill -9 <PID>  # macOS/Linux
taskkill /PID <PID> /F  # Windows

# Or use different port
uvicorn app.main:app --port 8001
```

### Pitfall 3: Virtual Environment Not Activated

**Symptom:** `Command 'pytest' not found` or wrong Python being used

**Solution:**
```bash
# Check if venv is active (should show (venv) in prompt)
# If not, activate it:
source venv/bin/activate  # macOS/Linux
.\venv\Scripts\activate.ps1  # Windows PowerShell
```

### Pitfall 4: CORS Errors (Frontend → Backend)

**Symptom:** `Access to XMLHttpRequest has been blocked by CORS policy`

**Solution:**
```python
# In backend/app/main.py, verify CORS is configured:
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"]
)
```

### Pitfall 5: Dependency Installation Failed

**Symptom:** `ERROR: Could not find a version that satisfies the requirement...`

**Solution:**
```bash
# Upgrade pip
pip install --upgrade pip

# Try again
pip install -r requirements.txt

# Or install with no cache (if network issue)
pip install --no-cache-dir -r requirements.txt
```

### Pitfall 6: Frontend Can't Connect to Backend

**Symptom:** "Network error" when uploading PDF

**Solution:**
```bash
# Verify backend is running
curl http://localhost:8000/health

# Check frontend .env has correct API URL
cat frontend/.env.local | grep VITE_API_URL

# Verify they match:
# Backend: localhost:8000
# Frontend VITE_API_URL: http://localhost:8000/api
```

### Pitfall 7: Tests Fail Due to Missing Fixtures

**Symptom:** `FileNotFoundError: demo/protocols/diabetes_protocol.pdf`

**Solution:**
```bash
# Ensure demo files exist
ls -la demo/protocols/
ls -la demo/patients/

# If missing, check git (may be in .gitignore)
git status demo/

# Download or create demo files
# See "Adding a New Demo Protocol" section above
```

---

## Useful Commands Reference

### Backend

```bash
# Start server with auto-reload
uvicorn app.main:app --reload

# Start with specific host/port
uvicorn app.main:app --host 0.0.0.0 --port 8001

# Run tests
pytest

# Run tests with coverage report
pytest --cov=app --cov-report=html

# Format code
black app/ tests/

# Lint
flake8 app/ tests/

# Type check
mypy app/

# Check dependencies for security issues
pip install safety && safety check
```

### Frontend

```bash
# Start dev server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview

# Run tests
npm run test

# Lint
npm run lint

# Fix linting issues
npm run lint:fix

# Format code
npm run format
```

### Git

```bash
# Check branch status
git status

# Pull latest changes
git pull origin main

# Create and switch to new branch
git checkout -b feature/my-feature

# Commit changes
git add .
git commit -m "feat: description of changes"

# Push to remote
git push origin feature/my-feature

# Squash commits before merge
git rebase -i main

# View commit history
git log --oneline

# See differences
git diff
```

---

## Deployment Preparation

### Pre-Deployment Checklist

- [ ] All tests passing (`pytest` and `npm run test`)
- [ ] No linting errors (`black`, `flake8`, `npm run lint`)
- [ ] Environment variables configured
- [ ] Database migrations (if applicable)
- [ ] API documentation up-to-date
- [ ] Changelog updated
- [ ] Code review completed
- [ ] No hardcoded secrets in code

### Building for Production

**Backend:**
```bash
# Build Docker image (if using Docker)
docker build -t trialmatch-ai:latest .

# Test locally
docker run -p 8000:8000 trialmatch-ai:latest
```

**Frontend:**
```bash
# Build optimized bundle
npm run build

# Check bundle size
npm run build -- --report

# Test build locally
npm run preview
```

---

## Getting Help

### Resources

- **API Documentation:** Swagger UI at `http://localhost:8000/docs`
- **Discord/Slack:** Team development channel
- **GitHub Issues:** Report bugs and feature requests
- **ADRs:** Architecture Decision Records in `/docs/adr/`

### Debugging Tips

1. **Enable Debug Logging:**
   ```bash
   export LOG_LEVEL=DEBUG
   uvicorn app.main:app --reload
   ```

2. **Use Browser DevTools:**
   - F12 to open DevTools
   - Network tab to inspect API calls
   - Console tab for JavaScript errors

3. **Use PostmanInSomnia for API Testing:**
   - Import API specification from `/docs/03_api_reference.md`
   - Test endpoints individually

4. **Add Breakpoints (Backend):**
   ```python
   import pdb
   pdb.set_trace()  # Breakpoint; use 'c' to continue, 'n' to next line
   ```

5. **Add Console Logs (Frontend):**
   ```javascript
   console.log('Debug info:', variableName);
   console.error('Error message:', error);
   ```

---

## Sign-Off

| Role | Name | Date | Signature |
|------|------|------|-----------|
| DevOps Lead | [Name] | 2026-03-24 | — |
| Backend Lead | [Name] | 2026-03-24 | — |
| Frontend Lead | [Name] | 2026-03-24 | — |

---

**END OF DEVELOPER SETUP GUIDE**
