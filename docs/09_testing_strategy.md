# Testing Strategy
## TrialMatch AI — Clinical Trial Eligibility Screener

**Document Version:** 1.0
**Last Updated:** 2026-03-24
**Status:** Final - MVP v1.0
**Audience:** QA engineers, test automation engineers, product managers

---

## Testing Philosophy

### Core Principles

1. **Quality Over Speed:** Better to slow down and catch bugs than to ship broken features
2. **Automation First:** Automated tests catch regressions; manual tests find surprises
3. **Clinical Rigor:** Test against real-world clinical scenarios, not just happy paths
4. **Transparency in Testing:** Show what we tested, how, and results to stakeholders
5. **Continuous Evaluation:** LLM quality is evaluated continuously; prompt changes require re-evaluation

### Testing Scope by Layer

| Layer | Test Type | Coverage Target |
|---|---|---|
| **Unit (PDF Parser, Extractors)** | Automated | >90% code coverage |
| **Integration (API endpoints)** | Automated + Manual | Critical paths 100%, edge cases 80%+ |
| **LLM Evaluation (Extraction, Screening)** | Automated eval dataset | Accuracy >90%, Concordance >85% |
| **End-to-End (Full workflow)** | Manual | All 3 therapeutic areas (diabetes, cardiology, oncology) |
| **Security** | Automated + Manual | HTTPS, CORS, PII detection, session management |
| **Performance** | Automated | Extraction <60s, Screening <90s, Report <10s |
| **Usability** | Manual + User testing | Task completion rate >90%, task time <10 min for new user |

---

## Unit Testing Strategy

### Backend Unit Tests

**Test Files:**
- `tests/test_pdf_parser.py` — Text extraction, OCR handling
- `tests/test_criteria_extractor.py` — JSON parsing, criteria validation
- `tests/test_patient_screener.py` — Assessment logic, confidence calibration
- `tests/test_report_generator.py` — PDF generation, table formatting

**Example: PDF Parser Tests**

```python
# tests/test_pdf_parser.py
import pytest
from app.services.pdf_parser import PDFParser

class TestPDFTextExtraction:
    """Test text extraction from PDFs."""

    def test_extract_text_from_searchable_pdf(self):
        """Extract text from searchable PDF."""
        pdf_path = "tests/fixtures/protocols/diabetes_protocol.pdf"
        parser = PDFParser()
        text, confidence = parser.extract_text_from_pdf(pdf_path)

        assert len(text) > 1000  # Substantial text extracted
        assert confidence > 0.95  # High confidence for searchable PDF
        assert "inclusion" in text.lower()  # Key word found

    def test_extract_text_from_scanned_pdf(self):
        """Extract text from scanned PDF with OCR."""
        pdf_path = "tests/fixtures/protocols/scanned_protocol.pdf"
        parser = PDFParser()
        text, confidence = parser.extract_text_from_pdf(pdf_path)

        assert len(text) > 500  # Text extracted despite OCR
        assert 0.65 <= confidence <= 0.95  # OCR confidence range
        assert "HbA1c" in text or "age" in text.lower()

    def test_extract_from_corrupted_pdf(self):
        """Handle corrupted PDF gracefully."""
        pdf_path = "tests/fixtures/protocols/corrupted.pdf"
        parser = PDFParser()

        with pytest.raises(ValueError, match="PDF appears corrupted"):
            parser.extract_text_from_pdf(pdf_path)

    def test_pdf_size_validation(self):
        """Reject PDFs larger than 50 MB."""
        parser = PDFParser()

        # Simulate large file
        with pytest.raises(ValueError, match="exceeds 50 MB"):
            parser.validate_pdf_size(51_000_000)

    def test_extract_preserves_formatting(self):
        """Preserve important formatting in extraction."""
        text = """
        INCLUSION CRITERIA:
        1. Age 18-75 years
        2. Type 2 Diabetes Mellitus
        """
        parser = PDFParser()

        # Verify numbers and structure preserved
        assert "1." in text
        assert "18-75" in text
```

