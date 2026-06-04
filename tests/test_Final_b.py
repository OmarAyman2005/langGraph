import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from tests.final_run_utils import run_and_print_example


EXAMPLE = {
    "Example_ID": "DEMO_D1_EX009_STYLE_SUCCESS",
    "Dataset_Type": "D1",
    "Run_ID": 1,

    "Raw_Input": """Both the sensor is ready and it is clean.
is the sensor prepared?""",

    "Expected_Entailment_Status": "entailed",
    "Expected_Not_Entailed_Type": "N/A",
    "Inference_Depth": 1,
    "Inference_Rules": "CE",
    "Distractor_Count": 0,
    "Case_Adjustment_Count": 1,
    "Pattern_Rewrite_Count": 1,
    "Subject_Propagation_Count": 1,
    "Synonym_Unification_Count": 1,
    "Antonym_Unification_Count": 0,
    "Normalization_Complexity_Score": 4,

    "Expected_Component": "N/A",
    "Expected_SubComponent": "N/A",
    "Expected_Specific_Error": "N/A",
}


def main() -> None:
    print("=" * 100)
    print("FINAL TEST B — DEMO 1: D1 VALID ENTAILED CE EXAMPLE")
    print("=" * 100)
    run_and_print_example(EXAMPLE)


if __name__ == "__main__":
    main()