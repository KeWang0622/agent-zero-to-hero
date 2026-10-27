# Contributing

This is a textbook, not a framework. Keep each lesson small, inspectable, and centered on one misconception. The course includes executable chapters and explicitly labelled design labs.

## useful changes

- Fix a demonstrated bug and add a regression case that would fail before the fix.
- Clarify a protocol invariant, implementation limit, or source attribution.
- Add one missing engineering concept with a concrete failure and an assessable exercise.
- Update a dated API fact using an opened primary source and record the checked date.

Priorities and acceptance criteria are in [docs/WISHLIST.md](docs/WISHLIST.md).

## validation

```bash
python -m pip install -e ".[test]"
python -m pytest tests/ -q
python -m ruff check .
git diff --check
```

Executable chapters need meaningful offline contract tests. Design labs need checked examples, working links, and explicit statements about what is and is not implemented. Live model tests must be opt-in; never require credentials for ordinary CI.

## house style

Use plain prose, lower-case section headings, and comments explaining why a decision matters. Prefer small functions. Avoid framework abstractions introduced only for configurability. Use the course's Anthropic vocabulary in foundation lessons and the provider's exact terms in adaptation chapters.

Keep the progression: misconception → small example → named failure → correction → exercise with acceptance criteria. Distinguish measured data, hypothetical calculations, vendor case studies, and editorial recommendations. Preserve original provider payloads when they matter; do not normalize away important behavior to make an adapter look shorter.

Update navigation and the evidence ledger when adding a lesson. Describe the resulting behavior and relevant checks in the PR. Contributions are MIT-licensed.
