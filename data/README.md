# Fixture provenance

The fixtures are original fictional English documents and labels, licensed MIT.
`scripts/create_fixtures.py` defines every literal template and evidence substring.
It deterministically generates `fixtures.json`; it never reads model output.
There are six station families, three document types per family, and three
questions per document. Tables include competing rows. Code includes error,
maintenance, and live branches. Cross references separate release prerequisites
from the referenced permit and timing sections with an unrelated archive section.

The split is document-disjoint but shares templates. It is deliberately small
and repetitive, useful for observing boundary effects, not production conclusions.
Evidence spans may span a condition and return value or require multiple distant
sections. All relevance annotations are author-created, with no external review.
