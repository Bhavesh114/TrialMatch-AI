# User Guide for Study Coordinators
## TrialMatch AI — Clinical Trial Eligibility Screener

**Document Version:** 1.0
**Last Updated:** 2026-03-24
**Status:** Final - MVP v1.0
**Audience:** Study coordinators, clinical research associates, trial personnel

---

## Introduction

Welcome to TrialMatch AI, your clinical trial eligibility screening assistant. This guide walks you through using the tool to screen patients faster while maintaining accuracy.

### What TrialMatch Does

TrialMatch AI helps you:
- **Quickly extract** eligibility criteria from trial protocol PDFs
- **Automatically screen** patients against those criteria
- **Clearly show** why patients are eligible or ineligible
- **Generate audit-ready reports** for your records

### What TrialMatch Does NOT Do

- **Does not make enrollment decisions.** You and your PI make final enrollment choices.
- **Is not a diagnostic tool.** It reads patient data you provide; it does not diagnose or assess medical conditions.
- **Does not replace clinical judgment.** Whenever the tool says "needs more information," you or your PI must decide how to proceed.
- **Does not store patient data.** Your patient information is processed and then deleted; we do not keep copies.

### Important Disclaimer

**TrialMatch AI is a decision support tool only.** All screening results must be verified and approved by you (the Study Coordinator) and your Principal Investigator before patient enrollment. This tool is designed to save you time, not to replace your clinical expertise and governance.

---

## Getting Started: Step-by-Step Walkthrough

### Step 1: Upload Your Trial Protocol PDF

**What You'll See:**
- A large upload area with "Choose File" button
- Example text showing what kind of file to upload
- Instructions: "Upload your trial protocol PDF"

**What To Do:**
1. Click the upload area or "Choose File" button
2. Select your protocol PDF from your computer
3. The file uploads automatically (no "Submit" button needed)
4. You'll see a progress bar while uploading

**Expected Outcomes:**
- ✅ **Success:** File uploads, you see a list of extracted criteria
- ❌ **File too large (>50 MB):** Error message "File exceeds 50 MB limit. Try a shorter protocol."
- ❌ **Wrong file type:** Error message "File must be a PDF. You uploaded: [type]"
- ❌ **Corrupted file:** Error message "PDF appears corrupted. Try downloading from source again."

**Pro Tip:**
- If your protocol is very long (>100 pages), consider uploading just the relevant sections (e.g., page 1 with title and criteria page)
- This speeds up extraction and reduces errors

---

### Step 2: Review and Edit Extracted Criteria

After extraction, you'll see a list of all eligibility criteria the AI found.

**What You'll See:**
- **Inclusion criteria** (green badges) at the top
- **Exclusion criteria** (red badges) below
- Each criterion shows:
  - Criterion ID (I1, I2, E1, etc.)
  - Description (plain language)
  - Category (demographics, diagnosis, lab values, etc.)
  - Data needed (specific info required to evaluate)

**What To Do:**
1. **Scan the list** to make sure it looks complete and accurate
2. **Edit criteria if needed:**
   - Click a criterion to edit its description, logic, or data points
   - Fix any AI mistakes (e.g., AI said "HbA1c <8%" but protocol says "<8.5%")
3. **Delete criteria if wrong:**
   - Click delete (trash icon) to remove a criterion the AI misread
4. **Add missing criteria:**
   - Click "Add New Criterion" and manually type it in
   - (Happens if AI missed something subtle)
5. **Click Next** to proceed to patient screening

**What NOT To Do:**
- Do not worry about perfect wording; AI just extracted it from the PDF
- Do not edit the criterion ID (system manages these)
- Do not add clinical interpretation; stick to what the protocol actually says

**Red Flags to Watch For:**
- **Missing criteria:** If protocol says "No active cancer" but list is silent on cancer, add this manually
- **Vague extraction:** If AI extracted "Good renal function" (too vague), edit to be more specific if protocol allows
- **Duplicate criteria:** If same criterion extracted twice, delete one copy

**Example Edit:**

Protocol says: "HbA1c between 7.0% and 8.5% at screening"
AI extracted: "HbA1c between 7.0% and 8.0%"
Action: Click the criterion, edit upper limit from 8.0% to 8.5%, click Save

---

### Step 3: Prepare and Input Patient Data

Now you'll input patient information for screening against the criteria.

**Two Ways To Enter Patient Data:**

