# Prompt Engineering Guide
## TrialMatch AI — Clinical Trial Eligibility Screener

**Document Version:** 1.0
**Last Updated:** 2026-03-24
**Status:** Final - MVP v1.0
**Audience:** ML engineers, prompt engineers, QA, product team

---

## Design Philosophy

### Core Principle: Transparency Over Automation

TrialMatch does not aim for full automation of clinical trial eligibility decisions. Instead, the system prioritizes:

1. **Transparency:** Every eligibility determination shows the LLM's reasoning, allowing coordinators to verify and correct
2. **Conservative Bias:** When in doubt, flag for review rather than assume (false positives > false negatives in clinical context)
3. **Auditability:** All decisions traceable to specific patient data and criterion definitions
4. **Human Oversight:** Tool is decision support; coordinators and PIs make final enrollment decisions

**Clinical Implications:**
- Missing a criterion (false negative) = patient incorrectly enrolled = regulatory/safety risk
- Flagging something as insufficient data (conservative) = coordinator does extra work but = safety
- Therefore: **If in doubt, return INSUFFICIENT_DATA**

### LLM Selection: Claude Sonnet 4

**Why Claude Sonnet 4?**
- Strong performance on structured data extraction and reasoning
- Excellent accuracy on medical terminology and clinical context
- Cost-effective for high-volume use (compared to Claude 3 Opus)
- Fast inference (5-10 seconds per call vs 15-20 for Opus)
- Good token efficiency for long protocols and detailed reasoning

**Estimated Token Usage:**
- Extraction: 12,000-15,000 tokens (input 10,000-13,000 + output 1,500-2,000)
- Screening: 3,500-5,000 tokens (input 2,500-3,500 + output 1,000-1,500)
- Cost per operation: $0.25-0.30 for extraction, $0.08-0.10 for screening

---

## Stage 1: Criteria Extraction

### Full Prompt Text

```
You are a clinical trial protocol analyst. Your task is to extract all inclusion and exclusion criteria from a clinical trial protocol document.

CRITICAL INSTRUCTIONS:

1. EXHAUSTIVENESS REQUIREMENT
   You MUST identify EVERY inclusion and exclusion criterion mentioned in the protocol.
   Missing a criterion means patients could be incorrectly enrolled into the trial—this is a serious clinical and regulatory risk.
   When in doubt, include the criterion rather than omitting it.

2. NO INFERENCE
   Do NOT infer criteria that are not explicitly stated.
   Do NOT assume implicit restrictions (e.g., do not assume pregnancy status if not mentioned).
   Extract only what is explicitly written in the protocol text.

3. COMPOUND CRITERIA AND LOGIC
   For criteria involving AND, OR, or NOT operators, capture the COMPLETE logic as written.
   Examples:
     - "Age 50-75 AND no prior chemotherapy" → logic: "Age 50-75 AND no prior chemotherapy"
     - "HbA1c <8% OR currently on insulin" → logic: "HbA1c <8% OR on insulin therapy"
     - "No history of CVD or cancer" → logic: "NOT (CVD history) AND NOT (cancer history)"

4. TEMPORAL CONDITIONS
   For criteria involving timeframes, ALWAYS include the timeframe in the logic field.
   Examples:
     - "Diagnosed within the last 6 months" → logic: "Diagnosed <6 months ago"
     - "No major surgery in the past 3 months" → logic: "No surgery within 3 months"
     - "Treatment must have ended more than 2 years ago" → logic: "Treatment ended >2 years ago"

5. AMBIGUOUS CRITERIA
   If a criterion is vague or subjective (e.g., "good renal function", "stable disease"), extract it exactly as written.
   Do NOT attempt to interpret or clarify vague criteria.
   The screening stage will handle ambiguity by returning INSUFFICIENT_DATA.

6. STRUCTURING THE OUTPUT
   For EACH criterion, provide a JSON object with these exact fields:
     - criterion_id: "I1", "I2", ... for inclusion; "E1", "E2", ... for exclusion
     - type: "inclusion" or "exclusion" (must match criterion_id prefix)
     - description: Plain language, 1-2 sentences, suitable for reading aloud
     - category: Assign to ONE of these categories:
         * "demographics" (age, sex, gender, race, location, nationality)
         * "diagnosis" (primary/secondary diagnosis, indication, disease state)
         * "lab_values" (blood tests, imaging results, vital signs, pathology)
         * "medications" (current medications, prior medications, medication classes, drug requirements)
         * "medical_history" (prior illnesses, surgeries, hospitalizations, treatments, vaccination status)
         * "procedures" (prior procedures, interventions, prior surgeries)
         * "functional_status" (performance status, ability to perform ADLs, ability to consent)
         * "other" (anything not fitting above categories)
     - data_points_needed: Array of SPECIFIC data elements needed to evaluate this criterion
         * Be concrete: ["age", "date_of_birth"] not just ["demographics"]
         * Be exhaustive: List every specific piece of information required
         * Examples:
           - Age criterion: ["age"] or ["age", "date_of_birth"]
           - HbA1c criterion: ["HbA1c_value", "HbA1c_date"]
           - Prior surgery: ["surgery_type", "surgery_date"]
     - logic: String describing compound conditions, AND/OR relationships, or temporal requirements
         * NULL if criterion is simple and standalone
         * Example: "18 ≤ age ≤ 75 AND eGFR ≥ 60"
         * Example: "Diagnosed within 6 months of enrollment"

7. NUMBERING SCHEME
   Number inclusion criteria sequentially as I1, I2, I3, ... (do NOT skip numbers)
   Number exclusion criteria sequentially as E1, E2, E3, ... (do NOT skip numbers)
   Order them as they appear in the protocol.

8. DEDUPLICATION
   Do NOT extract the same criterion twice, even if stated differently in different sections of the protocol.
   If the same criterion appears in both inclusion and exclusion sections (e.g., "must be 18-75" and "cannot be <18 or >75"), treat as ONE inclusion criterion.

9. ERROR HANDLING
   If you encounter a criterion that references an appendix or external document you cannot read, extract the criterion as written
   and note in the description that more details are in the referenced document.
   Do NOT leave out such criteria.

OUTPUT FORMAT:
Return ONLY valid JSON. No markdown code blocks, no explanation text, no preamble.
Return a JSON array (even if empty, return []).

Example structure:
[
  {
    "criterion_id": "I1",
    "type": "inclusion",
    "description": "Patients aged 18-75 years at enrollment",
    "category": "demographics",
    "data_points_needed": ["age", "date_of_birth"],
    "logic": "18 ≤ age ≤ 75"
  },
  {
    "criterion_id": "E1",
    "type": "exclusion",
    "description": "Pregnant or planning pregnancy during trial",
    "category": "functional_status",
    "data_points_needed": ["pregnancy_status", "plans_for_pregnancy"],
    "logic": "NOT pregnant AND NOT planning pregnancy"
  }
]

Now extract all criteria from the protocol text below.
```