**Example: Criteria Extractor Tests**

```python
# tests/test_criteria_extractor.py
from app.services.criteria_extractor import CriteriaExtractor
from app.models.criteria import CriterionModel

class TestCriteriaExtraction:
    """Test LLM-based criteria extraction."""

    def test_extract_simple_criteria(self):
        """Extract basic inclusion/exclusion criteria."""
        protocol_text = """
        INCLUSION CRITERIA:
        1. Age 18-75 years
        2. Type 2 Diabetes Mellitus

        EXCLUSION CRITERIA:
        1. Type 1 Diabetes
        2. Pregnant women
        """
        extractor = CriteriaExtractor()
        criteria = extractor.extract_criteria(protocol_text)

        assert len(criteria) >= 4  # At least 4 criteria
        assert sum(1 for c in criteria if c.type == "inclusion") >= 2
        assert sum(1 for c in criteria if c.type == "exclusion") >= 2

    def test_extract_compound_criteria(self):
        """Extract criteria with AND/OR logic."""
        protocol_text = """
        INCLUSION: Age 50-75 AND eGFR ≥60
        EXCLUSION: Prior chemotherapy within 2 years OR active cancer
        """
        extractor = CriteriaExtractor()
        criteria = extractor.extract_criteria(protocol_text)

        # Find compound criteria
        age_eGFR = next(c for c in criteria if "eGFR" in c.description)
        assert "AND" in age_eGFR.logic

        chemo_cancer = next(c for c in criteria if "chemotherapy" in c.description)
        assert "OR" in chemo_cancer.logic

    def test_extract_maintains_criterion_ids(self):
        """Criterion IDs sequentially numbered (I1, I2, E1, E2)."""
        extractor = CriteriaExtractor()
        criteria = [
            CriterionModel(criterion_id="I1", type="inclusion", ...),
            CriterionModel(criterion_id="I2", type="inclusion", ...),
            CriterionModel(criterion_id="E1", type="exclusion", ...),
        ]

        # No I3 before E1, no E0 before I1
        ids = [c.criterion_id for c in criteria]
        assert ids == sorted(ids, key=lambda x: (x[0], int(x[1:])))

    def test_validation_rejects_invalid_criteria(self):
        """Reject criteria with invalid structure."""
        invalid_criterion = {
            "criterion_id": "X1",  # Invalid prefix
            "type": "inclusion",
            "description": "Test",
            "category": "other",
            "data_points_needed": [],
        }

        # Should raise validation error
        with pytest.raises(ValueError):
            CriterionModel(**invalid_criterion)
```

**Example: Patient Screener Tests**

