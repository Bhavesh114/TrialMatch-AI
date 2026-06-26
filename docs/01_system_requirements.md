# System Requirements Document (SRD)
## TrialMatch AI — Clinical Trial Eligibility Screener

**Document Version:** 1.0
**Last Updated:** 2026-03-24
**Status:** Final - MVP v1.0
**Audience:** Product team, engineering, QA, compliance

---

## Executive Summary

TrialMatch AI is a clinical trial eligibility screening tool that automates the first-pass evaluation of patient eligibility against trial inclusion/exclusion criteria. The tool addresses the critical bottleneck in drug development: clinical trial enrollment, which delays study timelines by an average of 3-6 months and costs sponsors $600K-$8M per month when delayed.

**Core Problem Being Solved:**
- Study coordinators spend 40-60% of their time manually reviewing patient records against trial criteria (15-45 minutes per patient-trial pair)
- Current manual process has 10-15% error rate (patients enrolled later found ineligible)
- 80% of trials miss enrollment targets, primarily due to slow patient screening

**Product Approach:**
The tool reads a clinical trial protocol PDF, extracts eligibility criteria in structured form, then evaluates a de-identified patient summary against each criterion with transparent, auditable reasoning. The design prioritizes transparency over full automation—every eligibility determination shows the LLM's reasoning for coordinator verification, maintaining clinical governance while accelerating workflow.

**Success Criteria:**
- Criteria extraction accuracy: >90%
- Screening concordance with expert manual review: >85%
- Time to screen one patient: <3 minutes (vs 15-45 minutes manual)
- False negative rate: <5%
- Missing data identification: >80% accuracy

---

## Stakeholders and User Personas

### Primary Stakeholder: Study Coordinator (Sarah)

**Profile:**
- Role: Clinical Research Associate/Coordinator responsible for patient recruitment and enrollment
- Manages: 4-6 active trials simultaneously
- Time investment: ~3 hours per day on eligibility screening
- Medical background: Familiar with clinical terminology, but not a physician; relies on source documents for clinical interpretation
- Technical skill: Intermediate (comfortable with web tools, not a developer)
- Pain points:
  - Manual criterion matching is repetitive and error-prone
  - Context-switching between multiple trials reduces accuracy
  - High volume of ineligible-on-review situations creates frustration
  - No easy way to document screening rationale for audit purposes

**Goals:**
- Screen patients faster while maintaining accuracy
- Clearly understand why a patient is ineligible (to discuss with PI and patient)
- Export auditable screening records for regulatory/safety purposes
- Reduce re-screening when new information arrives

**Constraints:**
- Does not want responsibility for final clinical judgment (wants AI to highlight issues, not decide)
- Works under Study Coordinator supervision; cannot approve enrollment alone
- Needs tool that respects patient privacy (no PII/PHI storage)

### Secondary Stakeholder: Principal Investigator (Dr. Patel)

**Profile:**
- Role: Physician leading 2-3 clinical trials; oversees enrollment decisions
- Decision authority: Final approval on all enrollment decisions
- Time investment: 5-10 hours per week on screening oversight
- Medical background: Deep clinical expertise; expects nuance in edge cases
- Technical skill: Low to intermediate (wants tool to not require learning curve)
- Pain points:
  - Cannot review every screening decision; focuses on flagged/borderline cases
  - Needs confidence in automated screening to trust it
  - Concerned about liability if tool misses an ineligibility

**Goals:**
- Confident, auditable screening that reduces re-screening burden
- Clear visibility into reasoning (not a black box)
- Ability to override/correct tool assessments
- Support for edge cases (compound criteria, clinical judgment calls)

**Constraints:**
- Tool must not create false sense of certainty (scores/confidence are important)
- Will not use tool if it doesn't show work
- Retains final decision authority

### Tertiary Stakeholder: Clinical Trial Sponsor/Monitor

**Profile:**
- Role: Pharmaceutical company or CRO overseeing trial execution
- Concern: Regulatory compliance, protocol adherence, enrollment timeline
- Time investment: Periodic audits and monthly reports
- Pain points:
  - Re-screening of enrolled patients creates regulatory risk
  - Slow enrollment delays drug development and increases costs
  - No easy audit trail of screening decisions

**Goals:**
- Faster enrollment with documented rationale
- Compliance-ready screening records
- Reduction in protocol violations related to ineligibility

### Quaternary Stakeholder: Quality Assurance / Compliance Officer

**Profile:**
- Role: Ensures tool meets regulatory expectations, data protection requirements
- Concern: HIPAA compliance, de-identification standards, liability
- Time investment: Review of architecture, data flows, testing approach

**Goals:**
- Clear data handling policy (de-identified only, session-based, no persistence)
- Audit trail of screening decisions
- Compliance boundaries clearly documented

---

## Functional Requirements

### FR-001: Protocol PDF Upload and Validation
**Description:** User can upload a clinical trial protocol PDF file (single upload per session).

**Acceptance Criteria:**
- Upload accepts files up to 50 MB in size
- Supported formats: PDF only (both searchable and scanned)
- Rejected files show user-friendly error message: "File must be a PDF under 50 MB"
- Upload triggers file scan for malware/security (backend responsibility)
- UI shows progress indicator during upload
- On successful upload, PDF is temporarily stored in S3 with auto-delete after 24 hours
- Frontend displays protocol preview (first 5 pages) alongside extraction interface

**Technical Notes:**
- No file size validation on frontend; validation occurs backend
- Uploaded files trigger async extraction task; user does not wait for full extraction
- Maximum concurrent uploads per session: 1

---

### FR-002: Protocol Text Extraction
**Description:** System extracts full text from uploaded PDF using PyMuPDF with OCR fallback.

**Acceptance Criteria:**
- Extracts text from searchable PDFs with >98% accuracy
- Fallback to Tesseract OCR for scanned/image PDFs
- Flags extracted text with confidence score; <90% confidence shows warning to user: "Text extraction confidence low; review extracted criteria carefully"
- System handles multi-language protocols (at minimum recognizes non-English; future phases support translation)
- Timeout after 30 seconds; returns error if extraction takes longer
- For protocols >100 pages, extraction splits into chunks with progress tracking

**Technical Notes:**
- PyMuPDF preferred for performance; Tesseract as fallback for image PDFs
- Confidence score based on character recognition quality, not user perception
- Text extraction output cached in session for re-use

---

### FR-003: Eligibility Criteria Extraction
**Description:** LLM analyzes protocol text and extracts all inclusion and exclusion criteria in structured form.

**Acceptance Criteria:**
- Returns JSON array with minimum 8 and maximum 80 criteria per protocol
- Each criterion includes:
  - `criterion_id` (I1, I2... or E1, E2...)
  - `type` ("inclusion" or "exclusion")
  - `description` (plain language, 1-2 sentences)
  - `category` (one of: demographics, diagnosis, lab_values, medications, medical_history, procedures, functional_status, other)
  - `data_points_needed` (array of specific fields required to evaluate)
  - `logic` (compound conditions: AND, OR, temporal)
- Criteria extracted within 60 seconds (timeout failure shows "Extraction took too long; please try a shorter protocol" message)
- Extraction completeness >90% (tested against gold standard protocols)
- No duplicate criteria returned