### Prompt Design Decisions

**Why Exhaustiveness First:**
- Clinical trials are highly regulated. Missing a criterion can lead to enrollment of an ineligible patient, creating regulatory risk and potentially harming the patient
- Better to extract over-inclusively (coordinator will remove duplicates/errors) than under-inclusively
- Prompt explicitly states: "Missing a criterion means patients could be incorrectly enrolled"

**Why No Inference:**
- LLMs have a tendency to "fill in" reasonable but unstated restrictions
- Example: Protocol says "diabetes patients" without mentioning liver disease; LLM might infer "patients with normal liver function" which isn't stated
- Instruction "Do NOT infer criteria not explicitly stated" controls this hallucination risk

**Why Compound Logic in Plain Language:**
- Trials often have complex criteria like "Age 50-75 AND (eGFR >60 OR on dialysis)"
- Representing as string rather than JSON tree keeps extraction simple
- Screening stage interprets this logic string in context of patient data

**Why Temporal Conditions Explicit:**
- Many criteria are time-dependent: "No chemotherapy within 2 years", "Diagnosed recently"
- Temporal requirements MUST be captured so screening knows what data is needed (e.g., diagnosis date)
- Example: "Recent HbA1c" means nothing without knowing what "recent" is

**Why Specific data_points_needed:**
- During screening, if data point is missing, user knows exactly what to look for
- "HbA1c_value" and "HbA1c_date" is more helpful than just "lab_values"
- Coordinator can go fetch exact information from chart

**Why Category Assignment:**
- Helps coordinator organize and review criteria by type
- Aids in finding related criteria (e.g., all lab criteria)
- Useful for future features (filtering, analytics)

---

### Known Failure Modes and Mitigations

| Failure Mode | Example | Mitigation |
|---|---|---|
| **Over-inference** | Protocol: "diabetes patients". LLM infers: "HbA1c <10%". | Instruction: "Do NOT infer criteria not explicitly stated." |
| **Missing compound logic** | Protocol: "Age 50-75 AND no prior chemo". Extraction: I1="Age 50-75", I2="No prior chemo" (loses AND). | Instruction: "Capture COMPLETE logic including AND/OR." |
| **Temporal ambiguity** | Protocol: "Recent diagnosis". Extraction: logic="null" (no timeframe). | Instruction: "Always include timeframe in logic field." |
| **Double extraction** | Criterion stated twice differently in protocol. | Instruction: "Do NOT extract same criterion twice... if same criterion appears in multiple sections, treat as ONE." |
| **Vague criteria misinterpreted** | Protocol: "good renal function". LLM translates: "eGFR >80". | Instruction: "Extract exactly as written... screening will return INSUFFICIENT_DATA for ambiguous criteria." |
| **Category mismatch** | "Age 50 and has diabetes" assigned to "diagnosis" instead of mixed. | Instruction: "Assign to ONE category; if mixed, choose primary category (age → demographics)." |
| **Appendix reference lost** | Protocol: "See Appendix B for inclusion criteria". Extraction: skipped. | Instruction: "Extract criterion as written... note in description that more details are in referenced document." |

---

### Edge Case Handling: Real Protocol Examples

**Edge Case 1: Complex Temporal Criterion**

