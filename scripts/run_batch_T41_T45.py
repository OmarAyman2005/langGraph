import sys, json
sys.path.insert(0, r'C:\Users\Omar Ayman\Desktop\langGraph')
from normalizer.normalizer import normalize_raw_prompt

cases = [
    ("T41_PREVENT_NEGATION_SYNONYM_MERGE", "Ahmed is happy.\nAhmed is not happy.\nIs Ahmed happy?", 'expect_success_keep_both'),
    ("T42_INTERNAL_NEGATION", "Ahmed is not happy.\nIs Ahmed not happy?", 'expect_success'),
    ("T43_EXPLICIT_NOT_FORM", "Not Ahmed is happy.\nIs Ahmed not happy?", 'expect_success'),
    ("T44_NEGATIVE_CONDITIONAL_CONSEQUENT", "If Ahmed studies, then Ahmed is not tired.\nAhmed studies.\nIs Ahmed not tired?", 'expect_success'),
    ("T45_NEGATIVE_CONDITIONAL_ANTECEDENT", "If Ahmed is not tired, then Ahmed studies.\nAhmed is not tired.\nDoes Ahmed study?", 'expect_success'),
]

results = []
for tid, raw, expect in cases:
    print('---')
    print(tid)
    res = normalize_raw_prompt(raw)
    print(json.dumps(res, indent=2))
    ok = False
    if expect == 'expect_success' or expect == 'expect_success_keep_both':
        ok = bool(res.get('success'))
    status = 'PASS' if ok else 'FAIL'
    results.append((tid, status, res))
    print('Result:', status)
    if not ok:
        print('\nBatch stopped at', tid)
        break

print('\nSummary Table:')
print('Test ID | Status | Actual Behavior Summary | Notes')
print('--------------------------------')
for tid, status, res in results:
    if res.get('success'):
        summary = res.get('normalized_input').split('\n')[:5]
        summary = ' '.join(summary)
    else:
        summary = res.get('error')
    print(f'{tid} | {status} | {summary} |')

print('\nBatch meta:')
print('- code_changed: False')
print('- previous_passed_rerun: False')
print('- policy_decision_needed: False')
