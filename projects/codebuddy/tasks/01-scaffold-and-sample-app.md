# Task 01 — Package scaffold and sample legacy app

Implement this specification exactly. Do not read the other files in `tasks/`.
This specification is the complete contract. Ask no questions. Write the files.

All paths below are relative to `projects/codebuddy/`.

## Goal

Create the Python package skeleton for a CLI agent called `codebuddy`.
Create a small, deliberately imperfect target repository named `sample-legacy-app/`.
Later tasks add the agent logic. This task adds no Claude Agent SDK code.

## Files to create

### 1. `requirements.txt`

Exactly these three requirements, one per line, unpinned:

```
claude-agent-sdk
python-dotenv
black
```

### 2. `.env.example`

Include these four lines. Add a short comment above each line.

```
# Optional. The Agent SDK does not read .env by itself. codebuddy loads this file.
ANTHROPIC_API_KEY=
# Optional gateway pair. Use these instead of ANTHROPIC_API_KEY for a proxy.
ANTHROPIC_BASE_URL=
ANTHROPIC_AUTH_TOKEN=
# Optional model override. Default is claude-opus-5.
CODEBUDDY_MODEL=
```

### 3. `.gitignore`

```
.venv/
__pycache__/
*.pyc
.env
sample-legacy-app/EXPLORATION.md
codebuddy_generated/
```

### 4. `codebuddy/__init__.py`

One module docstring. One line: `__version__ = "0.1.0"`. Nothing else.

### 5. `codebuddy/commands/__init__.py`

One module docstring only. The file must be otherwise empty.

### 6. `transcripts/.gitkeep`

An empty file.

## The sample legacy app

Create exactly these seven files under `sample-legacy-app/`.
Write plain Python 3.13. Use the standard library only.
The app must import and run without errors.

### `sample-legacy-app/README.md`

Write a short, **deliberately stale** README. It must contradict the real code in two
ways. First, it must claim the package has three modules. The package really has five.
Second, it must tell the reader to call `app.run()`. The real entry point is `app.main()`.
Add no note that says the README is stale. The staleness must be silent.

### `sample-legacy-app/app.py`

The entry point. Define `main()`. `main()` must call one handler from `handlers.py` and
print the result. Add an `if __name__ == "__main__":` guard. Keep it under 30 lines.

### `sample-legacy-app/config.py`

A module-level dictionary named `SETTINGS`. Give it four keys: `tax_rate`, `currency`,
`discount_cap`, and `verbose`. Define `get(key, default=None)` which reads `SETTINGS`.

### `sample-legacy-app/handlers.py`

Define three functions. Each function takes a dictionary and returns a dictionary.
Each function must call something from `legacy_pricing.py` or `utils.py`.
**Write this file with CRLF line endings.**
**Format this file badly on purpose.** Use single quotes in some places and double quotes
in others. Put no space around some operators. Make two lines longer than 100 characters.

### `sample-legacy-app/legacy_pricing.py`

This is the deliberately confusing module. It is the file that a human reader must
struggle with. Build it as follows.

- Define one function `calc(o, c, d, f)`. Use only single-letter parameter names.
- Nest conditional statements at least four levels deep.
- Use at least four unexplained numeric literals, for example `0.07` and `1.15`.
- Include one **unreachable branch**. Order the tests so the last one can never run.
  For example, test `> 10` first, then `> 5`, then `> 20`.
- Define a second function `_legacy_adjust(v)` that `calc` calls.
- Add exactly one comment that starts with `# TODO:`.
- Add exactly one comment that starts with `# FIXME:`.
- Add no other comments. Add no docstrings.

### `sample-legacy-app/utils.py`

Define two helpers: `round_money(value)` and `slugify(text)`.
**Write this file with CRLF line endings.**
**Format this file badly on purpose**, in the same way as `handlers.py`.

### `sample-legacy-app/tests/test_utils.py`

Two `pytest`-style tests for `utils.round_money` and `utils.slugify`.
This file sets the convention that a later task copies. Therefore it must show a clear
convention:

- A one-line module docstring.
- Test names in the form `test_<function>_<case>`.
- Plain `assert` statements. Use no test class and no fixture.
- LF line endings. Clean formatting.

Create `sample-legacy-app/tests/__init__.py` as an empty file if the tests need it.

## Commenting requirements

`sample-legacy-app/` is the confusing target that the agent must later explain.
Therefore do **not** add helpful comments or docstrings inside `sample-legacy-app/`.
The only comments allowed there are the one `# TODO:` and the one `# FIXME:` in
`legacy_pricing.py`.

Files under `codebuddy/` follow the opposite rule. Every module gets a docstring that
says what the module does.

## Acceptance criteria

The reviewer runs these checks. All must pass.

1. Every file listed above exists at the stated path.
2. `python -m compileall -q sample-legacy-app codebuddy` reports no error.
3. `python -c "import sys; sys.path.insert(0,'sample-legacy-app'); import app; app.main()"`
   runs and prints output without raising.
4. Exactly two files contain a CRLF byte pair: `sample-legacy-app/handlers.py` and
   `sample-legacy-app/utils.py`. No other file contains CRLF.
5. `grep -c 'TODO:' sample-legacy-app/legacy_pricing.py` returns 1.
   `grep -c 'FIXME:' sample-legacy-app/legacy_pricing.py` returns 1.
6. `grep -rn 'TODO:\|FIXME:' sample-legacy-app --include='*.py'` matches
   `legacy_pricing.py` only.
7. `legacy_pricing.py` contains a branch chain whose final test can never be reached.
   The reviewer reads the file to confirm this.
8. `python -m black --check sample-legacy-app/handlers.py sample-legacy-app/utils.py`
   **fails**. This proves the formatter has real work to do later.
9. `sample-legacy-app/README.md` makes both false claims described above.
10. No file under `sample-legacy-app/` contains an explanatory comment, other than the
    single TODO and the single FIXME.
11. No file imports `claude_agent_sdk`. This task adds no SDK code.

## Out of scope

Do not create `config.py`, `observability.py`, `permissions.py`, `mcp.py`,
`__main__.py`, or anything under `codebuddy/commands/` other than `__init__.py`.
Do not create `README.md`, `DECISIONS.md`, or `COORDINATION.md` at the project root.
Do not install packages. Do not run `git add` or `git commit`.

## When you finish

Print a list of the files you created. Then print the result of each acceptance check
that you were able to run yourself. Then stop.