```python
# tests/test_patient_screener.py
from app.services.patient_screener import PatientScreener
from app.models.criteria import CriterionModel
from app.models.screening import CriterionAssessment

class TestPatientScreening:
    """Test LLM-based patient screening."""

    def test_screen_patient_basic(self):
        """Basic screening of patient against criteria."""
        criteria = [
            CriterionModel(
                criterion_id="I1",
                type="inclusion",
                description="Age 18-75",
                category="demographics",
                data_points_needed=["age"],
                logic="18 ≤ age ≤ 75"
            )
        ]
        patient_summary = "55-year-old female with Type 2 Diabetes."

        screener = PatientScreener()
        result = screener.screen_patient(criteria, patient_summary)

        # Should assess the one criterion
        assert len(result.criteria_assessments) == 1
        assessment = result.criteria_assessments[0]

        assert assessment.criterion_id == "I1"
        assert assessment.status == "MEETS"
        assert assessment.confidence == "high"
        assert "55" in assessment.reasoning

    def test_screen_patient_insufficient_data(self):
        """Screening returns INSUFFICIENT_DATA when info missing."""
        criteria = [
            CriterionModel(
                criterion_id="I1",
                type="inclusion",
                description="HbA1c <8%",
                category="lab_values",
                data_points_needed=["HbA1c"],
                logic="HbA1c < 8"
            )
        ]
        patient_summary = "Patient with Type 2 Diabetes."  # No HbA1c provided

        screener = PatientScreener()
        result = screener.screen_patient(criteria, patient_summary)

        assessment = result.criteria_assessments[0]
        assert assessment.status == "INSUFFICIENT_DATA"
        assert assessment.missing_data is not None
        assert "HbA1c" in assessment.missing_data[0]

    def test_confidence_calibration(self):
        """Confidence calibrated based on criterion clarity + data completeness."""
        criteria = [
            CriterionModel(
                criterion_id="I1",
                type="inclusion",
                description="Age 18-75 years",  # Clear criterion
                category="demographics",
                data_points_needed=["age"],
                logic="18 ≤ age ≤ 75"
            ),
            CriterionModel(
                criterion_id="I2",
                type="inclusion",
                description="Good renal function",  # Ambiguous criterion
                category="lab_values",
                data_points_needed=["eGFR"],
                logic=None
            )
        ]
        patient_summary = "Age 55. eGFR 72."

        screener = PatientScreener()
        result = screener.screen_patient(criteria, patient_summary)

        # I1: Clear criterion + complete data = HIGH confidence
        assert result.criteria_assessments[0].confidence == "high"

        # I2: Ambiguous criterion + complete data = MEDIUM confidence
        assert result.criteria_assessments[1].confidence in ["medium", "low"]

    def test_overall_eligibility_calculation(self):
        """Overall status calculated correctly."""
        criteria = [
            CriterionModel(criterion_id="I1", type="inclusion", ...),  # MEETS
            CriterionModel(criterion_id="I2", type="inclusion", ...),  # DOES_NOT_MEET
            CriterionModel(criterion_id="E1", type="exclusion", ...),  # MEETS (exclusion not triggered)
        ]

        # Expected: NOT_ELIGIBLE (because I2 does not meet)
        screener = PatientScreener()
        result = screener.screen_patient(criteria, patient_summary)

        assert result.overall_status == "NOT_ELIGIBLE"
```

**Unit Test Execution:**

```bash
# Run all unit tests
pytest tests/

# Run specific test file
pytest tests/test_criteria_extractor.py

# Run with coverage report
pytest tests/ --cov=app --cov-report=html

# Expected: >90% code coverage
```

---

## Integration Testing Strategy

### API Integration Tests

**Test Files:**
- `tests/test_api_extract.py` — POST /api/extract-criteria endpoint
- `tests/test_api_screen.py` — POST /api/screen-patient endpoint
- `tests/test_api_report.py` — POST /api/export-report endpoint
- `tests/test_api_health.py` — GET /health endpoint

**Example: Extraction Endpoint Test**

```python
# tests/test_api_extract.py
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

class TestExtractionEndpoint:
    """Test POST /api/extract-criteria endpoint."""

    def test_extract_valid_pdf(self):
        """Upload valid PDF and receive criteria."""
        with open("tests/fixtures/protocols/diabetes_protocol.pdf", "rb") as f:
            response = client.post(
                "/api/extract-criteria",
                files={"file": f}
            )

        assert response.status_code == 200
        data = response.json()

        assert "protocol" in data
        assert "criteria" in data
        assert len(data["criteria"]) > 0

        # Validate response schema
        for criterion in data["criteria"]:
            assert "criterion_id" in criterion
            assert "type" in criterion
            assert "description" in criterion
            assert "category" in criterion

    def test_extract_file_too_large(self):
        """Reject PDF larger than 50 MB."""
        # Simulate large file (can't actually create 50MB in test)
        # Using mock instead
        response = client.post(
            "/api/extract-criteria",
            files={"file": (
                "large.pdf",
                b"x" * (51 * 1024 * 1024)  # 51 MB
            )}
        )

        assert response.status_code == 413
        assert "exceeds" in response.json()["error"]

    def test_extract_wrong_file_type(self):
        """Reject non-PDF files."""
        response = client.post(
            "/api/extract-criteria",
            files={"file": ("document.txt", b"Not a PDF")}
        )

        assert response.status_code == 415
        assert "PDF" in response.json()["error"]

    def test_extract_sets_session_cookie(self):
        """Response includes session cookie."""
        response = client.post(
            "/api/extract-criteria",
            files={"file": open("tests/fixtures/protocols/diabetes_protocol.pdf", "rb")}
        )

        assert response.status_code == 200
        assert "session_id" in response.cookies
        cookie = response.cookies["session_id"]
        assert "httponly" in str(cookie)  # HTTP-only flag
        assert "secure" in str(cookie)    # Secure flag (in production)
```

