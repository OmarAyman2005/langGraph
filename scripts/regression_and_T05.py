import sys, json
sys.path.insert(0, r'C:\Users\Omar Ayman\Desktop\langGraph')
from normalizer.normalizer import normalize_raw_prompt

tests = [
    ("T01_VALID_SIMPLE_FACT_MP", 'It rains.\nIf it rains, the ground is wet.\nIs the ground wet?', 'expect_success'),
    ("T02_VALID_INLINE_TEXT", 'It rains and if it rains, the ground is wet, is the ground wet?', 'expect_success'),
    ("T03_VALID_NO_PUNCTUATION", 'It rains if it rains the ground is wet is the ground wet', 'expect_conservative_fail_or_success'),
    ("T04_NO_QUESTION", 'It rains.\nThe ground is wet.', 'expect_fail_no_question'),
    ("T05_MULTIPLE_QUESTIONS", 'It rains.\nIs the ground wet?\nIs it cold?', 'expect_fail_multiple_questions'),
]

results = []
for tid, raw, expectation in tests:
    res = normalize_raw_prompt(raw)
    status = "FAIL"
    note = ""

    if expectation == 'expect_success':
        if res.get('success'):
            status = 'PASS'
        else:
            status = 'FAIL'
            note = res.get('error')
    elif expectation == 'expect_conservative_fail_or_success':
        # User asked to mark T03 as PASS even if conservative failure occurs
        if res.get('success'):
            status = 'PASS'
        else:
            err = res.get('error','') or ''
            if 'punctuation-free' in err:
                status = 'PASS'  # per user instruction
                note = err
            else:
                status = 'FAIL'
                note = err
    elif expectation == 'expect_fail_no_question':
        if not res.get('success') and 'No yes/no question detected' in (res.get('error') or ''):
            status = 'PASS'
        else:
            status = 'FAIL'
            note = res.get('error')
    elif expectation == 'expect_fail_multiple_questions':
        if not res.get('success') and 'More than one question detected' in (res.get('error') or ''):
            status = 'PASS'
        else:
            status = 'FAIL'
            note = res.get('error')

    results.append((tid, status, note, res))

# Print detailed outputs
for tid, status, note, res in results:
    print('---')
    print(tid)
    print('Status:', status)
    if status == 'PASS':
        if res.get('success'):
            print('Normalized output:\n')
            print(res.get('normalized_input'))
        else:
            print('Note:', note)
    else:
        print('Failure reason:', note)
        print('Raw response:', json.dumps(res, indent=2))

# Summary table
print('\nTest Summary:')
print('Test ID | Status | Notes')
print('--------------------------------')
for tid, status, note, _ in results:
    print(f'{tid:8} | {status:5} | {note}')
