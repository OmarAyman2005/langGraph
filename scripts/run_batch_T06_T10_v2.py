import sys, json
sys.path.insert(0, r'C:\Users\Omar Ayman\Desktop\langGraph')
from normalizer.normalizer import normalize_raw_prompt

cases = [
    ("T06_ONLY_QUESTION_NO_PREMISES", "Is the ground wet?", 'expect_fail_no_premises'),
    ("T07_WH_QUESTION_UNSUPPORTED", "It rains.\nWhat happens to the ground?", 'expect_fail_wh'),
    ("T08_YES_NO_QUESTION_WITH_DO", "Ahmed plays.\nDoes Ahmed play?", 'expect_success'),
    ("T09_YES_NO_QUESTION_WITH_HAS", "Ahmed has lost.\nHas Ahmed lost?", 'expect_success'),
    ("T10_YES_NO_QUESTION_WITH_WILL", "Ahmed will win.\nWill Ahmed win?", 'expect_success'),
]

for tid, raw, expectation in cases:
    print('---')
    print(tid)
    res = normalize_raw_prompt(raw)
    print(json.dumps(res, indent=2))

    ok = False
    note = None
    if expectation == 'expect_success':
        ok = bool(res.get('success'))
        note = None if ok else res.get('error')
    elif expectation == 'expect_fail_no_premises':
        ok = (not res.get('success')) and ('No candidate premises' in (res.get('error') or ''))
        note = None if ok else res.get('error')
    elif expectation == 'expect_fail_wh':
        ok = (not res.get('success')) and ('unsupported' in (res.get('error') or '').lower() or 'wh' in (res.get('error') or '').lower())
        note = None if ok else res.get('error')

    status = 'PASS' if ok else 'FAIL'
    print('Result:', status, ('Note: '+note) if note else '')

    if not ok:
        print('\nBatch stopped at', tid)
        break

print('\nBatch finished')
