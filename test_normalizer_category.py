from normalizer.normalizer import normalize_raw_prompt


TESTS = [
    {
        "id": "17.1",
        "name": "Past vs present not treated as opposite",
        "input": """
It rains.
It rained.
Does it rain?
""",
        "expected": """Premises:
1. It rains.
2. It rained.

Question:
Does it rain?"""
    },
    {
        "id": "17.2",
        "name": "Malformed opposite with empty side ignored",
        "input": """
If it rains, the ground gets wet.
It rains.
Is the ground wet?
""",
        "expected": """Premises:
1. If it rains, then the ground gets wet.
2. it rains.

Question:
Does the ground get wet?"""
    },
    {
        "id": "17.3",
        "name": "Positive and negated atoms not grouped as synonyms",
        "input": """
Ahmed is happy.
Is Ahmed not happy?
""",
        "expected": """Premises:
1. Ahmed is happy.

Question:
Is Ahmed not happy?"""
    },
]

def normalize_text(text: str) -> str:
    return "\n".join(line.rstrip() for line in text.strip().splitlines())


def main():
    for test in TESTS:
        result = normalize_raw_prompt(test["input"])

        actual = result.get("normalized_input")
        error = result.get("error")
        success = result.get("success")

        expected = normalize_text(test["expected"])
        actual_norm = normalize_text(actual) if actual else None

        if expected.startswith("NORMALIZATION_ERROR"):
            passed = (not success) and error == expected
        else:
            passed = success and actual_norm == expected

        print("=" * 80)
        print(f"TEST {test['id']} — {test['name']}")
        print("=" * 80)

        print("\nINPUT:")
        print(test["input"].strip())

        print("\nEXPECTED:")
        print(expected)

        print("\nACTUAL:")
        print(actual if actual else error)

        print("\nPASS:")
        print(passed)

        if not passed:
            print("\nDEBUG:")
            print(result.get("debug"))

    print("=" * 80)


if __name__ == "__main__":
    main()