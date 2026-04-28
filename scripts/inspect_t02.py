import sys, json
sys.path.insert(0, r'C:\Users\Omar Ayman\Desktop\langGraph')
from normalizer.normalizer import detect_yes_no_questions, split_candidate_clauses
raw = 'It rains and if it rains, the ground is wet, is the ground wet?'
qs, nonqs = detect_yes_no_questions(raw)
print('questions:', qs)
print('non_questions:', nonqs)
print('split_candidate_clauses on remaining:')
print(split_candidate_clauses(', '.join(nonqs)))