**Technical Notes:**
- Uses Claude Sonnet 4 with specific system prompt for criteria extraction
- Prompt includes instruction to be exhaustive; missing a criterion means risk of incorrect enrollment
- Results cached after extraction for re-use during screening

---

### FR-004: Criteria Review and Manual Editing
**Description:** Coordinator reviews extracted criteria list and can edit, delete, or add criteria before screening begins.

**Acceptance Criteria:**
- Criteria displayed in human-readable list format, grouped by type (inclusion/exclusion) then category
- Each criterion shows all fields; can be edited inline
- Coordinator can:
  - Edit criterion description or logic
  - Delete a criterion (with confirmation: "Deleting this criterion means patients matching only this will not be flagged. Continue?")
  - Add a new criterion manually (form with all required fields)
  - Revert to extracted version (undo all edits with one click)
- Edited criteria persisted in session (not stored persistently)
- Cannot proceed to patient screening until at least 1 criterion defined
- UI shows count of total, inclusion, and exclusion criteria

**Technical Notes:**
- All edits local to session; if user navigates away and returns, edits are lost
- Deletion or addition of criteria does not change criterion_ids for already-extracted criteria
- Add-new-criterion generates next available id (e.g., if E5 is highest, new exclusion = E6)

---

### FR-005: Patient Summary Input (Free-Text)
**Description:** User can paste de-identified clinical notes/patient summary as free text.

**Acceptance Criteria:**
- Text input accepts up to 5,000 characters (displays character count; warning at 4,000+ characters)
- Accepts any text format (clinical note copy-paste, structured notes, bullet points)
- Sanitizes input to remove potential PII (e.g., medical record numbers if detected)
- Shows example input format: "Age: 55, Male. Diagnosis: Type 2 Diabetes. HbA1c 8.2%. BMI 31. Medications: Metformin 1000mg BID. No history of..."
- Input persisted in session (not stored externally)
- No input validation beyond character count; AI handles incomplete/messy data

**Technical Notes:**
- Input not validated for completeness; screening engine returns INSUFFICIENT_DATA for missing criteria
- Free-text approach intentionally flexible to support varied coordinator practices
- No spell-check or grammar correction

---

### FR-006: Patient Summary Input (Structured Form)
**Description:** Alternative to free-text: coordinator can fill structured form with common fields.

**Acceptance Criteria:**
- Form fields include:
  - Age (integer, 18-120)
  - Sex (dropdown: Male, Female, Other)
  - Primary diagnosis (text field, 100 char max)
  - Secondary diagnoses (text, comma-separated)
  - Current medications (text, comma-separated with dosages optional)
  - Lab values (key-value pairs: test name, value, unit, date)
  - Comorbidities (checkboxes: hypertension, diabetes, kidney disease, cancer, heart disease, liver disease, other)
  - Functional status (dropdown: Independent, Assisted, Dependent)
  - Recent procedures (text, comma-separated)
  - Allergies (text, comma-separated)
  - Pregnancy status (dropdown: Not pregnant, Pregnant, Unknown)
  - Additional notes (text, 500 char max)
- All fields optional; only age required (to distinguish from empty input)
- Form converts to free-text summary on submission (backend receives freetext representation)
- Option to switch between free-text and structured input mid-session

**Technical Notes:**
- Form validation happens frontend; prevents submission if age missing or invalid
- Structured form converts to narrative format internally: "Age 55, Male. Diagnosis: Type 2 Diabetes Mellitus. HbA1c 8.2% (date: 2024-03-10)..."
- Allows user to choose entry method based on available information

---

### FR-007: Patient Screening
**Description:** System evaluates patient against all extracted criteria, returning structured pass/fail/insufficient assessment.

**Acceptance Criteria:**
- For each criterion, system returns:
  - `criterion_id`
  - `status` (enum: "MEETS" | "DOES_NOT_MEET" | "INSUFFICIENT_DATA")
  - `confidence` (enum: "high" | "medium" | "low")
  - `reasoning` (2-3 sentences citing specific patient data)
  - `missing_data` (if status = INSUFFICIENT_DATA, list of specific info needed)
- Screening completes within 90 seconds
- Overall eligibility summary calculated:
  - ELIGIBLE: all inclusion criteria MEETS, no exclusion criteria DOES_NOT_MEET, no INSUFFICIENT_DATA for inclusion
  - NOT_ELIGIBLE: >=1 inclusion criterion DOES_NOT_MEET OR >=1 exclusion criterion DOES_NOT_MEET
  - REQUIRES_REVIEW: >=1 INSUFFICIENT_DATA (regardless of inclusion/exclusion)
- Confidence scores calibrated: high confidence only when patient data clearly matches/doesn't match criterion logic
- System returns missing data list aggregated across all INSUFFICIENT_DATA criteria

**Technical Notes:**
- Uses Claude Sonnet 4 with specific system prompt for screening stage
- Prompt emphasizes: "If in doubt, return INSUFFICIENT_DATA; the coordinator will verify"
- Screening cached per session to avoid re-running same patient against same criteria

---

### FR-008: Screening Results Display
**Description:** Results presented in clear, coordinator-friendly format with visual hierarchy.

**Acceptance Criteria:**
- Top-level summary:
  - Overall eligibility status (ELIGIBLE / NOT ELIGIBLE / REQUIRES REVIEW) with large, color-coded badge
  - Count of criteria met, not met, insufficient
  - Primary reason for ineligibility (if NOT ELIGIBLE)
- Detailed per-criterion breakdown showing:
  - Criterion description (editable, linked to criteria review)
  - Status badge (color-coded: green for MEETS, red for DOES_NOT_MEET, yellow for INSUFFICIENT_DATA)
  - Confidence score as meter/percentage (e.g., "High confidence" or "65% confidence")
  - Reasoning text (rendered as callout/card)
  - If INSUFFICIENT_DATA: highlighted missing data with suggested follow-up questions
- Missing data summary at bottom: aggregated list of all requested information
- All results can be printed to PDF (see FR-009)

**Technical Notes:**
- Visual hierarchy uses color, size, typography to guide coordinator attention
- Status badges consistent across entire app
- Reasoning text formatted for readability (not wall of text)

---

### FR-009: Screening Report Export
**Description:** User can download screening results as PDF report with audit trail.

**Acceptance Criteria:**
- Report includes:
  - Protocol title and version (extracted from PDF metadata if available)
  - Trial ID / NCT number (if present in protocol text)
  - Screening date and time (auto-generated)
  - Patient summary (de-identified, as entered by user)
  - Overall eligibility determination
  - Per-criterion assessment table (criterion, status, reasoning, confidence)
  - Missing data list with suggested follow-ups
  - Disclaimer: "This screening is for efficiency support only and does not replace clinical judgment by the study team. All determinations must be verified by the Study Coordinator and Principal Investigator."
  - Footer: "Generated by TrialMatch AI on [DATE]. This report is not a clinical decision and must not be used as the sole basis for enrollment."
- PDF filename format: `TrialMatch_Screening_[TRIALID]_[DATE]_[TIMESTAMP].pdf`
- PDF report can be downloaded immediately; not emailed
- Report does NOT include patient name, MRN, or other PHI (even if accidentally included in summary)

**Technical Notes:**
- Uses ReportLab or WeasyPrint for PDF generation
- Report template includes styled tables, headings, page breaks
- No PHI in footer or metadata
- Report generation completes within 10 seconds

