import sys
from pathlib import Path


# Force UTF-8 output so intentional D2 non-English / special-character tests print safely on Windows.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from tests.final_run_utils import run_and_print_example


# ============================================================
# Batch 15A-2:
# D2_EX027 and D2_EX028 verifier contradiction cases only.
# Each D2 example is run ONCE only.
# ============================================================

EXAMPLES = [
    {
        "Example_ID": "D2_EX027",
        "Dataset_Type": "D2",
        "Run_ID": 1,

        "Raw_Input": """Ahmed studies.
Ahmed does not study.
Does Ahmed study?""",

        "Expected_Entailment_Status": "N/A",
        "Expected_Not_Entailed_Type": "N/A",
        "Inference_Depth": "N/A",
        "Inference_Rules": "N/A",
        "Distractor_Count": "N/A",
        "Case_Adjustment_Count": "N/A",
        "Pattern_Rewrite_Count": "N/A",
        "Subject_Propagation_Count": "N/A",
        "Synonym_Unification_Count": "N/A",
        "Antonym_Unification_Count": "N/A",
        "Normalization_Complexity_Score": "N/A",

        "Expected_Component": "Verifier",
        "Expected_SubComponent": "N/A",
        "Expected_Specific_Error": "VF_CONTRADICTORY_PREMISES",
    },
]


def main() -> None:
    print("=" * 100)
    print("FINAL DATASET TEST A")
    print("Batch 15A-2: D2_EX027 to D2_EX028")
    print("=" * 100)

    for index, example in enumerate(EXAMPLES, start=1):
        print("\n\n")
        print("#" * 100)
        print(f"EXAMPLE {index}/{len(EXAMPLES)}")
        print("#" * 100)
        run_and_print_example(example)


if __name__ == "__main__":
    main()