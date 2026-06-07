# Development Log — TrialMatch AI

## [2026-06-05 18:00] — Afternoon

**Status:** Active development
**Focus area:** Testing
**Progress note:** Added integration tests for the /screen endpoint covering edge cases where patients have incomplete lab values (e.g., missing eGFR or platelet count). Tests assert that the screener returns a structured "insufficient data" response rather than a false exclusion, ensuring coordinators are prompted to collect missing labs before a definitive eligibility decision.

## [2026-06-05 22:00] — Evening

**Status:** Active development
**Focus area:** Prompt engineering
**Progress note:** Cleaned up the criteria extraction prompt to handle multi-part inclusion criteria more reliably — specifically cases where a single criterion contains nested sub-conditions joined by "and/or". Reviewed outputs on a batch of 15 oncology trials and confirmed the updated prompt reduces mis-parsed criteria by roughly 30%.

## [2026-06-06 14:00] — Afternoon

**Status:** Active development
**Focus area:** API integration
**Progress note:** Integrated ClinicalTrials.gov API v2 NCT ID lookup to resolve trial identifiers passed in from coordinator uploads. Added retry logic with exponential backoff to handle intermittent 503 responses, and updated the data pipeline to cache enriched trial metadata locally to reduce redundant API calls during batch screening runs.

## [2026-06-07 14:00] — Afternoon

**Status:** Active development
**Focus area:** Performance
**Progress note:** Profiled the two-stage LLM pipeline under concurrent screening requests and identified a bottleneck in the criteria extraction stage where large protocol PDFs were being re-parsed on every request. Introduced an in-memory cache keyed on protocol hash, cutting median latency by ~40% for repeat submissions of the same trial document during a coordinator's session.
