import sys, json
sys.path.insert(0, r'C:\Users\Omar Ayman\Desktop\langGraph')
from normalizer.normalizer import normalize_raw_prompt

cases = [
    ("T21_EITHER_OR", "Either Ahmed is a cat or Ahmed is a dog.\nIs Ahmed a dog?", 'expect_success'),
    ("T22_CONDITIONAL_STANDARD", "If it rains, then the ground is wet.\nIt rains.\nIs the ground wet?", 'expect_success'),
    ("T23_CONDITIONAL_MISSING_THEN", "If it rains, the ground is wet.\nIt rains.\nIs the ground wet?", 'expect_success'),
    ("T24_UNSUPPORTED_MODAL_PROBABILITY", "Ahmed might be happy.\nIs Ahmed happy?", 'expect_fail_modal'),
    ("T25_UNSUPPORTED_QUANTIFIER", "All cats are animals.\nAhmed is a cat.\nIs Ahmed an animal?", 'expect_fail_quantifier'),
]

results = []
for tid, raw, expect in cases:
    print('---')
    print(tid)
    res = normalize_raw_prompt(raw)
    print(json.dumps(res, indent=2))
    ok = False
    if expect == 'expect_success':
        ok = bool(res.get('success'))
    elif expect == 'expect_fail_modal':
        ok = (not res.get('success')) and ('probabilistic' in (res.get('error') or '').lower() or 'modal' in (res.get('error') or '').lower() or 'unsupported' in (res.get('error') or '').lower())
    elif expect == 'expect_fail_quantifier':
        ok = (not res.get('success')) and ('quantified' in (res.get('error') or '').lower() or 'quantifier' in (res.get('error') or '').lower() or 'category-wide' in (res.get('error') or '').lower())

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
        summary = res.get('normalized_input').split('\n')[:3]
        summary = ' '.join(summary)
    else:
        summary = res.get('error')
    print(f'{tid} | {status} | {summary} |')

print('\nBatch meta:')
print('- code_changed: False')
print('- previous_passed_rerun: False')
print('- policy_decision_needed: False')
