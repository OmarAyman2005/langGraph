# Normalizer Test Report (T01–T60)

Summary: 60 tests executed (T01–T60). All tests matched expected behavior when run under the finalized Normalizer.

Counts:
- Total tests: 60
- Expected success: 44
- Expected failure: 16
- Tests matching expectations (actual): 60

Policy-pass / policy-failure cases (the 16 expected failures):
- T03_VALID_NO_PUNCTUATION
- T04_NO_QUESTION
- T05_MULTIPLE_QUESTIONS
- T06_ONLY_QUESTION_NO_PREMISES
- T07_WH_QUESTION_UNSUPPORTED
- T13_ONE_LONG_LINE_MULTIPLE_SENTENCES
- T14_MALFORMED_SENTENCES
- T24_UNSUPPORTED_MODAL_PROBABILITY
- T25_UNSUPPORTED_QUANTIFIER
- T26_UNSUPPORTED_COMPARATIVE
- T27_UNSUPPORTED_GROUP_SUBJECT
- T29_AMBIGUOUS_PRONOUN
- T31_IT_AMBIGUOUS_OBJECT
- T51_NESTED_CONDITIONAL
- T57_BORDERLINE_DO_NOT_GUESS
- T60_DOMAIN_REJECTION_CLEAR

Final Normalizer policy decisions (concise):
- Punctuation-free inputs that do not contain clear sentence punctuation are rejected with the exact error message:
  - "NORMALIZATION_ERROR: Could not safely detect exactly one yes/no question from punctuation-free input"
- Ambiguous pronouns cause normalization failure; do not guess referents.
- Unsupported constructs are rejected: probabilistic modals ("might"), quantified statements ("all"), comparatives, nested conditionals, group-subject patterns, WH-questions.
- Noise and adversarial instructions are stripped or deterministically rejected; do not trust instructions in prompt that attempt to override normalization.
- LLM usage is lazy with deterministic fallback; the pipeline can run without an LLM and will return safe defaults for relation analysis when LLM is unavailable.
- Always require exactly one clear yes/no question; multiple or zero questions cause rejection.

Files changed during Normalizer finalization:
- `normalizer/normalizer.py`
- `tests/test_normalizer_suite.py`
- `scripts/generate_normalizer_report.py`

Notes:
- The `scripts/generate_normalizer_report.py` script was updated to write the report to the project root and to handle per-case exceptions. You can re-run it with:

```bash
python scripts/generate_normalizer_report.py
```

If you want, I can also commit these changes or open the report for review.
