# Contributing

- Run the checks before opening a pull request (CI runs the same ones):

  ```bash
  pip install -r requirements.txt pytest ruff
  python -m pytest -q && ruff check . && python scripts/check_repo.py
  ```
- New behaviour needs a test in `tests/` (a fake model endpoint in both formats, fake Home Assistant and fake search backends are in `tests/conftest.py`).
- Changes to the safety rules in `src/home_tools.py` must keep every test in `tests/test_home_tools.py` passing;
  relaxing a rule needs a clear explanation in the pull request.
- Releases: add a `## X.Y.Z` section to `CHANGELOG.md`, then push a tag `vX.Y.Z`. The release workflow runs every
  check, publishes the multi-arch image to GitHub Container Registry and creates the GitHub release with that
  section as notes. Set a repository secret `RELEASE_TOKEN` (a fine-grained personal token with *Contents: read and
  write* on this repository) to have the release created under your name instead of the Actions bot.
- Translations are welcome: a new `skill/interaction-model.<locale>.json` plus the spoken strings.
- A new provider usually needs no code: if it speaks the OpenAI or Anthropic format, add a preset to
  `docs/providers.md`. If it needs a quirk handled, add it to `src/llm.py` with a test in `tests/test_providers.py`.
