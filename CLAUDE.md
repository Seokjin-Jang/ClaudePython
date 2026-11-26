# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project status

ClaudePython is a collection of Python code written with AI (Claude). The repository currently contains only `README.md` and this file: there is no source code, package manifest, test suite, linter config, or CI yet. When code is added, update this file with the real build/test/lint commands and architecture instead of assuming conventions.

## Conventions from README

- Target Python 3.10+.
- Use a virtual environment at `.venv` (`python -m venv .venv`, then `.\.venv\Scripts\Activate.ps1` on Windows).
- Dependencies, once added, go in `requirements.txt` (`pip install -r requirements.txt`).
- Scripts are run directly: `python <file>.py`.
- Keep the "프로젝트 구조" section of `README.md` in sync when adding files or directories.

## Implementation workflow: TDD

When implementing a feature, fixing a bug, refactoring, or changing behavior in this repo, invoke the `test-driven-development` skill (`.claude/skills/test-driven-development/`, from obra/superpowers) before writing any implementation code, and follow its red-green-refactor cycle: write a failing test, run it and watch it fail for the right reason, write the minimal code to pass, run the full suite, then refactor. This also applies to subagents that write code.

- Test runner: `pytest` (install into `.venv` with `pip install pytest`). Run one test with `pytest path/to/test_file.py::test_name`, the full suite with `pytest`.
- Exceptions the skill allows (throwaway prototypes, generated code, config files) still need the user's OK before skipping TDD.

## Language

Documentation (README, commit messages) is written in Korean; keep new docs and commit messages in Korean. Code identifiers stay in English.

## Environment

- Development machine is Windows with PowerShell 5.1.
- Remote: `https://github.com/Seokjin-Jang/ClaudePython.git`, default branch `main`. Git HTTPS auth goes through `gh` (`gh auth setup-git`).