Protocol text:
> "Patients must have a diagnosis of type 2 diabetes mellitus confirmed by a fasting plasma glucose (FPG) ≥126 mg/dL or HbA1c ≥6.5% on at least two separate occasions within 12 months prior to screening."

Extraction:
```json
{
  "criterion_id": "I1",
  "type": "inclusion",
  "description": "Type 2 diabetes confirmed by FPG ≥126 mg/dL or HbA1c ≥6.5% on at least two separate occasions within 12 months prior to screening",
  "category": "diagnosis",
  "data_points_needed": [
    "fasting_plasma_glucose",
    "HbA1c",
    "date_of_first_test",
    "date_of_second_test"
  ],
  "logic": "(FPG ≥126 OR HbA1c ≥6.5%) on ≥2 occasions within 12 months of screening"
}
```

**Edge Case 2: Implicit AND Logic**

Protocol text:
> "Inclusion Criteria:
> 1. Adult male or female patients (≥18 years of age)
> 2. Confirmed diagnosis of Type 2 Diabetes Mellitus
> 3. Stable on current antidiabetic therapy for at least 12 weeks"

Extraction:
```json
[
  {
    "criterion_id": "I1",
    "type": "inclusion",
    "description": "Age 18 years or older",
    "category": "demographics",
    "data_points_needed": ["age", "date_of_birth"],
    "logic": "age ≥18"
  },
  {
    "criterion_id": "I2",
    "type": "inclusion",
    "description": "Confirmed diagnosis of Type 2 Diabetes Mellitus",
    "category": "diagnosis",
    "data_points_needed": ["diabetes_type", "diagnosis_confirmation_method"],
    "logic": null
  },
  {
    "criterion_id": "I3",
    "type": "inclusion",
    "description": "Stable on current antidiabetic therapy for at least 12 weeks",
    "category": "medications",
    "data_points_needed": [
      "current_antidiabetic_medication",
      "medication_start_date",
      "stability_confirmation"
    ],
    "logic": "On same diabetes medication ≥12 weeks"
  }
]
```

Note: Listed separately (I1, I2, I3) because they are listed separately in protocol. During screening, ALL must be true to meet inclusion (implicit AND).

**Edge Case 3: Criterion Referencing Appendix**

Protocol text:
> "Inclusion criteria are listed in Appendix A."

Extraction:
```json
[
  {
    "criterion_id": "I1",
    "type": "inclusion",
    "description": "See Appendix A for full list of inclusion criteria (not accessible in extracted text)",
    "category": "other",
    "data_points_needed": [],
    "logic": null
  }
]
```

Coordinator will see this and know to manually add criteria from Appendix A.

---

### Output Schema and Validation

**Valid Extraction Response:**

```json
{
  "extraction_successful": true,
  "criteria": [
    {
      "criterion_id": "I1",
      "type": "inclusion",
      "description": "...",
      "category": "demographics",
      "data_points_needed": [...],
      "logic": "..."
    }
  ],
  "extraction_metadata": {
    "total_inclusion_criteria": 5,
    "total_exclusion_criteria": 4,
    "extraction_confidence": 0.95
  }
}
```

**Validation Rules (Backend):**
- criterion_id format: `[IE]\d+` (I1, E2, etc.)
- type must match criterion_id prefix (I* → inclusion, E* → exclusion)
- description not empty, <500 characters
- category must be one of 8 allowed categories
- data_points_needed is array (can be empty, but should be non-empty for evaluable criteria)
- logic can be null or non-empty string

---

## Stage 2: Patient Screening

### Full Prompt Text

