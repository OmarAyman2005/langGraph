from normalizer.normalizer import normalize_raw_prompt
import json

raw = "It rains.\nIf it rains, the ground is wet.\nIs the ground wet?"
res = normalize_raw_prompt(raw)
print(json.dumps(res, indent=2))
