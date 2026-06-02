import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from tests.final_run_utils import run_and_print_example


# ============================================================
# Add any number of examples here.
# Copy Raw_Input and metadata from your final Dataset Excel.
# For D1 examples, D2 fields should be "N/A".
# For D2 examples, D1 fields should be "N/A".
# ============================================================

EXAMPLES = [
    {
        "Example_ID": "TEST_A_EX001",
        "Dataset_Type": "D1",
        "Run_ID": 1,

        "Raw_Input": """ahmed is nice. Is Ahmed nice?""",

        # D1 metadata
        "Expected_Entailment_Status": "entailed",
        "Expected_Not_Entailed_Type": "N/A",
        "Inference_Depth": 0,
        "Inference_Rules": "Direct Fact",
        "Distractor_Count": 0,
        "Case_Adjustment_Count": 1,
        "Pattern_Rewrite_Count": 0,
        "Subject_Propagation_Count": 0,
        "Synonym_Unification_Count": 0,
        "Antonym_Unification_Count": 0,
        "Normalization_Complexity_Score": 1,

        # D2 metadata
        "Expected_Component": "N/A",
        "Expected_SubComponent": "N/A",
        "Expected_Specific_Error": "N/A",
    },
]


def main() -> None:
    print("=" * 100)
    print("FINAL DATASET TEST A")
    print("Runs all examples stored inside this file.")
    print("=" * 100)

    for index, example in enumerate(EXAMPLES, start=1):
        print("\n\n")
        print("#" * 100)
        print(f"EXAMPLE {index}/{len(EXAMPLES)}")
        print("#" * 100)
        run_and_print_example(example)


if __name__ == "__main__":
    main()