import sys, json
sys.path.insert(0, r'C:\Users\Omar Ayman\Desktop\langGraph')
from normalizer.normalizer import normalize_raw_prompt

cases = [
    ("T31_IT_AMBIGUOUS_OBJECT", "The machine is near the screen.\nIt is active.\nIs the machine active?", 'expect_fail_ambiguous'),
    ("T32_RAIN_SIMPLE_CONTINUOUS", "It rains.\nIf it is raining, then the ground is wet.\nIs the ground wet?", 'expect_success'),
    ("T33_DO_SUPPORT", "Ahmed plays.\nIf Ahmed does play, then Ahmed wins.\nDoes Ahmed win?", 'expect_success'),
    ("T34_GETS_WET_IS_WET", "If it rains, then the ground gets wet.\nIt rains.\nIs the ground wet?", 'expect_success'),
    ("T35_BECOMES_COLD_IS_COLD", "If the AC works, then the room becomes cold.\nThe AC works.\nIs the room cold?", 'expect_success'),
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
    elif expect == 'expect_fail_ambiguous':
        ok = (not res.get('success')) and ('Ambiguous' in (res.get('error') or '') or 'ambiguous' in (res.get('error') or '').lower())

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
        summary = res.get('normalized_input').split('\n')[:4]
        summary = ' '.join(summary)
    else:
        summary = res.get('error')
    print(f'{tid} | {status} | {summary} |')

print('\nBatch meta:')
print('- code_changed: False')
print('- previous_passed_rerun: False')
print('- policy_decision_needed: False')
