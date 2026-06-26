# Compliance and Data Handling Document
## TrialMatch AI — Clinical Trial Eligibility Screener

**Document Version:** 1.0
**Last Updated:** 2026-03-24
**Status:** Final - MVP v1.0
**Audience:** Compliance officers, legal counsel, product management, security

---

## Executive Summary

TrialMatch AI is a clinical trial eligibility screening decision support tool designed to operate within strict data protection and de-identification boundaries. The MVP (Minimum Viable Product) processes only de-identified patient data and implements a session-based, no-persistence architecture that prioritizes user privacy over data retention.

**Key Compliance Posture:**
- **Not a HIPAA-covered entity** (does not meet definition of covered entity or business associate)
- **Not a diagnostic tool** (explicitly a decision support tool; not regulated as medical device in MVP scope)
- **Not subject to FDA regulations** (no clinical decision-making authority; no real-time monitoring)
- **Subject to general data privacy laws** (GDPR, CCPA if applicable based on user location)

**Data Handling Philosophy:**
- De-identified data only
- No persistent storage (session-based, in-memory)
- Temporary file cleanup (24-hour auto-delete from S3)
- User responsible for data protection; tool provides safeguards only

---

## HIPAA Boundary Analysis

### What Is HIPAA and Who Must Comply?

**HIPAA (Health Insurance Portability and Accountability Act):**
- U.S. federal law regulating protected health information (PHI)
- Applies to: Covered entities (healthcare providers, health plans, clearinghouses) and business associates (contractors handling PHI)
- Does NOT apply to: Non-healthcare entities processing general health data

### Is TrialMatch AI a HIPAA Covered Entity?

**No.** TrialMatch AI is not a healthcare provider, health plan, or healthcare clearinghouse.

**Is TrialMatch AI a HIPAA Business Associate?**

**No.** A business associate is an entity that:
1. Receives PHI from a covered entity
2. Creates, receives, maintains, or transmits PHI on behalf of the covered entity

**TrialMatch AI does neither:** Coordinators voluntarily input de-identified data into the tool; TrialMatch does not receive data from a healthcare provider, nor does it act as an agent on their behalf.

### De-Identification Requirement

**MVP Design Assumption:** All patient data input is de-identified per HIPAA Safe Harbor method.

**Safe Harbor De-Identification Standard (HIPAA):**
Remove or mask 18 specific identifiers:

| Identifier | TrialMatch Requirement |
|---|---|
| Names | NOT ALLOWED in patient summary |
| Medical record numbers | NOT ALLOWED |
| Account numbers | NOT ALLOWED |
| Social Security numbers | NOT ALLOWED |
| Plan beneficiary numbers | NOT ALLOWED |
| Dates of birth (exact) | NOT ALLOWED; use age instead |
| Dates of admission/discharge | Use year only, if needed |
| Dates of service | Use year only if necessary for time windows |
| Full phone numbers | NOT ALLOWED |
| Email addresses | NOT ALLOWED |
| Full addresses (city/state okay, street address not) | NOT ALLOWED |
| Biometric identifiers (face, fingerprints) | NOT ALLOWED |
| Full-face photographic images | NOT ALLOWED |
| Device identifiers/serial numbers | NOT ALLOWED |
| URLs | NOT ALLOWED |
| Vehicle identifiers | NOT ALLOWED |
| Insurance plan names | NOT ALLOWED |
| Any unique identifier | Use generic patient_123, case_001 if needed |

**What IS Allowed (De-Identified Data):**
- Age (use age, not DOB)
- Sex/gender (Male, Female, Other)
- Diagnosis names and codes (e.g., "Type 2 Diabetes Mellitus", "E11")
- Lab values and vital signs (e.g., HbA1c 8.2%, BP 140/90)
- Medication names and dosages (e.g., "Metformin 1000mg BID")
- Medical history (prior diagnoses, surgeries, treatments)
- Year of diagnosis (e.g., "Diagnosed 2019" is okay; "Diagnosed January 15, 2019" too specific)
- Comorbidities (e.g., "Hypertension", "Osteoarthritis")

### PII/PHI Detection in MVP

**User Warning System:**
TrialMatch detects patterns suggesting identifiable information:
```
Patterns detected and flagged:
- Names (common first/last names)
- Medical record numbers (common formats: MRN123456, 12345678, etc.)
- Exact dates of birth (YYYY-MM-DD or YYYY-MM, especially when paired with age)
- Social security numbers (XXX-XX-XXXX)
- Phone numbers (XXX-XXX-XXXX, +1 XXX XXX XXXX)
- Email addresses (@)
```