---

## LLM Evaluation Strategy

### Gold Standard Datasets

**Diabetes Protocol (Level 1 - Simple):**
- Protocol: 20-page Type 2 Diabetes trial (Phase II)
- Criteria: ~8 criteria (demographics, diagnosis, lab values)
- Complexity: Straightforward inclusion/exclusion

**Cardiology Protocol (Level 2 - Moderate):**
- Protocol: 35-page Heart Failure trial
- Criteria: ~12 criteria (compound logic, temporal conditions)
- Complexity: AND/OR logic, LVEF thresholds, prior medications

**Oncology Protocol (Level 3 - Complex):**
- Protocol: 50-page Breast Cancer trial
- Criteria: ~15 criteria (prior therapies, performance status, imaging)
- Complexity: Compound criteria, clinical judgment calls

**Patient Test Cases (per protocol):**
- 10 cases per protocol = 30 total cases
- Mix: 5 eligible, 5 ineligible, 5 borderline/requires-review
- Cover: Typical patient, edge cases (young/old, borderline labs), missing data

### Extraction Evaluation Metrics

**Metric 1: Precision**
```
Precision = (Correctly extracted criteria) / (Total criteria extracted)
            = (Gold standard criteria found in output) / (Total output criteria)

Example: If we extract 40 criteria and 38 match gold standard:
Precision = 38/40 = 95%

Target: >90%
```

**Metric 2: Recall**
```
Recall = (Correctly extracted criteria) / (Gold standard criteria count)
       = (Criteria found in output) / (Total gold standard criteria)

Example: If gold standard has 40 criteria and we extract 38:
Recall = 38/40 = 95%

Target: >90%
```

**Metric 3: F1 Score**
```
F1 = 2 × (Precision × Recall) / (Precision + Recall)
   = Harmonic mean of precision and recall

Target: >90%
```

**How to Calculate (Example Script):**

```python
# evaluation/eval_extraction.py
def evaluate_extraction():
    test_protocols = [
        ("Diabetes", "tests/fixtures/diabetes_gold.json"),
        ("Cardiology", "tests/fixtures/cardiology_gold.json"),
        ("Oncology", "tests/fixtures/oncology_gold.json"),
    ]

    for protocol_name, gold_file in test_protocols:
        # Load gold standard
        with open(gold_file) as f:
            gold_criteria = json.load(f)

        # Extract using TrialMatch
        extracted_criteria = extract_criteria(protocol_pdf_path)

        # Compare
        correct = 0
        for gold in gold_criteria:
            for extracted in extracted_criteria:
                if match_criteria(gold, extracted):
                    correct += 1
                    break

        precision = correct / len(extracted_criteria)
        recall = correct / len(gold_criteria)
        f1 = 2 * (precision * recall) / (precision + recall)

        print(f"{protocol_name}: Precision={precision:.2%}, Recall={recall:.2%}, F1={f1:.2%}")

        if f1 < 0.90:
            print(f"⚠️  BELOW TARGET for {protocol_name}")
            # Log failures for analysis
```

---

### Screening Evaluation Metrics

**Metric 1: Concordance**
```
Concordance = (LLM result matches expert decision) / (Total cases)
            = (Cases where overall_status matches) / (30 cases)

Example: 26/30 cases match = 87% concordance

Target: >85%
```

**Metric 2: False Negative Rate (Clinical Priority)**
```
False Negative Rate = (LLM says ELIGIBLE but expert says NOT_ELIGIBLE) /
                      (Expert NOT_ELIGIBLE cases)

Example: 1 false negative out of 10 expert NOT_ELIGIBLE = 10% FNR

Target: <5% (Clinical safety critical: false negatives = wrong enrollment)
```