**Option A: Free-Text (Paste Clinical Notes)**
- Best if: You have a clinical note you can copy-paste
- How: Click "Free Text" tab, paste notes from patient chart
- Format: Any style is okay; coordinates don't need to reformat
- Example:
  ```
  55-year-old female. Diagnosis: Type 2 Diabetes, diagnosed 2019.
  Most recent HbA1c: 8.2% (March 2024).
  BMI: 31.4. Medications: Metformin 1000mg twice daily, Lisinopril 10mg daily.
  Comorbidities: Hypertension (well-controlled), mild osteoarthritis.
  No history of cardiovascular disease or cancer.
  Not pregnant, no plans for pregnancy.
  Allergy: Penicillin.
  ```

**Option B: Structured Form (Fill Fields)**
- Best if: You don't have a note readily available
- How: Click "Structured Form" tab, fill in available fields
- Fields include:
  - Age (required)
  - Sex (Male / Female / Other)
  - Primary diagnosis
  - Secondary diagnoses
  - Current medications
  - Lab values (with dates)
  - Comorbidities (checkboxes)
  - Functional status
  - Procedures/surgeries
  - Allergies
  - Pregnancy status
  - Additional notes

**Important Data Entry Rules:**

1. **Be Thorough:** The more information you provide, the better the screening
2. **Be De-Identified:** NO patient names, MRN, dates of birth, or social security numbers
   - Use age instead of DOB
   - Do not include patient ID or medical record number
   - Skip phone numbers and addresses
3. **Be Specific:** Not "high blood pressure" but "Hypertension, on Lisinopril 10mg daily"
4. **Include Dates When Relevant:** "HbA1c 8.2% (March 2024)" better than "Recent HbA1c 8.2%"

**What Happens If You Include PII:**
- You'll see a warning: "Patient summary appears to contain identifiable information (name, MRN, DOB). Remove this before screening."
- This is a safety feature
- Remove the PII and try again; we do not store it

**After Entering Data:**
1. Review the summary to make sure it looks correct
2. Click "Screen Patient" button
3. Wait 10-20 seconds while AI evaluates patient against criteria

---

### Step 4: Review Screening Results

The AI returns a screening report showing eligibility determination and reason.

**What You'll See:**

**Top Section (Big Status):**
- Large colored badge showing: **ELIGIBLE** / **NOT ELIGIBLE** / **REQUIRES REVIEW**
- Below that: Count of criteria met, not met, and with insufficient data
- If not eligible: The top reason for ineligibility

**Middle Section (Detailed Breakdown):**
- Table showing each criterion with:
  - Criterion name (e.g., "Age 18-75 years")
  - Status badge (green=MEETS, red=DOES_NOT_MEET, yellow=INSUFFICIENT_DATA)
  - Confidence level (High, Medium, Low)
  - Reasoning (short explanation citing patient data)
  - Missing data (if applicable; what information is needed)

**Bottom Section (Missing Data Summary):**
- If any criteria returned INSUFFICIENT_DATA, you'll see:
  - What specific data is needed
  - Which criteria require that data
  - Suggested follow-up questions

**Understanding the Three Status Values:**

| Status | Meaning | Example | What To Do |
|--------|---------|---------|-----------|
| **MEETS** | Patient clearly satisfies criterion | Age 55 within range 18-75 | Proceed to next criterion |
| **DOES_NOT_MEET** | Patient clearly fails criterion | HbA1c 8.2% exceeds limit of 8.0% | Flag for PI discussion; likely ineligible |
| **INSUFFICIENT_DATA** | Data missing; cannot determine | No HbA1c provided | Coordinator must get more information from chart, then re-screen |

**Understanding Confidence Levels:**

| Confidence | Meaning | Example |
|---|---|---|
| **HIGH** | Clear criterion + complete patient data | Criterion: "Age 18-75". Patient: Age 55. → Clear determination. |
| **MEDIUM** | Criterion is clear but data incomplete, OR criterion ambiguous but data complete | Criterion: "Good renal function". Patient: eGFR 72. → Data provided but criterion vague. Coordinator judgment needed. |
| **LOW** | Both criterion and patient data are ambiguous | Criterion: "Stable disease" (no definition). Patient: "No recent treatment" (unclear what "recent" means). → Needs PI clarification. |

**Overall Eligibility Decision Rules:**

| Overall Status | Meaning |
|---|---|
| **ELIGIBLE** | ALL inclusion criteria MEET, NONE of the exclusion criteria triggered (no DOES_NOT_MEET), AND no INSUFFICIENT_DATA for inclusion criteria |
| **NOT_ELIGIBLE** | At least ONE inclusion criterion DOES_NOT_MEET, OR at least ONE exclusion criterion is triggered |
| **REQUIRES_REVIEW** | At least one criterion returned INSUFFICIENT_DATA (regardless of other results). Coordinator must investigate before final decision. |

