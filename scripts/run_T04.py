from normalizer.normalizer import normalize_raw_prompt
import json

raw = 'It rains.\nThe ground is wet.'
res = normalize_raw_prompt(raw)
print(json.dumps(res, indent=2))
