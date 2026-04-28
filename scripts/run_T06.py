from normalizer.normalizer import normalize_raw_prompt
import json

raw = 'Is the ground wet?'
res = normalize_raw_prompt(raw)
print(json.dumps(res, indent=2))
