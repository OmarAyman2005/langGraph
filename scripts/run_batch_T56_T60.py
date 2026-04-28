import sys, json
sys.path.insert(0, r'C:\Users\Omar Ayman\Desktop\langGraph')
from normalizer.normalizer import normalize_raw_prompt

cases = [
    ("T56_VALID_WITH_DISJUNCTION_AND_NEGATION", "The backup light is not active.\nThe screen is bright or the backup light is active.\nIs the screen bright?", 'expect_success'),
    ("T57_BORDERLINE_DO_NOT_GUESS", "Ahmed is ready.\nThis means he can go.\nCan Ahmed go?", 'expect_fail_borderline'),
    ("T58_FULL_PIPELINE_STYLE_RAW", "If the sensor is active, the alarm rings. If the alarm rings, the guard wakes up. The sensor is active. Does the guard wake up?", 'expect_success'),
    ("T59_QUESTION_TARGET_NOT_IN_PREMISES", "It rains.\nIs the sky blue?", 'expect_success'),
    ("T60_DOMAIN_REJECTION_CLEAR", "All engineers are students. Omar is an engineer. Is Omar a student?", 'expect_fail_domain'),
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
    elif expect == 'expect_fail_borderline':
        ok = (not res.get('success'))
    elif expect == 'expect_fail_domain':
        ok = (not res.get('success')) and ('quantified' in (res.get('error') or '').lower() or 'domain' in (res.get('error') or '').lower())
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
