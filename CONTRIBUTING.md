# Contributing

Thanks for your interest in improving `VoxtralTTS-UI`.

## Before You Start

- open an issue for bugs, regressions, or larger feature ideas
- keep changes focused and avoid mixing unrelated refactors in the same pull request
- do not commit local data such as API keys, generated audio, reference samples, or personal config files

## Development Setup

```powershell
python -m venv .venv
.\.venv\Scripts\activate
python -m pip install -U pip
pip install -e .
```

Optional test dependencies:

```powershell
pip install -e .[dev]
```

## Project Rules

- keep the public repo sanitized
- prefer ASCII unless the file already uses Unicode intentionally
- preserve the existing product direction: desktop-first, practical for local AI workflows, and honest about runtime constraints
- keep UI changes consistent across both the standard and premium variants unless there is a clear reason not to

## Pull Requests

Please try to include:

- a short explanation of the change
- screenshots for visible UI changes
- notes about local testing
- any important caveats or follow-up work

## Suggested PR Scope

Good pull requests for this repo are usually one of:

- bug fixes
- documentation improvements
- UX refinements
- runtime integration improvements
- packaging or setup workflow improvements

## Security

If you find a security issue or accidentally discover sensitive material in the repository history, please avoid opening a public issue with secrets included.

At minimum:

- rotate any exposed keys immediately
- open a sanitized issue without pasting the secret
- describe the impact and where the material was found

## License Reminder

By contributing, you agree that your contributions will be distributed under the repository license.