```
You are a clinical research screening assistant. Your task is to evaluate whether a patient meets, does not meet, or has insufficient data for eligibility criteria in a clinical trial.

CRITICAL PRINCIPLES:

1. CONSERVATIVE BIAS: IF IN DOUBT, RETURN INSUFFICIENT_DATA
   Clinical trial enrollment must be conservative. It is better to flag a case for coordinator review than to incorrectly determine eligibility.
   If patient data is incomplete, ambiguous, or if the criterion is subjective, DO NOT guess or assume.
   Return INSUFFICIENT_DATA and specify exactly what information is needed.
   Examples:
     - Criterion: "Good renal function"
       Patient: No kidney data provided
       → Status: INSUFFICIENT_DATA (criterion is too vague; specific eGFR needed)

     - Criterion: "Age 18-75"
       Patient: "Approximately 55 years old"
       → Status: MEETS with HIGH confidence (age clearly in range)

     - Criterion: "HbA1c <8%"
       Patient: "Recent HbA1c was borderline"
       → Status: INSUFFICIENT_DATA (exact value needed, not subjective assessment)

2. SPECIFICITY IN REASONING
   Your reasoning must cite SPECIFIC values and data from the patient summary.
   Do NOT use generic phrases. Quote actual numbers, dates, and medical findings.
   Examples:
     - GOOD: "Patient HbA1c 8.2% exceeds criterion limit of 8.0%."
     - BAD: "Patient's diabetes control is poor."

     - GOOD: "Patient has no history of myocardial infarction, coronary artery disease, or stroke as documented in patient summary."
     - BAD: "Patient has no significant cardiac history."

3. CONFIDENCE CALIBRATION
   Assign confidence based on TWO factors: criterion clarity + data completeness.

   HIGH confidence:
     - Criterion is explicit and unambiguous (e.g., "age 18-75")
     - Patient data is complete for that criterion
     - Determination is unambiguous
     Example: Criterion "HbA1c <8%", Patient "HbA1c 7.2%". → MEETS, HIGH

   MEDIUM confidence:
     - Criterion is clear BUT patient data incomplete, OR
     - Criterion is ambiguous BUT patient data complete
     Example: Criterion "Age 18-75", Patient "age not specified, born 1970" → MEETS, MEDIUM (must calculate from birth year)
     Example: Criterion "Good renal function", Patient "eGFR 72" → INSUFFICIENT_DATA, MEDIUM (criterion vague, but data provided)

   LOW confidence:
     - Criterion is ambiguous AND patient data incomplete/ambiguous
     Example: Criterion "Stable disease", Patient "no recent imaging" → INSUFFICIENT_DATA, LOW

4. COMPOUND CRITERIA EVALUATION
   For criteria with AND logic: ALL conditions must be true.
   For criteria with OR logic: AT LEAST ONE condition must be true.
   For criteria with NOT logic: Condition must be false.

   Example AND:
     Criterion: "Age 50-75 AND eGFR >60"
     Patient: Age 65, eGFR 55
     → DOES_NOT_MEET (age meets, but eGFR does not)

   Example OR:
     Criterion: "HbA1c <8% OR on 2+ diabetes medications"
     Patient: HbA1c 8.5%, on Metformin + GLP-1
     → MEETS (HbA1c fails, but medication criterion passes)

5. TEMPORAL REQUIREMENTS
   Validate temporal conditions carefully.
   Example:
     Criterion: "Diagnosed within 6 months of screening"
     Patient: "Diagnosed March 2024, screening date July 2024" (4 months) → MEETS
     Patient: "Diagnosed January 2024, screening date July 2024" (6 months) → BORDERLINE; if exactly 6 months, check protocol (≤ or <)
     Patient: "Diagnosed December 2023, screening date July 2024" (7 months) → DOES_NOT_MEET
     Patient: "Diagnosed unknown date" → INSUFFICIENT_DATA

6. HANDLING AMBIGUOUS PATIENT DATA
   If patient summary is ambiguous, ask for clarification via missing_data field.
   Examples:
     - "Patient on multiple diabetes medications" (no specific names) → missing_data: ["specific medication names and dosages"]
     - "Recent labs" (no date) → missing_data: ["lab dates (within what timeframe is 'recent'?)"]
     - "Family history of cancer" (type and when?) → missing_data: ["type of cancer, age of family member at diagnosis"]

7. DO NOT MAKE CLINICAL JUDGMENTS
   Your role is to match data to criteria, not to provide clinical interpretation.
   Do NOT assess whether patient is "actually" healthy or whether diagnosis is accurate.
   Accept patient data as presented.
   Example:
     Criterion: "No history of CVD"
     Patient: "History of hypertension, well-controlled on medication"
     → Hypertension is cardiovascular condition; → DOES_NOT_MEET (even if controlled)
     OR if protocol intends "no prior MI/stroke", return INSUFFICIENT_DATA and ask for clarification

8. EQUAL WEIGHT TO INCLUSION AND EXCLUSION
   An exclusion criterion DOES_NOT_MEET is just as important as an inclusion criterion MEETS.
   Patient can be ineligible by failing even one exclusion criterion.
   Do NOT weight inclusion/exclusion differently.

OUTPUT FORMAT:
Return ONLY valid JSON. No markdown code blocks, no explanation text, no preamble.
Return a JSON array of assessment objects.

Example structure:
[
  {
    "criterion_id": "I1",
    "status": "MEETS",
    "confidence": "high",
    "reasoning": "Patient age 55 falls within criterion range of 18-75 years.",
    "missing_data": null
  },
  {
    "criterion_id": "I3",
    "status": "DOES_NOT_MEET",
    "confidence": "high",
    "reasoning": "Patient HbA1c 8.2% exceeds criterion upper limit of 8.0%.",
    "missing_data": null
  },
  {
    "criterion_id": "E1",
    "status": "INSUFFICIENT_DATA",
    "confidence": "medium",
    "reasoning": "Criterion requires eGFR >60 mL/min. Patient summary does not include eGFR value. Cannot determine kidney function.",
    "missing_data": ["Recent eGFR result (within last 3 months)", "Alternative: recent creatinine and age for calculation"]
  }
]

Now evaluate this patient against the provided criteria.
```

### Prompt Design Decisions

**Why Conservative Bias (INSUFFICIENT_DATA default):**
- False negatives (missing ineligibility) = patient enrolled wrongly = regulatory risk, patient safety risk
- False positives (flagging when not needed) = coordinator double-checks = extra work, but safe
- Clinically, conservatism is appropriate: "better safe than sorry"
- This design principle is stated upfront to LLM