---

### FR-010: Session Management
**Description:** User session contains protocol, criteria, patient data, and screening results; all cleared on logout or session timeout.

**Acceptance Criteria:**
- Session persists throughout single workflow (upload → criteria review → patient screening → report export)
- Session timeout after 30 minutes of inactivity; warning shown at 25 minutes
- Explicit logout clears all data immediately
- Page refresh within active session preserves data
- Closing tab/browser does not persist data
- No user accounts required for MVP (session-only, no login)
- Concurrent sessions per browser: 1

**Technical Notes:**
- Session stored in React Context frontend + in-memory session on backend (no database)
- Session ID generated on first request; passed via HTTP-only cookie
- No persistent session storage (in-memory only; lost on backend restart)

---

### FR-011: Error Handling – PDF Upload Failures
**Description:** Clear error messages when protocol upload fails.

**Acceptance Criteria:**
- File too large (>50 MB): "File size exceeds 50 MB limit. Please upload a smaller protocol PDF."
- Wrong file type: "File must be a PDF. Please try again."
- File corrupted: "PDF appears corrupted. Try re-downloading from source and uploading again."
- Malware detected: "File failed security scan. Please verify source and try again."
- Network timeout: "Upload timed out after 30 seconds. Check your connection and try again."
- Each error includes suggestion for user action
- Error does not crash session; user can retry upload

---

### FR-012: Error Handling – Extraction Failures
**Description:** Clear error messages when criteria extraction fails.

**Acceptance Criteria:**
- Timeout (>60 seconds): "Criteria extraction took too long. This protocol may be too long for processing. Try splitting it into sections."
- LLM failure/rate limit: "System is currently busy. Please try again in a few minutes."
- Empty/invalid text extracted: "Could not read text from this PDF. If it's a scanned image, try a different file. Contact support if this persists."
- Low confidence extraction: Warning message (not error): "Text extraction confidence was low (78%). Please review criteria carefully for accuracy."
- User can retry extraction without re-uploading

---

### FR-013: Error Handling – Screening Failures
**Description:** Clear error messages when patient screening fails.

**Acceptance Criteria:**
- No criteria loaded: "No criteria defined. Please go back to review extracted criteria and ensure at least one is selected."
- No patient data: "Please enter patient information (free text or form) before screening."
- Screening timeout (>90 seconds): "Screening took too long. This may indicate a very complex protocol. Try simplifying patient input and try again."
- LLM failure: "Screening failed. Please try again in a few moments."
- All errors allow retry without re-entering data

---

### FR-014: Screening Confidence Scores
**Description:** System assigns confidence levels (high/medium/low) to each screening assessment.

**Acceptance Criteria:**
- Confidence calibrated by LLM based on:
  - Clarity of criterion (explicit vs ambiguous)
  - Completeness of patient data for that criterion
  - Presence of compound logic (AND/OR conditions)
- High confidence: Patient data clearly matches or doesn't match criterion; no ambiguity
- Medium confidence: Criterion is clear but patient data incomplete for definitive assessment; OR criterion ambiguous but patient data complete
- Low confidence: Both criterion and patient data are ambiguous/incomplete; judgment call required
- Confidence displayed visually (colored meter or badge)
- Low confidence scores do not block ELIGIBLE determination; but flag that PI should review

**Technical Notes:**
- Confidence not a statistical confidence interval; it's a heuristic measure of decisiveness
- Prompt explicitly asks LLM to assign confidence based on clarity + completeness

---

### FR-015: Missing Data Detection and Flagging
**Description:** System identifies and lists specific missing data points needed for complete screening.

**Acceptance Criteria:**
- For each criterion with status INSUFFICIENT_DATA:
  - System specifies exactly what data is missing: "Recent HbA1c value needed (criterion: HbA1c must be <8.0%)"
  - Suggests where to find it: "Check recent lab panel or ask patient"
  - No generic "missing data" responses; always specific
- Aggregated missing data list at bottom of results
- Missing data list de-duplicated (if 3 criteria need recent HbA1c, shown once)
- Sort missing data by frequency (most-needed first)

**Technical Notes:**
- Generated by screening LLM prompt; not post-processed
- Missing data tied to specific criteria for traceability

---

### FR-016: Compound Criteria Handling
**Description:** System correctly interprets and evaluates criteria with AND/OR logic and temporal conditions.

**Acceptance Criteria:**
- AND criteria: "Age 18-65 AND no prior chemotherapy" correctly requires both conditions met
- OR criteria: "HbA1c <8.0% OR currently on diabetes medication" accepts if either true
- Temporal conditions: "Diagnosed within last 6 months" correctly identifies recency
- Complex nesting: "Age 50-75 AND (no history of CVD OR well-controlled hypertension)" is correctly parsed
- System does not hallucinate additional logic; returns INSUFFICIENT_DATA if logic unclear

**Technical Notes:**
- Extraction prompt explicitly asks for logic field; screening prompt respects that logic
- Edge cases: "recently" without explicit timeframe returns INSUFFICIENT_DATA with note: "Criterion uses 'recently' without clear timeframe. Ask PI for clarification."

---

### FR-017: Ambiguous Criteria Handling
**Description:** System handles ambiguous or clinically nuanced criteria by returning INSUFFICIENT_DATA with explanation.

**Acceptance Criteria:**
- Vague criterion ("good renal function") → INSUFFICIENT_DATA: "Criterion 'good renal function' is subjective. Specific eGFR threshold needed."
- Contextual criteria ("stable disease") → INSUFFICIENT_DATA if context missing: "Disease stability cannot be confirmed without recent imaging/assessment dates."
- Clinical judgment criteria ("clinically significant contraindication") → INSUFFICIENT_DATA: "This criterion requires clinical judgment. Coordinator should review patient comorbidities and discuss with PI."
- System never returns MEETS for ambiguous criteria without patient data
- System never assumes clinic values or trends

**Technical Notes:**
- Prompt teaches LLM to recognize ambiguity and ask for clarification rather than guess
- Ambiguous criteria noted in extraction review stage; coordinator can clarify before screening

---

### FR-018: False Negative Prevention
**Description:** System designed to minimize risk of screening ELIGIBLE when patient is actually ineligible (false negatives).

**Acceptance Criteria:**
- Prompt explicitly instructs LLM: "If in doubt, return INSUFFICIENT_DATA rather than MEETS"
- Testing methodology measures false negative rate <5% against expert manual review
- Edge cases with high false negative risk (lab thresholds, temporal conditions) logged for monitoring
- No "confidence" score ever allows assumption of missing data

**Technical Notes:**
- Architectural choice: prefer false positives (flagging for coordinator review) over false negatives (missing ineligibility)
- Success metric: <5% false negative rate across eval dataset

---

### FR-019: Criterion ID Stability
**Description:** Criteria extracted from a protocol receive stable IDs (I1, I2..., E1, E2...) consistent across sessions.

**Acceptance Criteria:**
- First inclusion criterion = I1; second = I2; etc.
- First exclusion criterion = E1; second = E2; etc.
- If coordinator edits a criterion, ID does not change
- If coordinator deletes a criterion, IDs of remaining criteria do not shift
- When importing same protocol in new session, IDs remain consistent (same order)

**Technical Notes:**
- IDs generated by extraction stage in order returned by LLM
- IDs never re-indexed; deletion leaves gap (e.g., I1, I2, [I3 deleted], I4, I5)