**Metric 3: False Positive Rate**
```
False Positive Rate = (LLM says NOT_ELIGIBLE but expert says ELIGIBLE) /
                     (Expert ELIGIBLE cases)

Example: 0 false positives out of 15 expert ELIGIBLE = 0% FPR

Target: Lower FPR better (but less critical than FNR)
```

**Metric 4: Confidence Calibration**
```
Calibration = (High confidence assessments matching expert) /
              (Total high confidence assessments)

Example: 15/16 high-confidence assessments correct = 94% calibration

Target: >90% (LLM's confidence should correlate with correctness)
```

**How to Calculate (Example Script):**

```python
# evaluation/eval_screening.py
def evaluate_screening():
    test_suites = [
        ("Diabetes", diabetes_cases),
        ("Cardiology", cardiology_cases),
        ("Oncology", oncology_cases),
    ]

    total_concordant = 0
    total_cases = 0
    false_negatives = 0
    false_positives = 0
    expert_not_eligible = 0
    expert_eligible = 0

    for protocol_name, cases in test_suites:
        for case in cases:
            patient_summary = case["patient_summary"]
            expert_decision = case["expert_decision"]
            criteria = case["criteria"]

            # Screen patient
            llm_result = screen_patient(criteria, patient_summary)
            llm_decision = llm_result["overall_status"]

            total_cases += 1

            # Track results
            if llm_decision == "ELIGIBLE":
                llm_eligible = True
            else:
                llm_eligible = False

            if expert_decision == "ELIGIBLE":
                expert_eligible += 1
            else:
                expert_not_eligible += 1

            if llm_decision == expert_decision:
                total_concordant += 1
            elif llm_eligible and not expert_eligible:
                false_negatives += 1
            elif not llm_eligible and expert_eligible:
                false_positives += 1

    concordance = total_concordant / total_cases
    fnr = false_negatives / expert_not_eligible if expert_not_eligible > 0 else 0
    fpr = false_positives / expert_eligible if expert_eligible > 0 else 0

    print(f"Concordance: {concordance:.2%}")
    print(f"False Negative Rate: {fnr:.2%}")
    print(f"False Positive Rate: {fpr:.2%}")

    if fnr > 0.05:
        print("🚨 FNR EXCEEDS SAFETY THRESHOLD")
        # Log failures for analysis
```

---

## End-to-End Testing (E2E)

### User Workflow Test Cases

**Test Case E2E-001: Complete Happy Path (Eligible Patient)**

```gherkin
Given: Study coordinator has TrialMatch open
When:  1. Upload diabetes_protocol.pdf
       2. Review extracted criteria (8 criteria)
       3. Confirm all criteria correct
       4. Input patient summary: 55-year-old female, T2DM, HbA1c 7.8%, eGFR 85
       5. Screen patient
       6. Review results: Overall ELIGIBLE
       7. Export PDF report

Then:  1. Extraction completes in <15 seconds
       2. All 8 criteria extracted correctly
       3. Screening completes in <10 seconds
       4. All criteria show MEETS
       5. Overall status: ELIGIBLE
       6. PDF downloads successfully
       7. PDF contains all expected sections (title, results, disclaimer)
```

**Test Case E2E-002: Ineligible Patient (High HbA1c)**

```gherkin
Given: Criteria extraction completed (target: HbA1c <8%)
When:  1. Input patient summary: 62-year-old male, T2DM, HbA1c 8.4%
       2. Screen patient
       3. Review results

Then:  1. Screening completes in <10 seconds
       2. Criterion I3 (HbA1c) shows DOES_NOT_MEET
       3. Confidence: HIGH
       4. Reasoning cites: "HbA1c 8.4% exceeds limit of 8.0%"
       5. Overall status: NOT_ELIGIBLE
       6. Primary ineligibility reason shown: "HbA1c"
```

**Test Case E2E-003: Missing Data (No HbA1c)**

