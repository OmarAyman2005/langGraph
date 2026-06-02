import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from tests.final_run_utils import run_and_print_example


def read_multiline_input() -> str:
    print("Manual Debug Test: Final Full Pipeline Runtime Output")
    print("Paste one raw input.")
    print("When finished, type END on a new line.")
    print("=" * 100)

    lines = []

    while True:
        line = input()

        if line.strip() == "END":
            break

        lines.append(line)

    return "\n".join(lines)


def main() -> None:
    raw_input = read_multiline_input()

    example = {
        "Example_ID": "MANUAL_EX001",
        "Dataset_Type": "MANUAL",
        "Run_ID": 1,
        "Raw_Input": raw_input,

        # D1 metadata hidden as N/A
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

        # D2 metadata hidden as N/A
        "Expected_Component": "N/A",
        "Expected_SubComponent": "N/A",
        "Expected_Specific_Error": "N/A",
    }

    print("\n\n")
    run_and_print_example(
        example=example,
        include_dataset_metadata=False,
    )


if __name__ == "__main__":
    main()