---

### FR-020: Clinical Terminology Support
**Description:** System supports medical/clinical terminology throughout.

**Acceptance Criteria:**
- Criteria descriptions use clinical language (e.g., "eGFR", "HbA1c", "LVEF", "CVD")
- Patient input accepts clinical abbreviations (e.g., "Type 2 DM", "HTN", "COPD")
- Criterion categories (diagnosis, lab_values, etc.) reflect clinical workflow
- Example text in forms uses realistic clinical scenarios
- Glossary provided to coordinators (see User Guide)

**Technical Notes:**
- No auto-expansion of abbreviations; coordinators familiar with them
- System respects coordinator domain expertise

---

### FR-021: Protocol Diversity Support
**Description:** System works with protocols from multiple therapeutic areas (oncology, cardiology, diabetes, etc.).

**Acceptance Criteria:**
- Extraction handles >15 criteria reliably across trial types
- Category system (demographics, diagnosis, lab_values, medications, medical_history, procedures, functional_status, other) spans all supported therapeutic areas
- Test protocols provided: breast cancer (oncology), heart failure (cardiology), Type 2 diabetes
- Criteria extraction does not hallucinate area-specific criteria (e.g., doesn't assume imaging requirements if not stated)
- System works equally well with 8-criterion and 60-criterion protocols

---

### FR-022: Scanned PDF Handling
**Description:** System processes both searchable and scanned (image-based) PDFs.

**Acceptance Criteria:**
- Searchable PDF: Text extracted with PyMuPDF, >98% character accuracy
- Scanned PDF: Detected automatically; triggers Tesseract OCR with confidence scoring
- If OCR confidence <90%: Warning shown to coordinator: "This PDF appears to be scanned. Text extraction confidence is 78%. Please review extracted criteria carefully."
- Coordinator can manually correct text in extraction stage
- System does not assume text quality; OCR failures handled gracefully

**Technical Notes:**
- Detection based on PDF text extraction attempt; if <30% text extracted, assume scanned
- Tesseract runs on image pages only; mixed PDFs handled page-by-page
- Timeout for OCR: 20 seconds per page

---

### FR-023: Long Protocol Handling
**Description:** System handles protocols >50 pages efficiently.

**Acceptance Criteria:**
- Protocol >100 pages: chunked extraction (first 50 pages extracted, then second 50, etc.)
- User sees progress indicator: "Extracting criteria from 120-page protocol... Page 50 of 120"
- Total extraction timeout: 90 seconds (not per-page)
- Results merged and de-duplicated (if same criterion appears in multiple sections, shown once)
- Coordinator can review source section for each criterion

**Technical Notes:**
- Chunking prevents token limit issues with very long protocols
- De-duplication based on criterion description similarity (fuzzy match, >90% similarity = duplicate)

---

### FR-024: Protocol Metadata Extraction
**Description:** System extracts protocol metadata (title, version, NCT number, sponsor) if available.

**Acceptance Criteria:**
- Extracts trial title, version number, NCT number, sponsor from protocol text
- Metadata optional (no error if not found)
- Metadata displayed in results and included in export report
- Coordinator can edit metadata if extraction incorrect
- Trial ID in exported report filename

**Technical Notes:**
- Metadata extraction part of stage 1 LLM prompt
- User can override extracted metadata before proceeding

---

### FR-025: Coordinator Override Capability
**Description:** Coordinator can correct/override LLM screening assessments.

**Acceptance Criteria:**
- After screening results displayed, coordinator can click any criterion to edit assessment
- Edit form allows changing:
  - Status (MEETS / DOES_NOT_MEET / INSUFFICIENT_DATA)
  - Confidence level
  - Reasoning text
- Changes persisted in current session
- Report export includes note if any criteria overridden: "Note: 1 criterion assessment manually adjusted by coordinator (Criterion I3)"
- No audit log of who changed what (session-only, no user accounts)

**Technical Notes:**
- Override only affects current session; next run of same patient re-runs extraction fresh
- Overrides useful for PI review and final documentation

---

### FR-026: De-Identification Verification
**Description:** System checks for and warns about potential PII in patient summary.

**Acceptance Criteria:**
- Detects common PII patterns:
  - Names (e.g., "John Smith")
  - Medical record numbers (e.g., "MRN: 123456")
  - Dates of birth (exact DOB, not age)
  - Social security numbers
  - Phone numbers / emails
- Shows warning if PII detected: "Patient summary appears to contain identifiable information (possible name, MRN, or DOB). Remove this before screening."
- Does not block screening (PII detection advisory, not blocker)
- Coordinator can acknowledge and proceed
- PII in summary is NOT sent to LLM (sanitized before API call)

**Technical Notes:**
- PII detection uses regex patterns; not AI-based
- Conservative detection (may over-flag); better safe than sorry
- Does not remove PII automatically; coordinator does
- LLM receives sanitized version regardless

---

### FR-027: Progress Indicators and User Feedback
**Description:** System shows clear progress during long operations.

**Acceptance Criteria:**
- Upload progress: Shows file name, size, upload % complete
- Extraction progress: "Analyzing protocol... 25% complete" (estimated)
- Screening progress: "Screening patient against criteria... 40% complete" (estimated)
- Report generation: "Generating PDF... Please wait" with brief spinner
- All progress indicators disappear on completion or error
- No progress indicator lingers >120 seconds

**Technical Notes:**
- Progress updates streamed from backend to frontend (websocket or polling)
- Estimates based on typical processing time; user manages expectations

---

### FR-028: Accessibility Requirements
**Description:** System meets WCAG 2.1 Level AA accessibility standards.

**Acceptance Criteria:**
- Color not sole means of conveying information (status badges also use text labels)
- Keyboard navigation: All buttons, links, form fields accessible via Tab
- Focus indicators: Clear visual focus on all interactive elements
- Form labels: All inputs have associated labels
- Alt text: All icons have alt text or aria-label
- Screen reader support: Main headings, landmarks, form structure announced correctly
- Font size: Minimum 14px for body text; increases on zoom
- Contrast: All text meets 4.5:1 contrast ratio (WCAG AA)
- Mobile responsive: Tested on iOS Safari and Android Chrome

**Technical Notes:**
- Built using semantic HTML and ARIA landmarks
- React components use proper heading hierarchy
- Testing via axe DevTools and manual screen reader verification

---

### FR-029: Browser Compatibility
**Description:** Application works on modern browsers.

**Acceptance Criteria:**
- Supported browsers:
  - Chrome 90+
  - Firefox 88+
  - Safari 14+
  - Edge 90+
- Tested on latest 2 versions of each browser
- Graceful degradation if JavaScript disabled (no JS = display message: "TrialMatch requires JavaScript enabled")
- Mobile browsers (iOS Safari, Chrome Mobile) work on iPad/Android tablets (minimum screen width 600px)
- Not required to work on IE11 or older browsers

**Technical Notes:**
- Built with modern JavaScript (ES2020+); no IE11 polyfills
- PDF preview may not work on older mobile browsers (graceful degradation)

---

### FR-030: Documentation and Help
**Description:** In-app help and external documentation available.

**Acceptance Criteria:**
- In-app tooltips on complex fields (e.g., hover on "Confidence" explains high/medium/low)
- "?" icons throughout with contextual help
- Link to external User Guide (PDF or web) on every page
- Glossary of terms accessible from app
- Example patient summaries provided in patient input screen
- No jargon without explanation

---

### FR-031: Criterion Category Assignment
**Description:** System assigns extracted criteria to clinical categories for better organization.

**Acceptance Criteria:**
- Each criterion assigned exactly one category:
  - **Demographics:** Age, sex, gender, race/ethnicity, geographic location
  - **Diagnosis:** Primary/secondary diagnoses, indication, disease status (active/stable/resolved)
  - **Lab values:** Blood tests, imaging results, pathology, vital signs
  - **Medications:** Current meds, prior meds, medication classes, medication requirements
  - **Medical history:** Prior illnesses, surgeries, hospitalizations, treatments, vaccination status
  - **Procedures:** Prior surgeries, interventions, specific procedures
  - **Functional status:** Performance status (ECOG, Karnofsky), ADL (activities of daily living), ability to consent
  - **Other:** Anything not fitting above (pregnancy intent, availability, etc.)
- Category used for filtering/sorting in criteria review UI
- Categories consistent across all protocols

**Technical Notes:**
- Categories assigned by extraction LLM; not post-processed
- Categories help coordinator understand criterion type at a glance

---

### FR-032: Data Point Specification
**Description:** For each criterion, system specifies exactly what data is needed to evaluate it.

**Acceptance Criteria:**
- `data_points_needed` array lists specific items:
  - Example (age criterion): `["age", "date_of_birth"]`
  - Example (lab criterion): `["test_name", "value", "unit", "date"]`
  - Example (med criterion): `["medication_name", "dosage", "frequency", "start_date"]`
- Data points are specific, not generic (e.g., "HbA1c value" not just "lab results")
- Used to generate missing data list
- Coordinator can see exactly what info was needed to make each decision

---

## Non-Functional Requirements

### Performance Requirements

**FR-NFR-001: Extraction Performance**
- Criteria extraction latency: <60 seconds for protocols up to 50 pages
- Latency <120 seconds for protocols up to 100 pages
- P95 latency <80 seconds (typical protocols)
- CPU usage: <80% during extraction on single core
- Memory: <500 MB per session (including PDF in memory)

**FR-NFR-002: Screening Performance**
- Patient screening latency: <90 seconds per patient
- P95 latency <100 seconds
- Response time does not degrade with number of criteria (tested up to 80 criteria)
- Concurrent screenings: support 10 simultaneous sessions without degradation

**FR-NFR-003: Frontend Performance**
- Page load time: <2 seconds (first contentful paint)
- Interaction latency (button clicks): <100 ms
- Scrolling and form interaction: smooth (60 FPS)
- Bundle size (JS): <300 KB (gzipped)

**FR-NFR-004: Report Generation**
- PDF report generation: <10 seconds per report
- PDF file size: <5 MB
- Report rendering in viewer: <1 second

---

### Security Requirements

**FR-NFR-005: Input Sanitization**
- All user inputs (text, form fields) sanitized against XSS attacks
- HTML tags stripped from text inputs
- Special characters escaped before rendering
- Regular expressions validated before use

**FR-NFR-006: Session Security**
- Session ID generated cryptographically (128-bit entropy)
- Session data stored only in backend memory (not in localStorage or cookies)
- Session cookie: HTTP-only, Secure (HTTPS only), SameSite=Strict
- Session expiry: 30 minutes inactivity; explicit logout
- No session data persisted to disk or database

**FR-NFR-007: API Security**
- HTTPS only (no HTTP)
- CORS configured strictly (frontend domain only)
- API rate limiting: 100 requests per session per hour
- Request timeout: 120 seconds
- Invalid requests rejected with 400/401/403 responses (never 5xx on user error)

**FR-NFR-008: API Key Security**
- Anthropic API keys stored in AWS Secrets Manager
- Keys never logged or exposed in error messages
- Keys rotated annually
- Backup API keys available for failover

**FR-NFR-009: File Security**
- Uploaded PDFs scanned for malware (ClamAV or equivalent)
- Files stored in S3 with server-side encryption (AES-256)
- S3 bucket not publicly readable
- S3 bucket access logging enabled for audit
- Temporary files auto-deleted after 24 hours (Lambda lifecycle or S3 lifecycle policy)

**FR-NFR-010: Error Message Security**
- No sensitive data in error messages (no API keys, paths, configs)
- Error messages user-friendly, not technical stack traces
- Detailed errors logged server-side only; generic messages shown to user

---

### Reliability Requirements

**FR-NFR-011: Availability**
- Target uptime: 99.5% (30 minutes downtime per month acceptable)
- Graceful degradation: if LLM API unavailable, user shown: "Service temporarily unavailable. Please try again in 5 minutes." (not 5xx error)
- Health check endpoint: `/health` returns 200 if service operational

**FR-NFR-012: Fault Tolerance**
- Extraction failure does not lose uploaded PDF (user can retry)
- Screening failure does not lose patient input or criteria
- Report generation failure does not lose session data
- All data persisted long enough for retry

**FR-NFR-013: Error Recovery**
- Automatic retry: extraction/screening failures retry once after 5 seconds
- Manual retry: user can click "Try Again" for any failed operation
- No data loss on retry

---

### Usability Requirements

**FR-NFR-014: Intuitiveness**
- First-time user can screen a patient without documentation (task completion rate >90%)
- Coordinator with clinical background completes first screening in <10 minutes
- No non-obvious UI patterns (no hidden menus, no right-click required)

**FR-NFR-015: Visual Hierarchy**
- Important information (overall eligibility, ineligibility reason) shown prominently
- Results scannable in <10 seconds for overall status
- Detailed information (per-criterion reasoning) easily accessed but not overwhelming

**FR-NFR-016: Feedback and Control**
- Every action has feedback (success message, visual change, etc.)
- No actions without undo/correction (except final PDF export)
- User always knows what screen they are on and how to go back

---

### Compliance Requirements

**FR-NFR-017: De-Identification Standard**
- Patient summaries processed as de-identified per HIPAA Safe Harbor method
- No PHI persisted (not even temporary)
- Summary data not merged with external data
- No unique identifiers combined with quasi-identifiers
- Screening reports generated with de-identified data only

**FR-NFR-018: Audit Trail**
- Screening decisions logged with: timestamp, criteria set version, patient summary (de-id), results, any coordinator overrides
- Logs stored for 90 days
- Logs not accessible to end user (admin only, for compliance review)
- Log entry includes: trial ID, criteria version, screening status, timestamp

**FR-NFR-019: Disclaimers**
- Legal disclaimer shown on every report: "This screening is for efficiency support only and does not replace clinical judgment by the study team."
- Disclaimer also shown on results page before export
- Disclaimer not waivable; always present in export

**FR-NFR-020: Regulatory Scope**
- MVP explicitly scoped as decision support tool (not automated decision-making)
- Tool does not execute enrollment; coordinator does
- Tool does not diagnose or assess clinical eligibility; screening support only
- Documentation and UI clearly state these boundaries

---

## System Constraints and Assumptions

### Constraints

**Technical Constraints:**
1. Maximum PDF size: 50 MB (file size limit)
2. Maximum extraction timeout: 120 seconds per protocol
3. Maximum screening timeout: 90 seconds per patient
4. Maximum concurrent sessions: 1 per browser (session ID = browser instance)
5. Maximum criteria per protocol: 80 (safety limit)
6. Maximum patient summary length: 5,000 characters
7. S3 temporary file retention: 24 hours (non-configurable)
8. API rate limit: 100 requests per session per hour

**Operational Constraints:**
1. No database (MVP stateless)
2. No user accounts or login
3. No persistent history (sessions cleared on logout/timeout)
4. No offline mode (internet connection required)
5. No multi-protocol comparison (one protocol per session)
6. No batch screening (one patient per screening request)
7. No integration with EHR systems (MVP)

**Clinical Constraints:**
1. System does not make enrollment decisions (coordinator does)
2. System not validated as diagnostic tool
3. System not subject to CLIA or CAP regulations (decision support, not diagnostics)
4. PI oversight required for all enrollment decisions
5. No real-time clinical monitoring (tool is one-time screening, not ongoing)

---

### Assumptions

**User Assumptions:**
1. Coordinator familiar with trial protocols and patient summaries
2. Coordinator responsible for de-identification before pasting patient data
3. Coordinator understands clinical terminology (no tool education on medical concepts)
4. Patient summaries accurate and current (tool does not verify data quality)
5. Coordinator will verify all AI assessments before enrollment decision

**Technical Assumptions:**
1. PDF protocols written in English (MVP assumption; multi-language future)
2. Trial protocols structured similarly (standard format, not exotic layouts)
3. Internet connection stable throughout session
4. Anthropic Claude API always available (no extended outages)
5. S3 bucket and Lambda environments functioning (no infrastructure failures)
6. Browsers support modern JavaScript (ES2020+)

**Operational Assumptions:**
1. Clinical trial sponsor liable for enrollment decisions (not tool vendor)
2. TrialMatch AI used only for de-identified, domestic trial screening (not international regulatory)
3. Coordinator trained on tool before use
4. PI available for consultation on ambiguous cases
5. Tool not used for real-time enrollment (batch processing okay, but not production decision-making without review)

**Clinical Assumptions:**
1. Eligibility criteria stable during screening period (not changing mid-session)
2. Patient data is current (not historical screening)
3. Coordinator has authority to access and enter patient information
4. Study protocol reflects actual enrollment decisions (protocol describes actual screening, not aspirational)

---

## External Dependencies and Integrations

### Anthropic Claude API

**Service:** Anthropic Generative AI (Claude Sonnet 4)
**Purpose:** Criteria extraction and patient screening LLM
**Dependency Level:** Critical (system non-functional without it)
**Service Level Expectation:** 99.9% uptime
**Fallback Strategy:** Retry 3 times with exponential backoff; after 3 failures, show error to user
**Cost Model:** Pay-per-token (no fixed contract; usage-based)
**Quota Management:** No hard quota enforced; monitor monthly spend and alert if >$500/month

### AWS Services

**S3 (Simple Storage Service):**
- Purpose: Store temporary uploaded PDFs
- Lifecycle policy: Auto-delete after 24 hours
- Encryption: Server-side AES-256
- Versioning: Disabled (single version per upload)
- Dependency level: Important (upload fails if S3 unavailable)

**Lambda / Fargate:**
- Purpose: Compute for backend API
- Scaling: Auto-scale based on concurrent requests (min 1, max 10 instances)
- Timeout: 120 seconds per request
- Dependency level: Critical

**Secrets Manager:**
- Purpose: Store Anthropic API keys
- Rotation: Annual manual rotation
- Encryption: AWS KMS
- Dependency level: Critical (API calls fail if key not accessible)

**CloudFront:**
- Purpose: CDN for frontend (React app)
- Cache TTL: 1 hour for HTML, 1 week for JS/CSS
- Dependency level: Important (frontend slow if CDN unavailable, but still works)

### External Services

**GitHub Actions:**
- Purpose: CI/CD (testing, build, deployment)
- Triggers: On push to main branch
- Dependency level: Important (development only, not runtime)

**Vercel (Frontend Deployment):**
- Purpose: Host React frontend
- Deployment trigger: Push to GitHub
- Dependency level: Critical (frontend unavailable if Vercel down)

### No Integrations (Out of Scope)

The following are explicitly OUT OF SCOPE for MVP and documented as Phase 2/3 work:
- EHR systems (Epic, Cerner, OpenEMR)
- ClinicalTrials.gov API
- External lab/imaging systems
- Single sign-on (SSO) / LDAP
- Database systems

---

## Data Flow Requirements

### Data Classification

**De-Identified Data (Allowed in MVP):**
- Age, sex, demographics (not linked to names or MRN)
- Diagnosis codes/descriptions (not patient name or ID)
- Lab values and vital signs (not with dates that could re-identify)
- Medication lists (not with specific pharmacy)
- Medical history (not with patient identifiers)

**Potentially Identifiable Data (Restricted):**
- Patient names
- Medical record numbers (MRN)
- Dates of birth (exact; age is okay)
- Phone numbers, addresses
- Social security numbers

**Protected Information (Never Stored):**
- Payment/insurance information
- Genetic information
- Biometric data (beyond lab values)
- Mental health diagnosis (unless central to trial)

### Session Data Flow

```
1. Upload PDF
   ├─ Frontend: User selects file
   ├─ Backend: Validate file, scan for malware
   ├─ S3: Store temporarily with auto-delete after 24h
   ├─ Session: Store S3 path + metadata
   └─ Response: PDF preview + URL path

2. Extract Criteria
   ├─ Backend: Retrieve PDF from S3
   ├─ PyMuPDF: Extract text (OCR fallback)
   ├─ Claude API: Call extraction prompt with text
   ├─ Session: Store extracted criteria + LLM response
   ├─ Coordinator: Review and edit criteria in-session
   └─ Response: Criteria list, editable, persistent in session

3. Input Patient Summary
   ├─ Frontend: Free-text or structured form input
   ├─ Session: Store patient summary (de-identified)
   ├─ Validation: Check for obvious PII, warn coordinator
   └─ Response: Summary preview, confirmation to proceed

4. Screen Patient
   ├─ Backend: Retrieve criteria + patient summary from session
   ├─ Claude API: Call screening prompt with criteria + patient
   ├─ Session: Store screening results + LLM response
   ├─ Response: Detailed results with confidence/reasoning

5. Export Report
   ├─ Backend: Retrieve protocol metadata + criteria + results from session
   ├─ PDF generation: ReportLab create PDF with tables/formatting
   ├─ Response: PDF file (download, not email)
   └─ Session: Screening report logged for audit (timestamp, trial ID, results)

6. Session Timeout / Logout
   ├─ Session: Clear all data from backend memory
   ├─ S3: Temporary PDF cleaned up after 24h anyway
   ├─ Logs: Audit record persisted (timestamp, actions, no patient data)
   └─ Frontend: Redirect to home page
```

### PII/PHI Handling

**Input Validation:**
- Before screening, PII detection regex scans patient summary
- If PII found, warning shown; user must acknowledge before proceeding
- Tool does not remove PII automatically (manual coordinator action)

**In-Transit:**
- Patient summary sent to Claude API (encrypted HTTPS)
- API request includes de-identified data only
- API response (screening results) received over HTTPS
- No logging of request/response bodies that contain patient data

**In-Storage:**
- Session data: In-memory only (lost on backend restart)
- S3 PDFs: Not patient data (protocol only); 24h auto-delete
- Audit logs: De-identified only (timestamp, trial ID, actions, NOT patient summary or results)
- No database (no persistent patient data)

**Output:**
- Reports: De-identified (coordinator responsible for not including PII in summary)
- Filename: `TrialMatch_Screening_[TRIALID]_[DATE]_[TIMESTAMP].pdf` (no patient identifiers)
- Report footer: Disclaimer that this is decision support, not clinical decision

### Data Retention Policy

| Data Type | Storage Location | Retention | Clearance |
|-----------|------------------|-----------|-----------|
| Uploaded PDF | S3 | 24 hours | Auto-delete via S3 lifecycle |
| Session data (criteria, patient, results) | Backend memory | Session active | On logout or 30 min timeout |
| Audit logs (anonymized) | CloudWatch / logs | 90 days | Automatic log rotation |
| Export PDF (user-downloaded) | User's computer | N/A | User responsible for deletion |
| API logs (no patient data) | CloudWatch | 30 days | Automatic rotation |
| Error logs (sanitized) | CloudWatch | 14 days | Automatic rotation |

---

## Edge Cases and Exception Handling

### PDF-Related Edge Cases

**EC-001: Scanned PDF with Low OCR Confidence**
- Scenario: User uploads fax of protocol (very low image quality)
- Handling: Extract text with OCR, confidence score 45%
- User experience: Warning message "Text extraction confidence is low (45%). Please carefully review extracted criteria."
- Recommendation: User can upload higher-quality version or manually review criteria

**EC-002: PDF with Mixed Content (Text + Images)**
- Scenario: Protocol has criteria in both searchable text and embedded images
- Handling: Extract text first; for image pages, run OCR
- User experience: Smooth; user may not notice distinction
- Risk: Criteria in images might be missed if OCR fails

**EC-003: Password-Protected PDF**
- Scenario: User uploads encrypted PDF
- Handling: Backend detects encryption, rejects file
- User experience: Error message "PDF is password-protected. Please provide unencrypted version."

**EC-004: PDF with Non-English Text**
- Scenario: International protocol in French, German, or Spanish
- Handling: Claude API detects language; extraction works (Claude supports multiple languages)
- Limitation: MVP assumes English; future phases support localization
- User experience: Criteria extracted successfully; system notes language detected

**EC-005: Very Long Protocol (>200 Pages)**
- Scenario: Comprehensive protocol with extensive appendices
- Handling: Chunked extraction (pages 1-50, 51-100, 101-150, etc.)
- Timeout: Global 120 seconds; progress shown
- Risk: Criteria in appendices might be missed if extraction times out
- User experience: Progress indicator; partial results if timeout reached

**EC-006: Corrupted PDF**
- Scenario: Truncated file, bitwise corruption
- Handling: PyMuPDF or OCR fails with error
- User experience: Clear error message "PDF appears corrupted. Try downloading from source again and re-uploading."

---

### Criteria-Related Edge Cases

**EC-007: Extremely Vague Criteria**
- Scenario: "Patients must be in good health" (no specific metrics)
- Handling: Extraction captures it; screening returns INSUFFICIENT_DATA with note: "Criterion is subjective; PI judgment needed"
- Recommendation: Coordinator edits criterion to add specificity before screening

**EC-008: Contradictory Criteria**
- Scenario: "Age >65" AND "Age <60"
- Handling: Extraction captures both as written
- Screening: No patient can meet both; system flags this during review: "Criteria may be contradictory; confirm with PI"
- Resolution: Coordinator edits one criterion or adds note

**EC-009: Criteria Referencing External Documents**
- Scenario: "See Appendix B for detailed inclusion criteria" (appendix not in provided protocol text)
- Handling: Extraction notes reference but cannot extract content
- User experience: Criterion created as "See Appendix B for detailed inclusion criteria"
- Screening: Returns INSUFFICIENT_DATA for any criteria depending on appendix content
- Resolution: Coordinator must manually add criteria from appendix

**EC-010: Duplicate Criteria**
- Scenario: Same criterion stated twice in protocol (e.g., "HbA1c <8%" and "HbA1c must be below 8%")
- Handling: Extraction may capture both; coordinator sees duplicates and deletes one

**EC-011: Criteria with Temporal Conditions**
- Scenario: "Diagnosed with diabetes within last 5 years"
- Handling: Extraction captures temporal logic
- Screening: If patient summary doesn't include diagnosis date, returns INSUFFICIENT_DATA: "Diagnosis date needed to verify 5-year window"
- Patient data: Coordinator must provide "Diagnosed: 2021" or "HbA1c first detected: March 2021"

**EC-012: Implicit Criteria**
- Scenario: Protocol describes "target population: Type 2 Diabetes patients"; no explicit criterion "Must have Type 2 Diabetes"
- Handling: Extraction may or may not pick this up (depends on LLM inference)
- Solution: Coordinator manually adds explicit inclusion criterion if extraction misses it

---

### Patient Data Edge Cases

**EC-013: Patient Summary with Missing Key Data**
- Scenario: User enters only "Age 55, Type 2 Diabetes" (no lab values, meds, comorbidities)
- Handling: Screening proceeds; many criteria return INSUFFICIENT_DATA
- User experience: Long missing data list shown
- Recommendation: Coordinator goes back and adds more patient information from chart

**EC-014: Contradictory Patient Data**
- Scenario: "HbA1c 8.2% (2 weeks ago) ... Currently well-controlled on Metformin" (tension between A1c and description)
- Handling: System reports both data points; coordinator and LLM assess together
- Reasoning: "Patient's HbA1c of 8.2% suggests suboptimal control; medication claim may be aspirational"

**EC-015: Patient with Implausible Values**
- Scenario: "Age 120, BMI 85, eGFR 200"
- Handling: System does not validate clinical plausibility; reports as stated
- Risk: LLM may flag as unusual in reasoning ("implausibly high eGFR for age 120; verify data")
- Recommendation: Coordinator responsible for data quality

**EC-016: Patient on Multiple Conflicting Medications**
- Scenario: "Metformin 1000 BID, Lisinopril 20, Insulin 50 units TID" (polypharmacy)
- Handling: System processes all medications; screening evaluates against medication criteria
- Example: If criterion is "NOT on Insulin", patient flagged as DOES_NOT_MEET

**EC-017: Deceased Patient**
- Scenario: Coordinator enters "Patient deceased 2023"
- Handling: System processes as-is (no vital status field in structured form)
- Recommendation: UI prevents screening of deceased patient; shows warning if summary contains "deceased" keyword

---

### Screening Result Edge Cases

**EC-018: Patient Meets All Criteria**
- Scenario: Perfect match; all criteria MEETS
- Outcome: ELIGIBLE with high confidence
- Coordinator action: Can still export report; final enrollment decision by PI

**EC-019: Patient Fails One Criterion, Passes All Others**
- Scenario: 24 inclusion criteria met, 1 failed (e.g., age 72 but max is 70); no exclusion criteria triggered
- Outcome: NOT ELIGIBLE
- Coordinator action: Report exported with clear reason for ineligibility

**EC-020: Multiple Simultaneous INSUFFICIENT_DATA**
- Scenario: 8 criteria missing data (e.g., recent labs, imaging, procedure dates all absent)
- Outcome: REQUIRES_REVIEW; missing data list spans entire page
- Coordinator action: Decide whether to contact study site for more data or proceed to next patient

**EC-021: Low Confidence Across-the-Board**
- Scenario: Ambiguous protocol, minimal patient data; all assessments return medium/low confidence
- Outcome: Overall status still calculated (ELIGIBLE/NOT_ELIGIBLE/REQUIRES_REVIEW) but with caveat
- Coordinator action: Escalate to PI for review before enrollment

**EC-022: Confidence Mismatch (High Confidence DOES_NOT_MEET, but seems like error)**
- Scenario: Criterion "HbA1c <8%", patient HbA1c 8.1%, LLM returns DOES_NOT_MEET, high confidence
- Coordinator action: Can override to INSUFFICIENT_DATA if 8.1% vs 8% seems like margin of error

---

### System/Infrastructure Edge Cases

**EC-023: API Rate Limit Hit**
- Scenario: 100 requests in 1 hour limit exceeded
- Handling: 429 Too Many Requests response
- User experience: Error message "System busy; please try again later"
- Recovery: Clear data, start new session (new session ID = new rate limit bucket)

**EC-024: Claude API Timeout**
- Scenario: API call takes >60 seconds (unusual but possible)
- Handling: Backend timeout triggers; LLM call abandoned
- User experience: Error message "Extraction took too long; please try a shorter protocol"
- Recovery: Retry with shorter/chunked protocol

**EC-025: S3 Upload Failure**
- Scenario: AWS S3 temporarily unavailable
- Handling: Upload fails after 3 retry attempts
- User experience: Error message "Upload failed; please check connection and try again"
- Recovery: User retries upload

**EC-026: Session Timeout During Active Work**
- Scenario: Coordinator leaves screen for 30+ minutes during extraction
- Handling: Session cleared; data lost
- User experience: Redirect to home page with message "Your session expired. Please start over."
- Recovery: Restart workflow (re-upload PDF, etc.)

**EC-027: Browser Crashes During Report Export**
- Scenario: Browser crashed while PDF generating
- Handling: PDF generation in progress on backend; abandoned after timeout
- User experience: User returns to app; previous results still in session (session not lost)
- Recovery: Re-export report

**EC-028: Very Large Report (1000+ Criteria)**
- Scenario: Massive trial with extensive criteria
- Handling: PDF generation still works but may take 15 seconds
- PDF size: Could exceed 5 MB limit
- Recommendation: PDF generation tested up to 100 criteria; beyond that untested

---

### Compliance/Data Handling Edge Cases

**EC-029: Coordinator Accidentally Pastes Full Medical Record (with PHI)**
- Scenario: EHR copy-paste includes patient name, MRN, DOB
- Handling: PII detection triggered; warning shown
- User experience: "Please remove identifiable information: name, MRN, DOB detected. Screening cannot proceed until removed."
- Recovery: Coordinator manually removes PII and retries

**EC-030: Coordinator Requests Download of Screening for External Party**
- Scenario: Coordinator wants to email PDF to sponsor/regulatory
- Handling: No problem; tool generates PDF, user responsible for distribution
- Limitation: Tool does not send email; user manages distribution and redaction

**EC-031: Session Data Accessed by Unauthorized Person**
- Scenario: Coordinator steps away; another person at same computer accesses same browser
- Handling: Session ID stored in HTTP-only cookie; new person has full access to active session
- Recommendation: Coordinator should log out before stepping away (not automatic)
- Mitigation: Clear visual logout button; warning at 5-minute mark before timeout

---

## Glossary of Clinical and Technical Terms

### Clinical Terms

**Comorbidities:** Pre-existing medical conditions in addition to the primary diagnosis being studied (e.g., hypertension in a diabetes trial).

**Diagnosis Code:** Standardized medical coding system (ICD-10-CM in US) to classify diseases and health conditions.

**Exclusion Criterion:** A characteristic that disqualifies a patient from enrollment; any patient meeting an exclusion criterion cannot enroll.

**eGFR (Estimated Glomerular Filtration Rate):** Measure of kidney function; used to assess renal eligibility for trials involving nephrotoxic drugs.

**HbA1c (Hemoglobin A1c):** Blood test measuring average glucose over 3 months; primary diabetes control metric.

**Inclusion Criterion:** A characteristic required for enrollment; patient must meet all inclusion criteria to be eligible.

**LVEF (Left Ventricular Ejection Fraction):** Percentage of blood pumped out of heart's left ventricle; key measure in cardiac trials.

**Medical History:** Record of past illnesses, surgeries, treatments, and health events.

**Prior Therapy:** Previous treatments received (medications, radiation, chemotherapy, surgery) before entering trial.

**Protocol:** Official document describing trial objectives, methodology, inclusion/exclusion criteria, and procedures; read and followed by all study sites.

**Study Coordinator / Clinical Research Associate (CRA):** Person who recruits patients, obtains informed consent, and manages patient care in clinical trial.

**Principal Investigator (PI):** Physician overseeing trial at a specific research site; has final authority for enrollment decisions.

**Temporal Condition:** Criterion involving timing (e.g., "diagnosed within last 6 months"; "no surgery within 30 days").

---

### Technical Terms

**API (Application Programming Interface):** Interface allowing frontend and backend to communicate; defines requests and responses.

**Asynchronous Processing:** Work that happens in background without blocking user (e.g., extraction task).

**Confidence Score:** Metric (high/medium/low) indicating how certain the system is in a screening assessment.

**Claude API:** Anthropic's language model API providing access to Claude LLM for text generation.

**De-Identification:** Process of removing or masking personally identifiable information from data.

**Endpoint:** Specific API route (URL) that accepts requests and returns responses (e.g., `/api/extract-criteria`).

**FHIR (Fast Healthcare Interoperability Resources):** Standard for healthcare data exchange; used in EHR integrations (Phase 3+).

**HTTP-Only Cookie:** Cookie inaccessible to JavaScript; more secure than localStorage for session tokens.

**LLM (Large Language Model):** Neural network trained on vast text data; Claude is an LLM.

**Natural Language Processing (NLP):** AI techniques for understanding human language; extraction and screening use NLP.

**OCR (Optical Character Recognition):** Technology to extract text from images (e.g., scanned PDFs).

**Payload:** Data sent in request body (e.g., patient summary in screening request).

**Rate Limiting:** Restriction on number of API requests per time period (e.g., 100 per hour).

**S3 (Simple Storage Service):** AWS cloud storage service for files and objects.

**Schema:** Structure defining required and optional fields in request/response (e.g., CriterionModel schema).

**Session:** Stateful interaction between user and application; persists data during user's workflow.

**Token (LLM context):** Unit of text for LLM; roughly 1 token = 4 characters; Claude has token limits per request.

**Validation:** Process of checking data against rules before processing (e.g., file type validation).

---

## Sign-Off

| Role | Name | Date | Signature |
|------|------|------|-----------|
| Product Manager | [PM Name] | 2026-03-24 | — |
| Engineering Lead | [Eng Lead] | 2026-03-24 | — |
| QA Lead | [QA Lead] | 2026-03-24 | — |
| Compliance/Legal | [Compliance] | 2026-03-24 | — |

---

**END OF SYSTEM REQUIREMENTS DOCUMENT**