---

### Step 5: Export and File the Screening Report

Once satisfied with results, export a PDF report for your records.

**What To Do:**
1. Click "Download PDF Report" button
2. A PDF file downloads automatically to your computer
   - Filename: `TrialMatch_Screening_[TRIAL_ID]_[DATE].pdf`
   - Example: `TrialMatch_Screening_NCT05123456_2026-03-24.pdf`
3. Save or file the report as needed (email to PI, attach to patient chart, etc.)

**What's In The Report:**
- Protocol title, version, NCT number, sponsor
- Screening date and time
- De-identified patient summary (as you entered it)
- Overall eligibility determination
- Per-criterion assessment table (criterion, status, reasoning, confidence)
- Missing data list (if any)
- **Important disclaimer:** "This screening is for efficiency support only and does NOT replace clinical judgment. All determinations must be verified by Study Coordinator and Principal Investigator."
- Footer with generation timestamp

**Important:**
- The report contains NO patient identifiers (no names, MRN, DOB)
- This is intentional; you are responsible for any re-identification if needed for your records
- The report is a decision support tool, not a clinical decision
- Your PI must still review and approve enrollment

**What To Do With The Report:**
- ✅ File with trial records (as support for screening decision)
- ✅ Email to PI for review/approval
- ✅ Include in patient screening documentation
- ❌ Do NOT treat as final enrollment decision without PI sign-off
- ❌ Do NOT submit to regulatory agencies as clinical documentation

---

## Common Scenarios and Troubleshooting

### Scenario 1: Patient Clearly Eligible (All Criteria Met)

**Example:**
- Overall Status: **ELIGIBLE** (green badge)
- All criteria show green "MEETS" badges

**What To Do:**
1. Review the criteria briefly to make sure AI didn't miss anything obvious
2. Export the PDF report
3. Discuss with your PI if needed
4. Proceed with enrollment if PI agrees and all regulatory steps are complete
5. Document screening decision in trial records

---

### Scenario 2: Patient Clearly Ineligible (Fails Inclusion or Exclusion Criterion)

**Example:**
- Overall Status: **NOT ELIGIBLE** (red badge)
- Criterion I3 shows red "DOES_NOT_MEET": "HbA1c <8.0%" but patient HbA1c is 8.2%

**What To Do:**
1. Review the specific reason (shown in red badge reasoning)
2. **Discuss with PI:** Does PI want to override? Is the 0.2% difference clinically acceptable?
   - Most protocols are strict; 8.2% vs 8.0% likely means ineligible
   - But PI may have clinical judgment to override
3. **If PI agrees with AI:** Do not enroll; screen next patient
4. **If PI disagrees with AI:** Update the reasoning in the screening report manually, get PI sign-off, and proceed with enrollment
5. Export and file report with your decision

---

### Scenario 3: Insufficient Data (Missing Key Information)

**Example:**
- Overall Status: **REQUIRES_REVIEW** (yellow badge)
- Criterion I3 shows yellow "INSUFFICIENT_DATA": "Most recent HbA1c needed"
- Missing Data Summary shows: "HbA1c value from last 3 months (required by criteria I3, E1)"

**What To Do:**
1. **Get the missing data from the patient chart:**
   - Log into EHR
   - Pull patient's recent labs
   - Find HbA1c result (should be <3 months old per protocol)
2. **Update patient summary:**
   - Go back to patient input page
   - Re-enter the summary with the new HbA1c value
   - Click "Screen Patient" again
3. **Re-run screening:** Now the results should show complete determination (ELIGIBLE or NOT_ELIGIBLE)
4. **Export final report** after re-screening

**Pro Tip:**
- If you cannot find the missing data, discuss with patient or treatment team
- Some patients may not have recent labs; you might need to order them
- Document the reason if data was not available (e.g., "Patient has not had labs in 6 months; awaiting order")

---

### Scenario 4: Ambiguous Criterion Needs Interpretation

**Example:**
- Criterion says: "Hemodynamically stable"
- Patient data: "No recent hospitalizations; on stable medications"
- AI returns INSUFFICIENT_DATA: "Hemodynamically stable is not defined. Specific vital signs or echocardiography assessment needed."

**What To Do:**
1. **Clarify with PI:** Ask the PI: "Does 'hemodynamically stable' mean specific vital signs, ejection fraction, or clinical judgment?"
2. **Get additional patient data if needed:** Order echo, BP, heart rate, etc.
3. **Re-enter and re-screen** once you have the information PI wants
4. **Document the interpretation** (add note: "PI confirmed patient is hemodynamically stable based on [specific data]")

---

