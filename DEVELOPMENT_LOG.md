# Development Log — TrialMatch AI

## [2026-06-05 18:00] — Afternoon

**Status:** Active development
**Focus area:** Testing
**Progress note:** Added integration tests for the /screen endpoint covering edge cases where patients have incomplete lab values (e.g., missing eGFR or platelet count). Tests assert that the screener returns a structured "insufficient data" response rather than a false exclusion, ensuring coordinators are prompted to collect missing labs before a definitive eligibility decision.

## [2026-06-05 22:00] — Evening

**Status:** Active development
**Focus area:** Prompt engineering
**Progress note:** Cleaned up the criteria extraction prompt to handle multi-part inclusion criteria more reliably — specifically cases where a single criterion contains nested sub-conditions joined by "and/or". Reviewed outputs on a batch of 15 oncology trials and confirmed the updated prompt reduces mis-parsed criteria by roughly 30%.
