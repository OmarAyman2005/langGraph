import sys, json
sys.path.insert(0, r'C:\Users\Omar Ayman\Desktop\langGraph')
from normalizer.normalizer import normalize_raw_prompt

cases = [
    ("T16_NEGATION", "Ahmed is not happy.\nIs Ahmed not happy?", 'expect_success'),
    ("T17_CONJUNCTION_EXPLICIT", "Ahmed is tired and Ahmed is hungry.\nIs Ahmed hungry?", 'expect_success'),
    ("T18_CONJUNCTION_IMPLICIT_SUBJECT", "Ahmed is tired and hungry.\nIs Ahmed hungry?", 'expect_success'),
    ("T19_DISJUNCTION_EXPLICIT", "Ahmed is a cat or Ahmed is a dog.\nIs Ahmed a cat?", 'expect_success'),
    ("T20_DISJUNCTION_IMPLICIT_SUBJECT", "Ahmed is a cat or a dog.\nIs Ahmed a dog?", 'expect_success'),
]

results = []
for tid, raw, expect in cases:
    print('---')
    print(tid)
    res = normalize_raw_prompt(raw)
    print(json.dumps(res, indent=2))
    ok = bool(res.get('success')) if expect == 'expect_success' else False
    status = 'PASS' if ok else 'FAIL'
    results.append((tid, status, res))
    if not ok:
        print('\nBatch stopped at', tid)
        break

print('\nSummary Table:')
print('Test ID | Status | Actual Behavior Summary | Notes')
print('--------------------------------')
for tid, status, res in results:
    summary = ''
    note = ''
    if res.get('success'):
        summary = res.get('normalized_input').split('\n')[:3]
        summary = ' '.join(summary)
    else:
        summary = res.get('error')
    print(f'{tid} | {status} | {summary} | {note}')

# Meta info for batch
print('\nBatch meta:')
print('- code_changed: False')
print('- previous_passed_rerun: False')
print('- policy_decision_needed: False')
