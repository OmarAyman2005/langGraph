# Normalizer Contract

Input:
Raw user prompt.

Output:
Either:
- success=false + specific error
OR
- normalized prompt:

Premises:
1. ...
2. ...

Question:
...

Pipeline order:
1. Question checking — deterministic
2. Premise extraction/separation — LLM
3. Premise validation — LLM
4. Sentence pattern normalization — deterministic + LLM fallback
5. Subject propagation — deterministic
6. Question atom extraction — deterministic
7. Premise atom extraction — deterministic
8. Synonym unification — LLM
9. Antonym/negation unification — LLM
10. Final output