### Scenario 5: AI Made a Mistake in Extraction

**Example:**
- Protocol says: "HbA1c <8.5%"
- AI extracted: "HbA1c <8.0%"
- You caught it during criteria review

**What To Do:**
1. On the Extract page (before you screened any patients):
   - Click the criterion to edit
   - Change "8.0%" to "8.5%"
   - Save
2. Proceed to screening
3. Results will now use the correct threshold

---

## Frequently Asked Questions (FAQ)

### Q1: Can I screen multiple patients at once?

**A:** Not in this version. TrialMatch MVP screens one patient per trial per session. To screen multiple patients:
1. Screen Patient 1 → Export report
2. Start new session (refresh browser)
3. Upload protocol again, review criteria (they're in cache, so fast)
4. Screen Patient 2 → Export report
5. Repeat for each patient

(Future versions may support batch screening.)

---

### Q2: What if my protocol doesn't have numbered inclusion/exclusion sections?

**A:** TrialMatch still works! The AI extracts all criteria it finds, regardless of formatting. You may need to:
1. Review extracted criteria carefully to ensure none were missed
2. Add manually any criteria buried in study description
3. Edit descriptions to match your protocol's exact wording (helpful for documentation)

---

### Q3: Can I save my screening progress and come back to it later?

**A:** Your current screening session is saved as long as you stay in the app. If you:
- Close the browser tab → Session lost (data cleared)
- Refresh the page → Session persists (try it!)
- Come back tomorrow → Session lost (timeout after 30 minutes of inactivity)

**To preserve work:** Export the PDF report before closing the app.

---

### Q4: What if I disagree with the AI's assessment?

**A:** You can:
1. **Override the result:** Click the criterion, manually change status/reasoning, and document your change
2. **Export the report** showing your override
3. **Discuss with PI** if the override is clinically significant

Example:
- AI says DOES_NOT_MEET (HbA1c 8.1% vs limit 8.0%)
- You and PI agree 8.1% is clinically acceptable
- Change status to MEETS, add reasoning: "PI approved: 8.1% HbA1c within acceptable range given [clinical reason]"
- Export report with this override documented

---

### Q5: Is my patient data secure? Will TrialMatch store it?

**A:** No, your data is not stored. Here's what happens:
1. You paste/enter patient data
2. AI evaluates it for screening
3. Results shown to you
4. You close session or browser
5. All patient data is deleted
6. No copies remain on our servers

We do NOT:
- Save patient data to a database
- Email patient data anywhere
- Keep copies for future use
- Share patient data with anyone

(Data is only in your session, and only for as long as you're using the app.)

---

### Q6: What does "data point needed" mean?

**A:** When you see "Missing Data: Recent HbA1c value (within last 3 months)", this means:
- The AI could not find this specific data in the patient summary you entered
- To properly screen this criterion, you need to provide this specific data
- Example: You said "HbA1c is high" but didn't give the exact number; AI needs the exact number to compare against the criterion threshold

**How to fix:** Go back to patient input, add the specific data point, re-screen.

---

### Q7: Can I use TrialMatch for patients who don't speak English?

**A:** TrialMatch MVP requires English protocols and English patient data. If you have:
- Non-English protocol: Translate to English first, then upload
- Non-English patient summary: Translate to English, then enter

(Future versions may support multiple languages.)

---

### Q8: What if I need to screen a patient but don't have complete information?

**A:** Do your best with available information:
1. Enter what you have (age, diagnosis, available labs)
2. Run screening
3. You'll see INSUFFICIENT_DATA for any missing criteria
4. Coordinator work: Get the missing data, re-screen
5. Document the gaps (e.g., "Patient labs pending; screened with available data on [date], to be updated when labs available")

---

### Q9: Can I use TrialMatch for regulatory submissions?

**A:** No. TrialMatch is decision support, not a regulatory document. For submissions:
1. Use TrialMatch to screen (saves time)
2. Generate your own formal screening log/documentation
3. File with protocol and trial records per your regulatory requirements
4. TrialMatch report can be supporting documentation but is not the primary record

---

### Q10: What if the AI seems to have "hallucinated" criteria that aren't in the protocol?

**A:** This can happen (LLMs sometimes infer things not explicitly stated). Mitigation:
1. During criteria review, compare each extracted criterion to the PDF
2. Delete any criteria you cannot find in the protocol text
3. Report this to your study team (may indicate a protocol that needs clarification)

---

## Glossary of Clinical and Tool Terms

**Clinical Terms:**

| Term | Definition |
|---|---|
| **Comorbidity** | A medical condition a patient has in addition to the main disease being studied |
| **Diagnosis** | Medical condition or disease |
| **Exclusion Criterion** | A characteristic that makes a patient ineligible for the trial |
| **eGFR** | Estimated kidney function (normal: >60 mL/min) |
| **HbA1c** | Blood glucose control measure for diabetes (lower is better; <8% is typical target) |
| **Inclusion Criterion** | A characteristic required for enrollment |
| **Lab Values** | Results from blood tests, imaging, or other measurements |
| **Medical History** | Patient's past illnesses, surgeries, treatments |
| **Onset** | When a condition started |
| **Prior Therapy** | Treatments patient has received in the past |

**TrialMatch Terms:**

| Term | Definition |
|---|---|
| **Criterion ID** | Label for each criterion (I1, I2, E1, E2, etc.) |
| **De-identified** | Patient information with names, MRN, DOB removed (just age, diagnosis, etc.) |
| **DOES_NOT_MEET** | Patient clearly fails this criterion |
| **Extraction** | Process of pulling criteria from the protocol PDF |
| **INSUFFICIENT_DATA** | Missing information; cannot determine if criterion is met |
| **MEETS** | Patient clearly satisfies this criterion |
| **Screening** | Process of evaluating patient against criteria |

---

## Tips and Best Practices

### 1. Protocol Preparation
- Use the most recent protocol version (check version number)
- If protocol is very long, consider uploading key pages (cover page + criteria pages)
- If protocol is scanned, ensure good image quality (clear text)

### 2. Patient Data Entry
- Include dates for time-dependent criteria (diagnosis date, lab dates)
- Use clinical terminology (HbA1c not "blood sugar", eGFR not "kidney function")
- Be specific: "Metformin 1000mg twice daily" better than "on diabetes meds"
- Include units for lab values: "HbA1c 8.2%" not just "8.2"

### 3. Results Review
- Always verify AI reasoning makes sense
- If you see LOW confidence, consider asking PI before proceeding
- Do not assume MEETS means the patient should be enrolled; always get PI approval
- If NOT_ELIGIBLE, check if PI wants to override or exclude

### 4. Documentation
- Always export and file the screening report
- If you override AI decision, document why in the report or in trial records
- Keep reports organized (by date, by trial, by patient if needed)
- Maintain a screening log showing which patients were screened and outcomes

### 5. When to Escalate to PI
- Overall status is REQUIRES_REVIEW (missing data)
- Criterion is ambiguous (unclear how to interpret)
- You disagree with AI assessment
- Patient is borderline (barely meets or barely fails criteria)

---

## Troubleshooting Common Issues

### Issue: "File too large" error

**Cause:** Protocol PDF exceeds 50 MB

**Solutions:**
- Use a different, smaller version of the protocol
- Extract and upload only the criteria pages (cover + inclusion/exclusion sections)
- Use OCR software to compress the PDF before uploading

---

### Issue: "Could not extract text" error

**Cause:** PDF is heavily redacted, scanned from very poor quality image, or corrupted

**Solutions:**
- Try re-downloading the protocol from source (may be a corrupted file)
- If scanned, try a higher-resolution version
- Report to study team; may need to request protocol from sponsor

---

### Issue: "Network error" or "Connection failed"

**Cause:** Internet connection dropped, or server is temporarily unavailable

**Solutions:**
- Check internet connection
- Wait a few moments and try again
- If persistent, contact your IT support or TrialMatch team

---

### Issue: Extracted criteria seem incomplete or wrong

**Cause:** AI missed some criteria or misinterpreted protocol text

**Solutions:**
- Carefully review the criteria list against the protocol PDF
- Manually add any missing criteria using "Add Criterion" button
- Edit any incorrect criteria (e.g., wrong threshold numbers)
- Contact TrialMatch team to report systematic issues (helps improve the AI)

---

### Issue: Patient screening takes too long (>30 seconds)

**Cause:** System is busy or AI is slower than usual

**Solutions:**
- Wait a bit longer (typical screening takes 10-20 seconds)
- Check internet connection
- Try again if persistent
- If repeatedly slow, contact support

---

## Contacting Support

If you encounter issues or have questions:

**Email:** support@trialmatch.app
**Include:**
- Trial ID (NCT number)
- Brief description of the issue
- Screenshot if helpful
- Patient summary (de-identified) if screening-related

---

## Sign-Off

| Role | Name | Date | Signature |
|------|------|------|-----------|
| User Experience Lead | [Name] | 2026-03-24 | — |
| Clinical Advisor | [Name] | 2026-03-24 | — |
| Training Coordinator | [Name] | 2026-03-24 | — |

---

**END OF USER GUIDE**
