import sys, json
sys.path.insert(0, r'C:\Users\Omar Ayman\Desktop\langGraph')
from normalizer.normalizer import normalize_raw_prompt
raw = 'It rains and if it rains, the ground is wet, is the ground wet?'
res = normalize_raw_prompt(raw)
print('T02 result:')
print(json.dumps(res, indent=2))
raw2 = 'It rains.\nIf it rains, the ground is wet.\nIs the ground wet?'
res2 = normalize_raw_prompt(raw2)
print('\nT01 result:')
print(json.dumps(res2, indent=2))
