from graph.builder import build_graph
from graph.state import make_initial_state
from normalizer.normalizer import normalize_raw_prompt


def main():
    raw_input = """
if people eat healthy they become fit people eat healthy
Do people become fit
"""

    initial_state = make_initial_state(raw_input=raw_input)

    graph = build_graph()
    result = graph.invoke(initial_state)

    print("\n=== NORMALIZED OUTPUT ===")
    print(result.get("normalized_input"))

    print("\n=== NORMALIZATION SUCCESS ===")
    print(result.get("normalization_success"))

    print("\n=== NORMALIZATION ERROR ===")
    print(result.get("normalization_error"))

    print("\n=== NORMALIZATION DEBUG ===")
    print(result.get("normalization_debug"))


if __name__ == "__main__":
    main()