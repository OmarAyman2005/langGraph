from graph.builder import build_graph
from graph.state import make_initial_state


def main():
    raw_input = """
I am Crazy or Stupid.
Ahmed is Crazy.
is Ahmed Stupid?
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