**User Action on Detection:**
1. Warning displayed: "Patient summary appears to contain identifiable information (name, MRN, DOB). Remove this before screening."
2. Screening blocked until user removes PII
3. PII not submitted to LLM or stored

**Technical Implementation:**
```python
def detect_phi(text: str) -> list[str]:
    """Detect patterns suggesting PHI in text."""
    patterns = {
        'name': r'\b[A-Z][a-z]+ [A-Z][a-z]+\b',
        'mrn': r'\b(?:MRN|MR#)[\s:]*\d{6,10}\b',
        'ssn': r'\b\d{3}-\d{2}-\d{4}\b',
        'dob': r'\b(?:DOB|Date of birth|Born)[\s:]*\d{4}-\d{2}-\d{2}\b',
        'phone': r'\b\d{3}-\d{3}-\d{4}\b',
        'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    }
    detected = []
    for pattern_name, pattern in patterns.items():
        if re.search(pattern, text):
            detected.append(pattern_name)
    return detected
```

---

## De-Identification Standards and Validation

### Safe Harbor Method (Used in MVP)

**Approach:** Remove or encrypt 18 specified identifiers + other unique identifiers

**Strengths:**
- Bright-line rule (either identifier is present or it isn't)
- No statistical assessment needed
- HIPAA explicitly accepts this method as de-identification

**Weaknesses:**
- Does not prevent re-identification if data is combined with external sources
- Example: "55-year-old female, Type 2 Diabetes, from Boston" might be re-identifiable if cross-referenced with Census/insurance databases

**TrialMatch Mitigation:** Tool operates on assumption that coordinators understand their institutional responsibility to avoid re-identification through external data linkage

### What Constitutes Re-Identification Risk?

**Re-identification Risk Factors:**
1. Combining de-identified data with external databases (census, insurance rolls)
2. Using unique combinations of characteristics (e.g., "only female >90 years old in rural county")
3. Linking with identifiable data later
4. Sharing outside organization without contracts

**TrialMatch Mitigation:**
- Encourages local use only (not sharing patient data with external parties)
- Provides disclaimers in user guide about re-identification risks
- Does not export raw patient data (reports show only de-identified summary)

---

## Data Flow Audit

### Complete Data Lifecycle

```
USER (Study Coordinator Browser)
  ↓ [Upload Protocol PDF]
AWS S3 (Temporary Storage)
  ├─ Encryption: AES-256 (server-side)
  ├─ Lifecycle: Auto-delete after 24 hours
  ├─ Versioning: Disabled
  └─ Access: Lambda only (private bucket)

Anthropic Claude API (Criteria Extraction)
  ├─ Input: Protocol text (not patient data)
  ├─ Output: Structured criteria (stored in session)
  ├─ Retention: Not stored by Anthropic (stateless API call)
  └─ Transport: HTTPS encrypted

USER [Patient Summary Input]
  ↓ [De-identified patient data]

Backend Session (In-Memory Storage)
  ├─ Duration: Session active (max 30 minutes)
  ├─ Scope: Single session, single user
  ├─ Persistence: Memory only, lost on logout/timeout
  └─ Access: No database, no disk storage

Anthropic Claude API (Screening)
  ├─ Input: Criteria + patient summary
  ├─ Output: Screening results
  ├─ Retention: Not stored
  └─ Transport: HTTPS encrypted

Backend [Report Generation]
  ├─ Input: Protocol metadata + criteria + results
  ├─ Output: PDF file (de-identified)
  ├─ Patient data: Not included in PDF
  └─ Sanitization: All identifiers removed

USER [Download PDF]
  ├─ Direct to browser
  ├─ No intermediate storage
  └─ No server-side copy retained

Session Cleanup [Logout or 30 min timeout]
  ├─ Session memory cleared
  ├─ S3 file still deleted at 24h mark
  └─ API logs: De-identified only
```

### Data Retention by Component

| Component | Data Stored | Retention | Clearance |
|---|---|---|---|
| **S3 (Protocol PDFs)** | Protocol PDFs only, not patient data | 24 hours | Auto-delete lifecycle policy |
| **Backend Memory** | Session data (criteria, patient summary, results) | Session active (~30 min) | Auto-clear on logout/timeout |
| **Anthropic API** | Not retained (stateless API) | N/A | N/A |
| **Logs (CloudWatch)** | De-identified logs (timestamps, actions, no patient data) | 30 days | Auto-rotation |
| **Audit Trail** | Trial ID, criteria version, screening decision, timestamp (no patient data) | 90 days | Periodic purge |
| **Browser Cache** | Session cookie (ID only) | Session-based | Expires with session |
| **Downloaded PDFs** | User's computer (user responsible) | User's discretion | User responsible for deletion |

---

## Session-Based Processing Model (No Persistence)

### Architectural Design Decision

**Why No Persistent Data Storage?**

Clinical trial data, even de-identified, carries regulatory and ethical sensitivities. Persistent storage creates:
1. Security liabilities (breach risk, backup/recovery complexity)
2. Data minimization concerns (retaining data beyond use)
3. Compliance burden (data retention policies, access controls)

**Session-Only Design Benefits:**
1. Minimal data footprint (only active sessions exist)
2. Automatic cleanup (session timeout = data cleared)
3. No compliance burden for stored data
4. Reduced security liability

### Session Lifecycle

```
T+0:00 - User opens TrialMatch
  → Generate session ID (128-bit random token)
  → Create session memory object
  → Set HTTP-only session cookie (30 min TTL)

T+0:05 - User uploads protocol
  → Protocol text extracted to S3 (temporary)
  → Criteria extracted to session memory
  → S3 path stored in session

T+0:15 - User enters patient summary
  → Patient summary stored in session memory
  → NOT persisted to database
  → NOT stored in logs

T+0:20 - User runs screening
  → Patient summary + criteria sent to API
  → Screening results returned
  → Results stored in session memory

T+0:25 - User exports PDF
  → Report generated from session data
  → PDF file streamed to browser (not saved server-side)
  → User downloads; becomes user's responsibility

T+0:30 - User navigates away
  → Session still active; data available if user refreshes
  → Session expires after 30 minutes of inactivity
  → Session memory cleared
  → S3 protocol file still exists (will be deleted at T+24h)

T+25:00 - S3 Cleanup
  → Protocol PDF auto-deleted from S3 (24h lifecycle)
  → No data remains on TrialMatch servers
```

### What Happens on Various Events

| Event | Session Memory | S3 Files | Cookies |
|---|---|---|---|
| **User Logout** | Cleared immediately | Still on S3 (24h delete) | Cleared |
| **Page Refresh** | Persists (RTC request re-loads) | Still on S3 | Still valid |
| **Browser Close** | Lost (no persistence) | Still on S3 | Expires |
| **Inactivity (30 min)** | Cleared (timeout) | Still on S3 (24h delete) | Expires |
| **New Protocol Upload** | Previous data cleared, new protocol loaded | Old file still exists (24h delete) | Session continues |
| **Network Interruption** | Persists if brief; cleared if timeout | Persists | Persists |

### Data Recovery Impossible

**By Design:** If user session is lost, data cannot be recovered.

**Rationale:**
- Clinical trial data is session-specific and sensitive
- Recovery functionality would require persistent storage (increases compliance burden)
- Users expected to export reports before session ends (responsible data handling)

**User Guidance:** "Always download and save your PDF report before closing the app. Session data is not recoverable."

---

## API Security Considerations

### Authentication and Authorization

**MVP Approach (Session-Based):**
- No user accounts (no login)
- Session ID = authentication token
- Generated per browser instance
- HTTP-only cookie (JavaScript cannot access)
- Secure flag (HTTPS only)
- SameSite=Strict (CSRF protection)

**Limitations:**
- No audit trail of "who" did the screening (coordinator identity not tracked)
- No authorization roles (all coordinators have full access)
- No fine-grained access control

**Production Upgrade Needed:** Phase 2+ should add:
- User accounts with login
- Audit trail (who screened whom, when)
- Role-based access control (PI vs Coordinator permissions)
- Coordinator credentials for regulatory compliance

### Data in Transit

**Transport Security:**
- HTTPS 1.2+ required (TLS encryption)
- All endpoints require HTTPS (HTTP redirects to HTTPS)
- No unencrypted data transmission

**API Request Validation:**
```
POST /api/screen-patient HTTP/1.1
Host: api.trialmatch.app
Content-Type: application/json
Connection: secure (enforced by HTTPS)

{
  "criteria": [...],
  "patient_summary": {...}
}
```

**No API Keys in MVP:**
- Session cookie used for authentication
- No long-lived API keys to compromise
- API keys used only server-side (Anthropic key, AWS credentials)

### Input Sanitization

**Frontend Sanitization:**
- HTML tags removed from text inputs
- XSS prevention: innerHTML never used for user data
- CSP headers limit script sources

**Backend Sanitization:**
```python
def sanitize_patient_summary(summary: str) -> str:
    """Remove/escape potentially harmful content."""
    # Remove HTML tags
    summary = re.sub(r'<[^>]+>', '', summary)

    # Escape special characters for logging
    summary = summary.replace('\n', '\\n')

    # Limit length
    return summary[:5000]
```

**API Response Validation:**
- JSON schema validation (Pydantic)
- Enum validation (status must be one of specific values)
- Type validation (numbers are numbers, not strings)

---

## Disclaimer Requirements

### Mandatory Disclaimer in App

**Must Display Before Screening:**

```
⚠️ IMPORTANT DISCLAIMER

TrialMatch AI is a DECISION SUPPORT TOOL ONLY. It does not make enrollment
decisions and is not a substitute for clinical judgment by the Study
Coordinator and Principal Investigator.

• All screening results must be VERIFIED and APPROVED by the Study
  Coordinator and Principal Investigator before patient enrollment.

• This tool is designed to improve efficiency; it does not replace
  regulatory and clinical oversight.

• Clinical trial eligibility decisions are the responsibility of the
  Study Team. TrialMatch provides recommendations only.

• By using this tool, you acknowledge that you understand this
  limitation and will not use these results as the sole basis for
  enrollment decisions.
```

### Mandatory Disclaimer in Exported PDF Reports

**Must Appear on Every Report:**

```
DISCLAIMER: DECISION SUPPORT TOOL, NOT CLINICAL DECISION

This screening report was generated by TrialMatch AI, a clinical trial
eligibility screener. This report is provided for EFFICIENCY SUPPORT ONLY
and does NOT constitute a clinical decision or medical judgment.

The information in this report must NOT be used as the sole basis for
patient enrollment decisions. All screening determinations must be verified
and approved by authorized clinical trial personnel (Study Coordinator and
Principal Investigator) in accordance with protocol requirements and
applicable regulations.

Generated on: [DATE/TIME]
Report ID: [UNIQUE ID]
Protocol: [TRIAL ID]

⚠️ This is not a regulatory document and should not be submitted as such.
```

### Legal Requirements Met

✅ **Transparency:** Disclaimers clearly state tool is decision support, not decision-making
✅ **Accountability:** Disclaimers shift final responsibility to coordinators and PI
✅ **Scope Limitation:** Disclaimers explain tool is not regulated medical device or diagnostic
✅ **User Acknowledgment:** UI requires user to acknowledge disclaimer before use

---

## Regulatory Classification and Scope

### Is TrialMatch AI a Medical Device?

**FDA Classification Analysis:**

| Question | Answer | Implication |
|---|---|---|
| Does it diagnose, cure, mitigate, treat, or prevent disease? | No (explicitly decision support only) | Not a medical device per FDA definition |
| Does it provide real-time patient monitoring? | No (one-time screening only) | Not subject to real-time monitoring regs |
| Does it make autonomous clinical decisions? | No (coordinator/PI decide) | Not subject to autonomous decision-making regs |
| Is it marketed as a medical device? | No | Not regulated as medical device |
| Does it process clinical trial data? | Yes (but as support, not decision-making) | Possibly subject to clinical trial regulations |

**Conclusion:** MVP is **not a regulated medical device**. However, Phase 2+ integration with EHR systems or real-time clinical decision support would trigger device classification.

### HIPAA Status

**Is TrialMatch a HIPAA Covered Entity?**
- No. Not a healthcare provider, plan, or clearinghouse.

**Is TrialMatch a HIPAA Business Associate?**
- No. Does not receive PHI from covered entities; does not act as agent on their behalf.

**Is TrialMatch Subject to HIPAA Privacy Rule?**
- No. But must respect de-identification standards if processing health data.

**Implication:** TrialMatch is not subject to HIPAA Breach Notification Rule, Security Rule, etc. However, best practices of data protection still apply (encryption, access controls, etc.).

### GDPR Compliance (If Serving EU Users)

**If coordinators or patients are in EU:**
- GDPR applies (even for U.S. company serving EU users)
- MVP design is GDPR-compliant:
  - No persistent data storage (minimal data footprint)
  - User consent via disclaimer (explicit acknowledgment required)
  - Data subject rights (users can request data be deleted; session data is already deleted)
  - Data minimization (only de-identified data processed)

**Required for GDPR:**
- Privacy Policy (describing data processing)
- Data Processing Agreement (if serving healthcare organizations)
- Data Protection Officer (recommended for healthcare data)

---

## Risk Register: Compliance Perspective

| Risk | Likelihood | Impact | Mitigation | Residual Risk |
|---|---|---|---|---|
| **Re-identification via external data linkage** | Medium | High | Coordinator training on re-ID risks; encourage local use only | Medium |
| **Coordinator inputs identifiable data despite warning** | Medium | Medium | PII detection + blocking; user must remove PII | Low |
| **Coordinator disregards disclaimer and enrolls patient based solely on AI result** | Low | High | Multiple disclaimers; emphasizes PI approval required | Medium |
| **Data breach of temporary S3 files** | Very Low | High | S3 encryption, access logging, 24h auto-delete | Very Low |
| **Session timeout during active use; user data lost** | Low | Medium | Warning at 5-min mark; encourages PDF export | Low |
| **Patient data accidentally emailed/shared by coordinator** | Low | High | Tool encourages local use; reminds user to de-identify | Medium |
| **LLM hallucination leads to missed ineligibility (false negative)** | Low | High | Prompt engineering; evaluation testing >85% accuracy; coordinator review | Low |
| **LLM hallucination leads to false positive; coordinator wastes time** | Medium | Low | Conservative bias in prompt; coordinator can override | Low |
| **API key exposure (Anthropic, AWS)** | Very Low | High | Keys in Secrets Manager, not in code; rotation policy | Very Low |
| **Unauthorized access to session (CORS, XSS, CSRF)** | Very Low | High | HTTPS only, CORS strict, CSP headers, CSRF tokens | Very Low |

---

## Recommendations for Production HIPAA Compliance (Phase 3+)

If organization plans to integrate with EHRs or process identifiable data, these are required:

### 1. Business Associate Agreement (BAA)
- If TrialMatch becomes a business associate (receives PHI from covered entities)
- BAA must be signed before any PHI is processed
- Specifies:
  - Permitted uses of PHI (screening only)
  - Data security obligations
  - Breach notification requirements
  - Data destruction timeline

### 2. Security Infrastructure

**Administrative:**
- Designate Security Officer
- Conduct Risk Assessment (NIST framework)
- Implement access controls (user accounts, audit logs)
- Security awareness training for all staff

**Physical:**
- Secure data centers (AWS responsibility)
- Access badges, cameras (for any on-prem infra)

**Technical:**
- Encryption at rest (AES-256, database encryption)
- Encryption in transit (TLS 1.2+)
- Intrusion detection systems
- Regular vulnerability scanning
- Incident response plan

### 3. Privacy Safeguards
- Detailed Privacy Notice (HIPAA Minimum Necessary)
- Consent/Authorization forms
- Limited dataset agreements (if sharing de-identified data)
- Audit controls (log access, track disclosures)

### 4. Data Retention and Destruction
- Written Data Retention Policy
- Documented destruction procedures (secure deletion, certified destruction for hardware)
- Retention schedule (e.g., "screening results retained for 7 years per regulatory requirement")

### 5. Breach Response
- Breach notification protocol (notify affected individuals, HHS, media if >500)
- Timeline: "without unreasonable delay, no later than 60 calendar days"
- Documentation requirements

### 6. Regulatory Reporting
- Annual compliance certification
- Respond to any FDA inspection (if device classification applied)
- Respond to HHS Office for Civil Rights inquiries

---

## Institutional Responsibility

### TrialMatch's Responsibility (MVP)

✅ Provide de-identification guidance and detection
✅ Operate session-based, no-persistence architecture
✅ Display disclaimers and require acknowledgment
✅ Encrypt data in transit and at rest (temporary)
✅ Auto-delete temporary files per schedule
✅ Maintain API security standards
✅ Publish privacy policy and terms of use

### Using Organization's Responsibility

✅ Ensure coordinators understand de-identification requirements
✅ Ensure coordinators understand tool is decision support, not decision
✅ Do not send identifiable data to TrialMatch (removal is coordinator responsibility)
✅ Maintain audit trail of screening decisions (TrialMatch does not)
✅ Ensure PI reviews and approves all screening results
✅ Follow institutional data protection policies
✅ Notify TrialMatch of any data concerns or suspected breaches
✅ Maintain compliance with FDA, HIPAA, institutional IRB per their obligations

### Shared Responsibility

- **Data Security:** TrialMatch encrypts; organization must secure exported PDFs
- **Data Minimization:** TrialMatch accepts only de-identified data; organization ensures de-identification
- **Regulatory Compliance:** TrialMatch designs for compliance; organization implements per their obligations

---

## Sign-Off

| Role | Name | Date | Signature |
|------|------|------|-----------|
| Chief Compliance Officer | [Name] | 2026-03-24 | — |
| Data Protection Officer | [Name] | 2026-03-24 | — |
| Legal Counsel | [Name] | 2026-03-24 | — |

---

**END OF COMPLIANCE NOTES**
