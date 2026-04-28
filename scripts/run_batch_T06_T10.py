import sys, json
sys.path.insert(0, r'C:\Users\Omar Ayman\Desktop\langGraph')
from normalizer.normalizer import normalize_raw_prompt

cases = [
    ("T06_ONLY_QUESTION_NO_PREMISES", "Is the ground wet?"),
    ("T07_WH_QUESTION_UNSUPPORTED", "It rains.\nWhat happens to the ground?"),
    ("T08_YES_NO_QUESTION_WITH_DO", "Ahmed plays.\nDoes Ahmed play?"),
    ("T09_YES_NO_QUESTION_WITH_HAS", "Ahmed has lost.\nHas Ahmed lost?"),
    ("T10_YES_NO_QUESTION_WITH_WILL", "Ahmed will win.\nWill Ahmed win?"),
]

for tid, raw in cases:
    print('---')
    print(tid)
    res = normalize_raw_prompt(raw)
    print(json.dumps(res, indent=2))
    # If a test failed (success==False), stop the batch at first failure
    if not res.get('success'):
        print('\nBatch stopped due to failure at', tid)
        break
print('\nBatch complete')
