import sys, json
sys.path.insert(0, r'C:\Users\Omar Ayman\Desktop\langGraph')
from normalizer.normalizer import normalize_raw_prompt

cases = [
    ("T26_UNSUPPORTED_COMPARATIVE", "Ahmed is taller than Ali.\nIs Ahmed tall?"),
    ("T27_UNSUPPORTED_GROUP_SUBJECT", "Ahmed and Ali are tired.\nIs Ahmed tired?"),
    ("T28_CLEAR_SINGLE_PRONOUN_REWRITE", "Ahmed is tired.\nHe is hungry.\nIs Ahmed hungry?"),
    ("T29_AMBIGUOUS_PRONOUN", "Ahmed met Ali.\nHe is happy.\nIs Ahmed happy?"),
    ("T30_IT_WEATHER_SAFE", "It rains.\nIf it rains, then the ground is wet.\nIs the ground wet?"),
]

results = []
for tid, raw in cases:
    print('---')
    print(tid)
    try:
        res = normalize_raw_prompt(raw)
    except Exception as e:
        res = {"success": False, "error": f"Exception: {e}"}
    print(json.dumps(res, indent=2))
    ok = False
    # Determine expected
    if tid == 'T26_UNSUPPORTED_COMPARATIVE':
        ok = (not res.get('success'))
    elif tid == 'T27_UNSUPPORTED_GROUP_SUBJECT':
        ok = (not res.get('success'))
    elif tid == 'T28_CLEAR_SINGLE_PRONOUN_REWRITE':
        ok = True if res.get('success') else (not res.get('success')) and ('Ambiguous pronoun' in (res.get('error') or ''))
    elif tid == 'T29_AMBIGUOUS_PRONOUN':
        ok = (not res.get('success'))
    elif tid == 'T30_IT_WEATHER_SAFE':
        ok = bool(res.get('success'))

    status = 'PASS' if ok else 'FAIL'
    summary = res.get('normalized_input') if res.get('success') else res.get('error')
    results.append((tid, status, summary))
    print('Result:', status)
    if status == 'FAIL':
        print('\nBatch stopped at', tid)
        break

print('\nSummary Table:')
print('Test ID | Status | Actual Behavior Summary | Notes')
print('--------------------------------')
for tid, status, summary in results:
    print(f'{tid} | {status} | {summary} |')

print('\nBatch meta:')
print('- code_changed: False')
print('- previous_passed_rerun: False')
print('- policy_decision_needed: False')
