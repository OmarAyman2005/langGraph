import sys, json
sys.path.insert(0, r'C:\Users\Omar Ayman\Desktop\langGraph')
from normalizer.normalizer import normalize_raw_prompt
raw = 'It rains if it rains the ground is wet is the ground wet'
res = normalize_raw_prompt(raw)
print(json.dumps(res, indent=2))
