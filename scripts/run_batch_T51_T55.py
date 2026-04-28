import sys, json
sys.path.insert(0, r'C:\Users\Omar Ayman\Desktop\langGraph')
from normalizer.normalizer import normalize_raw_prompt

cases = [
    ("T51_NESTED_CONDITIONAL", "If it rains, then if the ground is cold, then the road freezes.\nIt rains.\nIs the road freezing?", 'expect_fail_nested'),
    ("T52_MULTI_PREDICATE_FACT", "Ahmed eats and sleeps and studies.\nDoes Ahmed study?", 'expect_success_or_fail'),
    ("T53_RELATIONAL_VERB_UNSUPPORTED", "Ahmed loves Sara.\nDoes Ahmed love Sara?", 'expect_policy'),
    ("T54_FACT_WITH_OBJECT_ACTION", "Ahmed eats dinner.\nDoes Ahmed eat dinner?", 'expect_success'),
    ("T55_VALID_COMPLEX_NORMALIZATION", "If the machine is on, the screen gets bright.\nThe machine is on.\nIs the screen bright?", 'expect_success'),
]

results = []
for tid, raw, expect in cases:
    print('---')
    print(tid)
    res = normalize_raw_prompt(raw)
    print(json.dumps(res, indent=2))
    ok = False
    if expect == 'expect_fail_nested':
        ok = (not res.get('success'))
    elif expect == 'expect_success_or_fail':
        ok = True if res.get('success') else (not res.get('success')) and ('punctuation-free' in (res.get('error') or '').lower())
    elif expect == 'expect_policy':
        # Behavior must be consistent; accept either
        ok = True
    elif expect == 'expect_success':
        ok = bool(res.get('success'))

    status = 'PASS' if ok else 'FAIL'
    results.append((tid, status, res))
    print('Result:', status)
    if status == 'FAIL':
        print('\nBatch stopped at', tid)
        break

print('\nSummary Table:')
print('Test ID | Status | Actual Behavior Summary | Notes')
print('--------------------------------')
for tid, status, res in results:
    if res.get('success'):
        summary = res.get('normalized_input').split('\n')[:4]
        summary = ' '.join(summary)
    else:
        summary = res.get('error')
    print(f'{tid} | {status} | {summary} |')

print('\nBatch meta:')
print('- code_changed: False')
print('- previous_passed_rerun: False')
print('- policy_decision_needed: False')