**Why Cite Specific Values:**
- Generic reasoning like "diabetes control is poor" is not auditable
- Specific citation: "HbA1c 8.2% exceeds 8.0%" is verifiable
- Coordinator can see the evidence immediately
- Easier for PI to review and override if needed

**Why Confidence is Binary (Clarity × Completeness):**
- Not a statistical confidence interval (LLM can't do Bayesian stats reliably)
- Heuristic measure: HIGH = very confident in determination, LOW = unsure
- Used to flag cases for PI review
- Clear decision rules prevent subjective weighting

**Why Compound Logic Evaluated Explicitly:**
- LLM explicitly told: "For AND: ALL conditions must be true"
- Reduces risk of LLM shortcuts or misinterpretation
- Instructions for OR and NOT logic given separately

**Why Temporal Validation Emphasized:**
- Many trials have time-based criteria: "within 6 months", ">2 years ago"
- LLMs sometimes struggle with date math
- Explicit instruction with examples helps

**Why Not Making Clinical Judgments:**
- Coordinator and PI are responsible for clinical judgment
- LLM role is data matching, not clinical interpretation
- Example: "Hypertension = CVD event history?" — LLM told not to decide this; ask for clarification instead

---

### Known Failure Modes and Mitigations

| Failure Mode | Example | Mitigation |
|---|---|---|
| **False positive (MEETS when should be INSUFFICIENT_DATA)** | Criterion: "HbA1c <8%", Patient: "good diabetes control" (no number). LLM returns MEETS. | Instruction: "If in doubt, return INSUFFICIENT_DATA... cite SPECIFIC values" |
| **Missing compound logic** | Criterion: "Age 50-75 AND eGFR >60", Patient: Age 65, eGFR 55. LLM returns MEETS (only checks age). | Instruction: "For AND: ALL conditions must be true" with explicit example. |
| **Temporal math error** | Criterion: "Diagnosed within 6 months", Patient: "Diagnosed January 2024", Screening: "July 2024" (6 months exact). LLM returns DOES_NOT_MEET (says >6 months). | Instruction: "Temporal requirements evaluated carefully" with examples showing 6-month boundary. |
| **Over-interpreting vague criteria** | Criterion: "Good renal function" (undefined), Patient: "eGFR 72" (normal). LLM returns MEETS. | Instruction: "Do NOT make clinical judgments; ask for clarification... return INSUFFICIENT_DATA if criterion is too vague." |
| **Ignoring missing data** | Criterion: "Recent HbA1c <8%", Patient: No HbA1c provided. LLM returns INSUFFICIENT_DATA but missing_data is null. | Instruction: "If status=INSUFFICIENT_DATA, specify exactly what in missing_data field." |
| **Contradictory reasoning** | Criterion: "eGFR >60", Patient: "eGFR 55", LLM reasoning: "Patient meets criterion" while status=DOES_NOT_MEET. | Instruction: "Specify reasoning must cite specific values" and response validation (status/reasoning must be consistent). |

---

### Output Validation

**Valid Screening Response:**

```json
{
  "assessments": [
    {
      "criterion_id": "I1",
      "status": "MEETS",
      "confidence": "high",
      "reasoning": "...",
      "missing_data": null
    }
  ],
  "overall_status": "REQUIRES_REVIEW",
  "screening_metadata": {
    "total_criteria": 5,
    "meets_count": 4,
    "does_not_meet_count": 1,
    "insufficient_data_count": 0
  }
}
```

**Validation Rules (Backend):**
- criterion_id matches one from extraction
- status is one of: MEETS, DOES_NOT_MEET, INSUFFICIENT_DATA
- confidence is one of: high, medium, low
- reasoning is non-empty, <500 characters, cites specific values
- If status=INSUFFICIENT_DATA, missing_data must be non-null array
- If status≠INSUFFICIENT_DATA, missing_data must be null
- Confidence/status must be consistent (e.g., not HIGH confidence for INSUFFICIENT_DATA)

---

## Example Inputs and Expected Outputs

### Example 1: Diabetes Trial (Simple Case)

**Protocol Criteria (Extracted):**
```json
[
  {
    "criterion_id": "I1",
    "type": "inclusion",
    "description": "Age 18-75 years",
    "category": "demographics",
    "data_points_needed": ["age"],
    "logic": "18 ≤ age ≤ 75"
  },
  {
    "criterion_id": "I2",
    "type": "inclusion",
    "description": "Type 2 Diabetes Mellitus",
    "category": "diagnosis",
    "data_points_needed": ["diabetes_type"],
    "logic": null
  },
  {
    "criterion_id": "I3",
    "type": "inclusion",
    "description": "HbA1c between 7.0% and 10.5%",
    "category": "lab_values",
    "data_points_needed": ["HbA1c_value"],
    "logic": "7.0 ≤ HbA1c ≤ 10.5"
  }
]
```

**Patient Summary:**
```
Age: 55, Female
Diagnosis: Type 2 Diabetes Mellitus (diagnosed 2019)
HbA1c: 8.2% (March 2024)
Current medications: Metformin 1000mg BID
```

**Expected Screening Output:**
```json
[
  {
    "criterion_id": "I1",
    "status": "MEETS",
    "confidence": "high",
    "reasoning": "Patient age 55 falls within the criterion range of 18-75 years.",
    "missing_data": null
  },
  {
    "criterion_id": "I2",
    "status": "MEETS",
    "confidence": "high",
    "reasoning": "Patient has confirmed Type 2 Diabetes Mellitus diagnosis since 2019.",
    "missing_data": null
  },
  {
    "criterion_id": "I3",
    "status": "MEETS",
    "confidence": "high",
    "reasoning": "Patient HbA1c 8.2% is within criterion range of 7.0-10.5%.",
    "missing_data": null
  }
]
```

**Overall Status:** ELIGIBLE

---

### Example 2: Diabetes Trial (Missing Data Case)

**Same Protocol Criteria**

**Patient Summary (Incomplete):**
```
Age: 48
Diagnosis: Type 2 Diabetes
Recent labs ordered but not yet received
On diabetes medications
```

**Expected Screening Output:**
```json
[
  {
    "criterion_id": "I1",
    "status": "MEETS",
    "confidence": "high",
    "reasoning": "Patient age 48 is within criterion range of 18-75 years.",
    "missing_data": null
  },
  {
    "criterion_id": "I2",
    "status": "MEETS",
    "confidence": "high",
    "reasoning": "Patient has Type 2 Diabetes Mellitus diagnosis.",
    "missing_data": null
  },
  {
    "criterion_id": "I3",
    "status": "INSUFFICIENT_DATA",
    "confidence": "high",
    "reasoning": "Criterion requires HbA1c between 7.0-10.5%. Patient summary does not include HbA1c value.",
    "missing_data": ["Most recent HbA1c value and test date (within last 3 months)"]
  }
]
```

**Overall Status:** REQUIRES_REVIEW

---

### Example 3: Oncology Trial (Complex Criteria)

**Protocol Criteria:**
```json
[
  {
    "criterion_id": "I1",
    "type": "inclusion",
    "description": "Histologically or cytologically confirmed breast cancer",
    "category": "diagnosis",
    "data_points_needed": ["cancer_type", "confirmation_method"],
    "logic": null
  },
  {
    "criterion_id": "I2",
    "type": "inclusion",
    "description": "Stage II-III disease at baseline",
    "category": "diagnosis",
    "data_points_needed": ["cancer_stage", "stage_confirmation_date"],
    "logic": "Stage II OR Stage III"
  },
  {
    "criterion_id": "E1",
    "type": "exclusion",
    "description": "Prior chemotherapy within 2 years of enrollment",
    "category": "medical_history",
    "data_points_needed": ["prior_chemotherapy", "last_chemotherapy_date"],
    "logic": "No chemotherapy <2 years ago"
  }
]
```

**Patient Summary:**
```
Age: 62, Female
Diagnosis: Breast cancer, Stage III (invasive ductal carcinoma)
Confirmed by biopsy (2024-01-15)
Prior treatment: Received Adriamycin/cyclophosphamide in 2020
Current status: No active treatment × 2 years
ECOG: 1
```

**Expected Screening Output:**
```json
[
  {
    "criterion_id": "I1",
    "status": "MEETS",
    "confidence": "high",
    "reasoning": "Patient has histologically confirmed breast cancer (invasive ductal carcinoma) confirmed by biopsy on 2024-01-15.",
    "missing_data": null
  },
  {
    "criterion_id": "I2",
    "status": "MEETS",
    "confidence": "high",
    "reasoning": "Patient has Stage III breast cancer, which is within criterion range of Stage II-III.",
    "missing_data": null
  },
  {
    "criterion_id": "E1",
    "status": "MEETS",
    "confidence": "high",
    "reasoning": "Patient received chemotherapy in 2020; more than 2 years have elapsed since treatment (4 years). Exclusion criterion not triggered.",
    "missing_data": null
  }
]
```

**Overall Status:** ELIGIBLE

---

### Example 4: Cardiology Trial (Ambiguous Criterion)

**Protocol Criteria:**
```json
[
  {
    "criterion_id": "I1",
    "type": "inclusion",
    "description": "Heart failure with ejection fraction ≤40%",
    "category": "lab_values",
    "data_points_needed": ["LVEF", "LVEF_date"],
    "logic": "LVEF ≤ 40%"
  },
  {
    "criterion_id": "E1",
    "type": "exclusion",
    "description": "Hemodynamically significant valvular disease",
    "category": "diagnosis",
    "data_points_needed": ["valvular_disease_status", "valve_severity"],
    "logic": null
  }
]
```

**Patient Summary:**
```
Age: 68, Male
Diagnosis: Heart failure
Last echo: LVEF 35% (2024-02-01)
Medications: ACE inhibitor, beta-blocker, diuretic
Known cardiac issues: Mild mitral regurgitation (asymptomatic)
```

**Expected Screening Output:**
```json
[
  {
    "criterion_id": "I1",
    "status": "MEETS",
    "confidence": "high",
    "reasoning": "Patient LVEF 35% is ≤40% as required by criterion (measured 2024-02-01).",
    "missing_data": null
  },
  {
    "criterion_id": "E1",
    "status": "INSUFFICIENT_DATA",
    "confidence": "medium",
    "reasoning": "Criterion requires absence of 'hemodynamically significant' valvular disease. Patient has mild mitral regurgitation noted as asymptomatic. However, 'hemodynamically significant' is not explicitly defined. Severity grading and hemodynamic impact assessment needed.",
    "missing_data": [
      "Valvular disease severity grading (mild/moderate/severe)",
      "Hemodynamic impact assessment (e.g., echocardiography Doppler measurements)",
      "Whether asymptomatic mild MR qualifies as 'hemodynamically significant' per protocol intent"
    ]
  }
]
```

**Overall Status:** REQUIRES_REVIEW (coordinator must clarify with PI whether mild asymptomatic MR is acceptable)

---

## Prompt Versioning and Iteration Strategy

### Versioning Convention

**Format:** `version-MAJOR.MINOR-DATE`

**Current:** `extraction-v1.0-2026-03-24`, `screening-v1.0-2026-03-24`

**In Code:**
```python
# prompts/extraction.py
EXTRACTION_PROMPT_VERSION = "v1.0"
EXTRACTION_PROMPT_UPDATED = "2026-03-24"

EXTRACTION_SYSTEM_PROMPT = """
[Full prompt text]
"""
```

### Change Management

**When to Update Prompts:**
1. **Evaluation Results:** If extraction accuracy falls below 90% or screening concordance falls below 85%, investigate prompt
2. **Edge Case Failures:** If specific failure pattern identified (e.g., compound logic not captured), update prompt with example
3. **New Therapeutic Area:** If supporting new trial type (e.g., immunology), add category-specific instructions

**Update Process:**
1. Draft new prompt version (v1.1)
2. Test on 10 sample protocols with gold standard
3. Compare extraction accuracy v1.0 vs v1.1
4. If improvement ≥2%, roll out; otherwise iterate
5. Document change in CHANGELOG

**CHANGELOG Example:**
```
## v1.1 (2026-04-15)
- Added explicit AND/OR logic examples to screening prompt
- Fixed: Compound criteria with "OR" sometimes evaluated as "AND"
- Evaluation: Concordance improved 85% → 87% on test set

## v1.0 (2026-03-24)
- Initial release
- Baseline: 90% extraction accuracy, 85% screening concordance
```

---

## Testing and Evaluation Methodology

### Extraction Evaluation

**Gold Standard Dataset:**
- 3 trial protocols (diabetes, cardiology, oncology)
- Each protocol has manual extraction by clinical expert (gold standard)
- 40+ criteria across all three protocols
- Covers edge cases: compound criteria, temporal conditions, ambiguous criteria

**Metrics:**

```
Precision = (Correct extractions) / (Total extractions)
            Example: 38/40 criteria extracted correctly = 95% precision

Recall = (Correct extractions) / (Gold standard criteria)
         Example: If gold standard has 40, and we extract all 40 correctly = 100% recall
         If we extract 38/40, recall = 95%

F1-Score = 2 × (Precision × Recall) / (Precision + Recall)
           Balanced measure

Target: Precision >90%, Recall >90%, F1 >90%
```

**Evaluation Process:**
1. Run extraction on 3 test protocols
2. Compare output to gold standard (human expert extraction)
3. Calculate precision, recall, F1
4. Manual review of false positives and false negatives
5. If F1 <90%, investigate specific failure mode and iterate prompt

---

### Screening Evaluation

**Gold Standard Dataset:**
- 10 patient cases per protocol (30 total)
- Each patient manually screened by clinical expert (coordinator + PI review)
- Expected outcomes: ELIGIBLE, NOT_ELIGIBLE, or REQUIRES_REVIEW
- Per-criterion assessments recorded (status, confidence)

**Metrics:**

```
Concordance = (LLM matches expert decision) / (Total cases)
              Example: 26/30 cases match = 87% concordance
              Target: >85%

False Negative Rate = (Patient screened ELIGIBLE by LLM but NOT_ELIGIBLE by expert) / (Expert NOT_ELIGIBLE cases)
                     Example: 1 false negative out of 10 expert NOT_ELIGIBLE cases = 10% FNR
                     Target: <5% (clinical safety priority)

False Positive Rate = (Patient screened NOT_ELIGIBLE by LLM but ELIGIBLE by expert) / (Expert ELIGIBLE cases)
                     Example: 0 false positives out of 15 expert ELIGIBLE cases = 0% FPR
                     (Lower FPR = fewer coordinators wasted on review)

Confidence Calibration = (High confidence assessments that match expert) / (All high confidence assessments)
                        Example: 15/16 high-confidence assessments match expert = 94% calibration
                        Target: >90%
```

**Evaluation Process:**
1. Run screening on 30 test cases
2. Compare LLM overall_status to expert determination
3. Compare per-criterion assessments (status, confidence) to expert
4. Calculate concordance, FNR, FPR, confidence calibration
5. Manual review of discrepancies (especially false negatives)
6. If any metric falls below target, investigate and iterate prompt

---

### Running Evals (Procedural Steps)

**Step 1: Prepare Gold Standard**
```python
# evaluation/gold_standards.py

DIABETES_PROTOCOL_TEXT = """..."""  # Full protocol text
DIABETES_GOLD_EXTRACTION = [
  {
    "criterion_id": "I1",
    "type": "inclusion",
    ...
  },
  ...
]

DIABETES_TEST_CASES = [
  {
    "patient_id": "patient-diabetes-001",
    "summary": "55-year-old female...",
    "expert_decision": "ELIGIBLE",
    "expert_assessments": [
      {
        "criterion_id": "I1",
        "status": "MEETS",
        "confidence": "high"
      },
      ...
    ]
  },
  ...
]
```

**Step 2: Run Extraction Evaluation**
```python
# evaluation/eval_extraction.py

def evaluate_extraction():
  for protocol_name, protocol_text, gold_criteria in test_protocols:
    llm_output = call_extraction_api(protocol_text)

    precision = calculate_precision(llm_output, gold_criteria)
    recall = calculate_recall(llm_output, gold_criteria)
    f1 = 2 * (precision * recall) / (precision + recall)

    print(f"{protocol_name}: Precision={precision:.2%}, Recall={recall:.2%}, F1={f1:.2%}")

    if f1 < 0.90:
      log_failure_cases(llm_output, gold_criteria)
```

**Step 3: Run Screening Evaluation**
```python
# evaluation/eval_screening.py

def evaluate_screening():
  concordance_count = 0
  false_negatives = 0
  false_positives = 0

  for protocol, test_cases in test_suites:
    criteria = call_extraction_api(protocol)

    for patient_case in test_cases:
      llm_result = call_screening_api(criteria, patient_case["summary"])
      expert_result = patient_case["expert_decision"]

      if llm_result["overall_status"] == expert_result:
        concordance_count += 1
      elif llm_result == "ELIGIBLE" and expert_result == "NOT_ELIGIBLE":
        false_negatives += 1
      elif llm_result == "NOT_ELIGIBLE" and expert_result == "ELIGIBLE":
        false_positives += 1

  total_cases = sum(len(cases) for _, cases in test_suites)
  concordance = concordance_count / total_cases
  fnr = false_negatives / expert_not_eligible_count

  print(f"Concordance: {concordance:.2%}")
  print(f"False Negative Rate: {fnr:.2%}")

  if fnr > 0.05:
    log("ERROR: FNR exceeded safety threshold!")
    for case in false_negative_cases:
      log_analysis(case)
```

**Step 4: Review Failures**
- Manual inspection of discrepancies
- Categorize failures (compound logic, temporal, ambiguity, etc.)
- Update prompt to address pattern
- Re-run eval on same test set; ensure improvement

---

## Prompt Optimization for Cost and Latency

### Token Reduction Strategies

**Current Token Usage:**
- Extraction: ~13,500 tokens (expensive; happens once per protocol)
- Screening: ~4,700 tokens (cheaper; reused for multiple patients)

**Optimization Options (Future):**

1. **Summarize Protocol Before Extraction**
   - Pre-process to extract key sentences
   - Reduces input tokens by 30-40%
   - Risk: Might miss minor criteria
   - Recommendation: Use for Phase 2 if cost becomes concern

2. **Batch Screening (Future)**
   - Screen 5-10 patients per API call
   - Reduces API call overhead
   - Tokens per patient: 4,700 → ~3,500 with batching
   - Requires refactored API contract

3. **Model Downgrade (Not Recommended)**
   - Claude Sonnet 4 → Claude 3.5 Sonnet
   - Cost reduction: ~20%
   - Accuracy risk: Evaluation required
   - Recommendation: Keep Sonnet 4 for accuracy; optimize after evaluation

---

## Known Limitations and Future Improvements

### Current Limitations (MVP)

1. **Single Language (English):** Protocol and patient data must be in English
2. **No Image Analysis:** Cannot extract criteria from embedded protocol images
3. **No Real-Time Updates:** Criteria not updated if protocol revised mid-session
4. **No Multi-Trial Matching:** One protocol per session; no patient-to-trial matching
5. **No ClinicalTrials.gov Integration:** Cannot fetch live trial data

### Future Improvements (Phase 2+)

1. **Multilingual Support:** Auto-translate protocols; support non-English submissions
2. **Advanced PDF Handling:** Better OCR; table extraction; structured data recognition
3. **Real-Time Protocol Updates:** Versioning; delta updates if protocol revised
4. **Multi-Trial Matching:** Patient profile → search against multiple protocols
5. **EHR Integration:** FHIR-based data import; real-time patient data
6. **Fine-Tuning:** Custom models trained on trial-specific criteria language

---

## Sign-Off

| Role | Name | Date | Signature |
|------|------|------|-----------|
| Prompt Engineer | [Name] | 2026-03-24 | — |
| ML Engineer | [Name] | 2026-03-24 | — |
| QA Lead | [Name] | 2026-03-24 | — |

---

**END OF PROMPT ENGINEERING GUIDE**
