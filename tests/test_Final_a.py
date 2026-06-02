import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from tests.final_run_utils import run_and_print_example


# ============================================================
# Temporary N8 special-case test
# Purpose:
# - Tests antonym unification in an already-negated premise:
#   ahmed is not weak -> ahmed is strong
# - Tests antonym unification in a question:
#   is khaled short? -> is khaled not tall?
# - Tests double-negation cleanup inside N8.
# ============================================================

EXAMPLES = [
    {
        "Example_ID": "N8_SPECIAL_EX001",
        "Dataset_Type": "MANUAL",
        "Run_ID": 1,

        "Raw_Input": """sara is strong.
ahmed is not weak.
khaled is tall.
is khaled short?""",

        # D1 metadata
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

        # D2 metadata
        "Expected_Component": "N/A",
        "Expected_SubComponent": "N/A",
        "Expected_Specific_Error": "N/A",
    },
]


def main() -> None:
    print("=" * 100)
    print("FINAL DATASET TEST A — N8 SPECIAL CASE")
    print("Runs all examples stored inside this file.")
    print("=" * 100)

    for index, example in enumerate(EXAMPLES, start=1):
        print("\n\n")
        print("#" * 100)
        print(f"EXAMPLE {index}/{len(EXAMPLES)}")
        print("#" * 100)
        run_and_print_example(
            example=example,
            include_dataset_metadata=False,
        )


if __name__ == "__main__":
    main()