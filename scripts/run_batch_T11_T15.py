import sys, json
sys.path.insert(0, r'C:\Users\Omar Ayman\Desktop\langGraph')
from normalizer.normalizer import normalize_raw_prompt

cases = [
    ("T11_YES_NO_QUESTION_WITH_CAN", "Ahmed can swim.\nCan Ahmed swim?", 'expect_success'),
    ("T12_MULTIPLE_PREMISES_CLEAR", "Ahmed is tired.\nIf Ahmed is tired, then Ahmed sleeps.\nIs Ahmed sleeping?", 'expect_success'),
    ("T13_ONE_LONG_LINE_MULTIPLE_SENTENCES", "Ahmed is tired Ahmed sleeps if Ahmed sleeps then Ahmed rests is Ahmed resting", 'expect_fail_conservative'),
    ("T14_MALFORMED_SENTENCES", "Ahmed.\nHappy.\nIs Ahmed happy?", 'expect_fail_malformed'),
    ("T15_ATOMIC_FACT", "Ahmed is happy.\nIs Ahmed happy?", 'expect_success'),
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
    elif expectation == 'expect_fail_conservative':
        # conservative failure for punctuation-free
        ok = (not res.get('success')) and ('punctuation-free' in (res.get('error') or '').lower())
        note = None if ok else res.get('error')
    elif expectation == 'expect_fail_malformed':
        ok = (not res.get('success')) and ('malformed' in (res.get('error') or '').lower() or 'unsupported' in (res.get('error') or '').lower())
        note = None if ok else res.get('error')

    status = 'PASS' if ok else 'FAIL'
    print('Result:', status, ('Note: '+note) if note else '')

    if not ok:
        print('\nBatch stopped at', tid)
        break

print('\nBatch finished')
