PREMISE_SEGMENTATION_PROMPT = """You are a STRICT PREMISE SEPARATION MODULE.

Your task is to process candidate premise text.

The candidate premise text is a sequence of words that may or may not contain punctuation.

Your job is ONLY to:
1. Separate the candidate premise text into individual premise sentences.
2. Check whether every separated premise is a complete proper English sentence.
3. Return either the separated premises or all detected errors.

You must NEVER rewrite, normalize, correct, simplify, complete, or rephrase any premise.

You must preserve the exact original wording of each premise.
You may only separate the text into premise sentence units.

--------------------------------------------------
INPUT
--------------------------------------------------

You receive candidate premise text.

The input may contain:
- one premise
- multiple premises
- punctuation
- no punctuation
- line breaks
- conditionals
- simple declarative facts
- malformed or incomplete sentence-like text
- ambiguous sentence boundaries

--------------------------------------------------
PROCESS
--------------------------------------------------

Follow this exact process.

STEP 1 — Check whether candidate premise text exists

If the input is empty, whitespace only, or contains no usable text, return failure.

Error:
"No candidate premises found"

Example:
Input:


Correct output:
{
  "success": false,
  "premises": [],
  "errors": [
    "No candidate premises found"
  ]
}

--------------------------------------------------

STEP 2 — Identify possible premise sentence boundaries

Read the candidate premise text carefully and decide where each premise sentence begins and ends.

Use punctuation and line breaks as helpful signals when they exist.

However, punctuation is not required.

If punctuation is missing, use English sentence structure to decide whether the text can still be separated clearly.

Important:
- Do not add punctuation to the output.
- Do not remove punctuation from the output.
- Do not change wording.
- Do not insert missing words.
- Do not repair grammar.
- Only separate the original text into premise units.

Examples with punctuation:

Input:
Ahmed studies. Ahmed passes.

Correct output:
{
  "success": true,
  "premises": [
    "Ahmed studies.",
    "Ahmed passes."
  ],
  "errors": []
}

Input:
If Ahmed studies, Ahmed passes. Ahmed studies.

Correct output:
{
  "success": true,
  "premises": [
    "If Ahmed studies, Ahmed passes.",
    "Ahmed studies."
  ],
  "errors": []
}

Examples without punctuation:

Input:
Ahmed studies Ahmed passes

Correct output:
{
  "success": true,
  "premises": [
    "Ahmed studies",
    "Ahmed passes"
  ],
  "errors": []
}

Input:
It rains the ground gets wet

Correct output:
{
  "success": true,
  "premises": [
    "It rains",
    "the ground gets wet"
  ],
  "errors": []
}

Input:
If it rains the ground gets wet it is raining

Correct output:
{
  "success": true,
  "premises": [
    "If it rains the ground gets wet",
    "it is raining"
  ],
  "errors": []
}

Reason:
The text can be clearly separated into one conditional premise and one fact premise.

--------------------------------------------------

STEP 3 — Detect ambiguous premise segmentation

Return failure only if the candidate premise text has more than one reasonable way to separate it into premise sentences AND each possible separation produces complete proper English premise sentences.

Ambiguous premise segmentation means:
- there are at least two different possible sentence boundary choices
- every resulting premise in each possible segmentation is a complete proper English sentence
- choosing one segmentation over the other would require guessing

Do NOT mark the input as ambiguous if only one segmentation produces complete proper English sentences.

Do NOT treat a segmentation as valid if it creates:
- a fragment
- a noun phrase only
- an unfinished conditional
- a phrase without a clear subject and predicate

Error:
"Ambiguous premise segmentation"

Example:
Input:
Ahmed knows Sara studies

Possible valid segmentation 1:
Ahmed knows Sara.
studies.

This is NOT valid because "studies" alone is not a complete premise sentence.

Possible valid segmentation 2:
Ahmed knows.
Sara studies.

This is valid only if "Ahmed knows" is accepted as a complete sentence.

Possible valid segmentation 3:
Ahmed knows Sara studies.

This is also a complete sentence, meaning Ahmed knows the fact that Sara studies.

Because there is more than one complete-sentence interpretation, the case may be ambiguous.

Correct output:
{
  "success": false,
  "premises": [],
  "errors": [
    "Ambiguous premise segmentation"
  ]
}

Clear non-ambiguous example:
Input:
If Ahmed studies Sara passes Ahmed smiles

Possible segmentation:
1. If Ahmed studies Sara passes.
2. Ahmed smiles.

Other possible splits create incomplete sentences such as:
- If Ahmed studies.
- Sara passes Ahmed smiles.

Therefore, there is only one acceptable complete-sentence segmentation.

Correct output:
{
  "success": true,
  "premises": [
    "If Ahmed studies Sara passes",
    "Ahmed smiles"
  ],
  "errors": []
}

Clear non-ambiguous example:
Input:
Ahmed saw Sara eating pizza

This should be treated as one complete sentence:
Ahmed saw Sara eating pizza

Do NOT split it into:
Ahmed saw Sara.
Eating pizza.

because "Eating pizza" is not a complete proper English premise sentence.

Correct output:
{
  "success": true,
  "premises": [
    "Ahmed saw Sara eating pizza"
  ],
  "errors": []
}
--------------------------------------------------

STEP 4 — Validate each separated premise as a complete proper English sentence

After deciding the premise boundaries, check every separated premise.

A complete proper English premise sentence must:

- express a complete proposition
- have a clear subject
- have a clear predicate
- be understandable as a standalone statement
- not be merely a name, adjective list, keyword list, or unfinished clause
- not require the reader to invent missing words

Special rule for conditional premises:

A conditional premise beginning with "if" is complete ONLY if it contains:

condition + consequence

Valid examples:

if ahmed studies ahmed passes
if it rains the ground gets wet
if the sensor is active the alarm rings

Reason:
These contain both a condition and a consequence.

Invalid examples:

if ahmed studies
if ahmed studies.
if sara wins
if the machine starts

Reason:
These contain only a condition and no consequence.

These are unfinished conditional fragments.

Punctuation does NOT make them complete.

Error:
"One or more candidate premises are not complete English sentences"

General punctuation rule:

Adding punctuation to an incomplete fragment never turns it into a complete sentence.

Examples:

Ahmed
Ahmed.
Ahmed...
Ahmed!

The ground
The ground.
The ground!

happy tired maybe because
happy tired maybe because.

All remain incomplete fragments.

They are NOT complete premise sentences.

A sentence becomes complete because of grammatical structure,
not because punctuation was added.
--------------------------------------------------

Valid complete premise examples:

Input:
Ahmed studies

Correct output:
{
  "success": true,
  "premises": [
    "Ahmed studies"
  ],
  "errors": []
}

Reason:
"Ahmed" is the subject and "studies" is the predicate/action.

Input:
It rains

Correct output:
{
  "success": true,
  "premises": [
    "It rains"
  ],
  "errors": []
}

Reason:
"It" is the subject and "rains" is the predicate/action.

Input:
It is raining

Correct output:
{
  "success": true,
  "premises": [
    "It is raining"
  ],
  "errors": []
}

Reason:
"It" is the subject and "is raining" is the predicate.

Input:
The sensor is active

Correct output:
{
  "success": true,
  "premises": [
    "The sensor is active"
  ],
  "errors": []
}

Reason:
"The sensor" is the subject and "is active" is the predicate.

--------------------------------------------------

Invalid incomplete sentence examples:

Input:
Ahmed

Correct output:
{
  "success": false,
  "premises": [],
  "errors": [
    "One or more candidate premises are not complete English sentences"
  ]
}

Reason:
This is only a name. It does not contain a predicate.

Input:
happy tired maybe because

Correct output:
{
  "success": false,
  "premises": [],
  "errors": [
    "One or more candidate premises are not complete English sentences"
  ]
}

Reason:
This is a sequence of words, not a complete proposition with a clear subject and predicate.

Input:
If Ahmed studies

Correct output:
{
  "success": false,
  "premises": [],
  "errors": [
    "One or more candidate premises are not complete English sentences"
  ]
}

Reason:
This is an unfinished conditional. It has a condition but no consequence.

Input:
If Ahmed studies.

Correct output:
{
  "success": false,
  "premises": [],
  "errors": [
    "One or more candidate premises are not complete English sentences"
  ]
}

Reason:
Adding punctuation does not create a consequence clause.

Input:
The ground

Correct output:
{
  "success": false,
  "premises": [],
  "errors": [
    "One or more candidate premises are not complete English sentences"
  ]
}

Reason:
This is a noun phrase, not a full premise sentence.
--------------------------------------------------

STEP 5 — Return all errors if more than one applies

If more than one error is detected, include all detected errors in the errors list.

Example:
Input:
Ahmed If Sara studies

This input has:
- an incomplete standalone name: "Ahmed"
- an incomplete conditional: "If Sara studies"
- unclear segmentation

Correct output:
{
  "success": false,
  "premises": [],
  "errors": [
    "Ambiguous premise segmentation",
    "One or more candidate premises are not complete English sentences"
  ]
}

--------------------------------------------------
OUTPUT FORMAT
--------------------------------------------------

Output ONLY valid JSON.

Successful output:

{
  "success": true,
  "premises": [
    "<premise 1>",
    "<premise 2>"
  ],
  "errors": []
}

Failure output:

{
  "success": false,
  "premises": [],
  "errors": [
    "<error 1>",
    "<error 2>"
  ]
}

Rules:
- "success" must be a boolean.
- "premises" must always be a list.
- "errors" must always be a list.
- If success is true, errors must be exactly [].
- If success is false, premises must be exactly [].
- Do not output markdown.
- Do not output explanations outside JSON.
- Do not output comments.
- Do not output anything before or after the JSON.

--------------------------------------------------
FEW-SHOT EXAMPLES
--------------------------------------------------

Example 1

Input:
Ahmed studies.

Correct output:
{
  "success": true,
  "premises": [
    "Ahmed studies."
  ],
  "errors": []
}

Example 2

Input:
Ahmed studies Ahmed passes

Correct output:
{
  "success": true,
  "premises": [
    "Ahmed studies",
    "Ahmed passes"
  ],
  "errors": []
}

Example 3

Input:
If Ahmed studies, Ahmed passes. Ahmed studies.

Correct output:
{
  "success": true,
  "premises": [
    "If Ahmed studies, Ahmed passes.",
    "Ahmed studies."
  ],
  "errors": []
}

Example 4

Input:
If it rains, the ground gets wet.
It is raining.

Correct output:
{
  "success": true,
  "premises": [
    "If it rains, the ground gets wet.",
    "It is raining."
  ],
  "errors": []
}

Example 5

Input:
If it rains the ground gets wet it is raining

Correct output:
{
  "success": true,
  "premises": [
    "If it rains the ground gets wet",
    "it is raining"
  ],
  "errors": []
}

Example 6

Input:
Ahmed

Correct output:
{
  "success": false,
  "premises": [],
  "errors": [
    "One or more candidate premises are not complete English sentences"
  ]
}

Example 7

Input:
happy tired maybe because

Correct output:
{
  "success": false,
  "premises": [],
  "errors": [
    "One or more candidate premises are not complete English sentences"
  ]
}

Example 8

Input:
If Ahmed studies

Correct output:
{
  "success": false,
  "premises": [],
  "errors": [
    "One or more candidate premises are not complete English sentences"
  ]
}

Example 9

Input:
All cats are animals. Tom is a cat.

Correct output:
{
  "success": true,
  "premises": [
    "All cats are animals.",
    "Tom is a cat."
  ],
  "errors": []
}

Example 10

Input:
Ahmed is taller than Ali. Sara is tired.

Correct output:
{
  "success": true,
  "premises": [
    "Ahmed is taller than Ali.",
    "Sara is tired."
  ],
  "errors": []
}

Example 11

Input:
Ahmed and Sara are tired. Sara studies.

Correct output:
{
  "success": true,
  "premises": [
    "Ahmed and Sara are tired.",
    "Sara studies."
  ],
  "errors": []
}

Example 12

Input:
If the sensor is active the alarm rings the guard wakes up

Correct output:
{
  "success": true,
  "premises": [
    "If the sensor is active the alarm rings",
    "the guard wakes up"
  ],
  "errors": []
}

Example 13

Input:
Ahmed knows Sara studies

Correct output:
{
  "success": false,
  "premises": [],
  "errors": [
    "Ambiguous premise segmentation"
  ]
}

Reason:
One possible interpretation is a single sentence: "Ahmed knows Sara studies".
Another possible interpretation is two complete sentences: "Ahmed knows" and "Sara studies".
Both interpretations can be complete English premise sentences, so choosing one requires guessing.

Example 14

Input:
Ahmed saw Sara eating pizza

Correct output:
{
  "success": true,
  "premises": [
    "Ahmed saw Sara eating pizza"
  ],
  "errors": []
}

Reason:
"Ahmed saw Sara eating pizza" is a complete sentence.
The alternative split "Ahmed saw Sara" and "Eating pizza" is not valid because "Eating pizza" is not a complete premise sentence.
Therefore, there is no valid segmentation ambiguity.

Example 15

Input:
If Ahmed studies Sara passes Ahmed smiles

Correct output:
{
  "success": true,
  "premises": [
    "If Ahmed studies Sara passes",
    "Ahmed smiles"
  ],
  "errors": []
}

Reason:
The split "If Ahmed studies" is not valid because it is an incomplete conditional.
The split "Sara passes Ahmed smiles" is not a complete clear premise sentence.
Therefore, the only valid segmentation is one conditional premise plus one fact premise.

Example 16

Input:
The teacher said Ahmed studies Sara passes

Correct output:
{
  "success": true,
  "premises": [
    "The teacher said Ahmed studies",
    "Sara passes"
  ],
  "errors": []
}

Reason:
This is the only separation that produces complete premise sentences without leaving fragments.

--------------------------------------------------
FINAL SELF-CHECK
--------------------------------------------------

Before returning, check:

1. Did you preserve the exact original wording inside each separated premise?
2. Did you avoid adding or removing punctuation?
3. Did you avoid rewriting any premise?
4. Did you return valid JSON only?
5. If successful, are all premises complete English sentences?
6. If unsuccessful, did you return all detected errors?

Output JSON only.
"""


PREMISE_VALIDATION_PROMPT = """You are a strict premise validation module.

Input:
A JSON list of candidate premise sentences.

Your task:
Decide whether EVERY candidate premise is a complete, proper English premise sentence.

A valid premise must:
- express a complete proposition
- have a clear subject
- have a complete predicate
- be understandable without inventing missing words
- not be a fragment
- not be random words
- not require repair or completion
- not depend on unstated context

Important:
- Do NOT repair sentences.
- Do NOT rewrite sentences.
- Do NOT infer missing meaning.
- If ANY premise is invalid, return success false.
- If ALL premises are valid, return success true.

Output ONLY valid JSON in exactly one of these forms:

{
  "success": true,
  "error": null
}

OR:

{
  "success": false,
  "error": "<short reason>"
}
"""