```gherkin
Given: Criteria requires HbA1c lab value
When:  1. Input patient summary: 48-year-old female, T2DM, labs pending
       2. Screen patient

Then:  1. Criterion I3 (HbA1c) shows INSUFFICIENT_DATA
       2. Missing data: "HbA1c value (within last 3 months)"
       3. Overall status: REQUIRES_REVIEW
       4. Missing data summary shows data needed
       5. Coordinator can go back and re-enter with updated HbA1c
```

---

## Performance Testing

### Load and Performance Benchmarks

**Target Latencies:**

| Operation | Target | P95 | P99 |
|---|---|---|---|
| Upload PDF (50 MB) | <5s | <8s | <10s |
| Extract criteria | <30s | <40s | <60s |
| Screen patient | <15s | <20s | <30s |
| Export report | <10s | <12s | <15s |
| End-to-end workflow | <90s | <120s | <150s |

**Performance Test Script:**

```python
# tests/test_performance.py
import time
import pytest

class TestPerformance:
    """Performance benchmarks for critical operations."""

    def test_extraction_latency(self, benchmark):
        """Measure extraction time."""
        def extract():
            with open("tests/fixtures/diabetes_protocol.pdf", "rb") as f:
                response = client.post("/api/extract-criteria", files={"file": f})
            return response

        result = benchmark(extract)
        assert result.status_code == 200

    def test_screening_latency(self, benchmark):
        """Measure screening time."""
        criteria = load_test_criteria()
        patient_summary = "55-year-old female, T2DM, HbA1c 8.2%"

        def screen():
            response = client.post(
                "/api/screen-patient",
                json={"criteria": criteria, "patient_summary": patient_summary}
            )
            return response

        result = benchmark(screen)
        assert result.status_code == 200

    def test_report_generation_latency(self, benchmark):
        """Measure report generation time."""
        def generate_report():
            response = client.post("/api/export-report", json={})
            return response

        result = benchmark(generate_report)
        assert result.status_code == 200
        assert result.headers["Content-Type"] == "application/pdf"
```

---

## Security Testing

### Security Test Checklist

- [ ] **HTTPS Enforcement:** All endpoints respond to HTTPS only; HTTP redirects
- [ ] **CORS:** Frontend can access API; other origins rejected
- [ ] **Session Security:** Cookie HTTP-only, Secure, SameSite=Strict
- [ ] **PII Detection:** Patient data with names/MRN/SSN detected and blocked
- [ ] **Input Sanitization:** HTML tags removed, special chars escaped
- [ ] **API Rate Limiting:** 100 requests/hour per session enforced
- [ ] **SQL Injection:** (Not applicable; no SQL used) ✓
- [ ] **XSS Prevention:** User input never rendered as HTML ✓
- [ ] **CSRF Protection:** CORS prevents cross-site requests ✓
- [ ] **API Key Security:** Keys in Secrets Manager, not in code ✓
- [ ] **Error Messages:** No sensitive info (stack traces, keys, paths) in errors ✓

**Example HTTPS Test:**

```bash
# Attempt HTTP; should redirect
curl -I http://localhost:8000/health
# Response: 301 Moved Permanently, Location: https://localhost:8000/health

# HTTPS should work
curl -I https://localhost:8000/health
# Response: 200 OK
```

---

## Manual QA Checklist

### Before Each Release

- [ ] **Smoke Test:** Upload PDF → Extract → Screen → Export on all 3 therapeutic areas
- [ ] **Data Entry:** Free-text and structured form both work
- [ ] **Results Display:** All three statuses (ELIGIBLE, NOT_ELIGIBLE, REQUIRES_REVIEW) display correctly
- [ ] **Disclaimers:** All disclaimers present and user must acknowledge
- [ ] **Accessibility:** Tab navigation works; color not sole differentiator; screen reader compatible
- [ ] **Mobile:** Responsive design works on iPad (min width 600px)
- [ ] **Browser Compatibility:** Chrome, Firefox, Safari latest versions
- [ ] **Error Handling:** Upload fails, extraction timeout, network errors all handled gracefully
- [ ] **Performance:** No visible lag on interactions; results appear within expected time
- [ ] **Data Privacy:** No patient data visible in URLs, logs, or system messages
- [ ] **Keyboard Navigation:** All buttons and links accessible via keyboard

---

## Continuous Integration (CI/CD) Gates

### GitHub Actions Pipeline

```yaml
# .github/workflows/test.yml
name: Test and Evaluate

on: [push, pull_request]

jobs:
  backend-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.9'
      - name: Install dependencies
        run: pip install -r backend/requirements.txt -r backend/requirements-dev.txt
      - name: Run unit tests
        run: pytest backend/tests/test_*.py --cov=app
      - name: Lint
        run: flake8 app/ tests/
      - name: Type check
        run: mypy app/

  frontend-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
        with:
          node-version: '18'
      - name: Install dependencies
        run: npm install
      - name: Run tests
        run: npm run test
      - name: Lint
        run: npm run lint
      - name: Build
        run: npm run build

  llm-evaluation:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
      - name: Install dependencies
        run: pip install -r backend/requirements.txt -r backend/requirements-dev.txt
      - name: Run extraction evaluation
        run: python evaluation/eval_extraction.py
      - name: Run screening evaluation
        run: python evaluation/eval_screening.py
      - name: Check thresholds
        run: |
          EXTRACTION_F1=$(grep "F1=" eval_extraction.log | awk '{print $2}')
          SCREENING_CONC=$(grep "Concordance=" eval_screening.log | awk '{print $2}')

          if (( $(echo "$EXTRACTION_F1 < 0.90" | bc -l) )); then
            echo "Extraction F1 below 90% threshold"
            exit 1
          fi

          if (( $(echo "$SCREENING_CONC < 0.85" | bc -l) )); then
            echo "Screening concordance below 85% threshold"
            exit 1
          fi
```

---

## Test Artifacts and Reports

### What Gets Tracked

1. **Unit Test Results:** Coverage %, pass/fail count, slow tests
2. **Integration Test Results:** Endpoint response times, error rates
3. **LLM Evaluation Metrics:** Precision, recall, F1, concordance, FNR
4. **Performance Metrics:** Latencies for each operation (percentiles)
5. **Security Scan Results:** Vulnerability scan results (OWASP, dependency checks)

### Test Report Template

```markdown
# Test Report - Release 1.0.0

## Summary
- **Build Status:** PASSED ✓
- **Overall Quality:** HIGH
- **Ready for Release:** YES

## Unit Tests
- Backend: 87/90 tests passed (96.7% pass rate)
- Frontend: 42/45 tests passed (93.3% pass rate)
- Coverage: 91% (target: >90%) ✓

## Integration Tests
- All 15 endpoint tests passed ✓
- No performance regressions

## LLM Evaluation
- Extraction F1: 92% (target: >90%) ✓
- Screening Concordance: 87% (target: >85%) ✓
- False Negative Rate: 3% (target: <5%) ✓
- Confidence Calibration: 91% (target: >90%) ✓

## Performance Benchmarks
- Extraction P95: 35s (target: <40s) ✓
- Screening P95: 18s (target: <20s) ✓
- Report generation P95: 9s (target: <12s) ✓

## Security Scan
- Vulnerability count: 0 (critical/high)
- Dependencies checked: ✓

## Manual QA
- Smoke tests: All 3 therapeutic areas passed ✓
- Accessibility scan: WCAG AA compliant ✓
- Browser compatibility: Chrome, Firefox, Safari tested ✓

## Known Limitations
- None blocking release

## Sign-Off
- QA Lead: [Name] - APPROVED
- Release Manager: [Name] - APPROVED
```

---

## Sign-Off

| Role | Name | Date | Signature |
|------|------|------|-----------|
| QA Lead | [Name] | 2026-03-24 | — |
| Test Automation Engineer | [Name] | 2026-03-24 | — |
| Product Manager | [Name] | 2026-03-24 | — |

---

**END OF TESTING STRATEGY DOCUMENT**
