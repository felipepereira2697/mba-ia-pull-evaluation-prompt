# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

MBA challenge (fork of `devfullcycle/mba-ia-pull-evaluation-prompt`): pull a low-quality prompt that turns bug reports into user stories from the LangSmith Prompt Hub, optimize it, push it back, and evaluate it until **each** of the 5 metrics (Helpfulness, Correctness, F1-Score, Clarity, Precision) is >= 0.8. A passing average is not enough. Code, prompts, and docs are written in Portuguese. `README.md` is the challenge statement and lists the required deliverables.

## Commands

Run scripts from the repo root, because `evaluate.py` uses the relative path `datasets/bug_to_user_story.jsonl`.

```bash
python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt

python src/pull_prompts.py   # Hub -> prompts/bug_to_user_story_v1.yml
python src/push_prompts.py   # prompts/bug_to_user_story_v2.yml -> Hub
python src/evaluate.py       # exit code 0 only if approved; makes paid/rate-limited LLM calls

pytest tests/test_prompts.py
pytest tests/test_prompts.py::TestPrompts::test_prompt_no_todos -v   # single test
```

No linter or build step is configured. Configuration comes from `.env` (see `.env.example`).

## Challenge constraints

**Do not modify** (per the challenge rules): `src/evaluate.py`, `src/metrics.py`, `src/utils.py`, `datasets/bug_to_user_story.jsonl`. To raise a score, change only `prompts/bug_to_user_story_v2.yml`.

## Architecture

**The Hub, not the local YAML, is what gets evaluated.** `evaluate.py` pulls `{USERNAME_LANGSMITH_HUB}/bug_to_user_story_v2` from the LangSmith Hub, so a YAML edit has no effect on scores until it is pushed. The iteration loop is edit YAML → push → evaluate.

**Evaluation flow** (`evaluate.py`):
1. Creates the LangSmith dataset `{LANGSMITH_PROJECT}-eval` from the JSONL. If a dataset with that name already exists it is reused as is, so later JSONL changes are not synced.
2. Runs `prompt | llm` over the examples via `client.evaluate` as a LangSmith experiment, sequentially (`max_concurrency=1`) to respect free-tier rate limits. The target returns `{"answer": ...}`.
3. `evaluate_all_metrics` calls three LLM judges from `metrics.py` per example: F1, Clarity, Precision. The other two metrics are derived: Helpfulness = (Clarity + Precision) / 2, Correctness = (F1 + Precision) / 2. Low Precision therefore drags down both derived metrics.
4. Scores are saved as experiment feedback and averaged per metric for the pass/fail report.

The other evaluators in `metrics.py` (tone, acceptance criteria, user story format, completeness) are not used by `evaluate.py`.

**Models:** `utils.get_llm` selects the provider through `LLM_PROVIDER`. `LLM_MODEL` generates answers and `EVAL_MODEL` (via `get_eval_llm`) runs the judges. No model is pinned; both must be set in `.env` and must accept `temperature=0`.

## Gotchas

- The prompt template's input variable must be `{bug_report}`, which is the dataset's input key.
- `LLM_PROVIDER` must be `openai` or `google`. `evaluate.py` also accepts `gemini` in its env check, but `utils.get_llm` rejects it.
- Pulling any `owner/name` prompt requires `dangerously_pull_public_prompt=True`.
- `USERNAME_LANGSMITH_HUB` is a public Hub handle that only exists after a prompt has been made public once (steps in the README).
- `utils.validate_prompt_structure` expects `description`, `system_prompt`, `version`, and at least 2 `techniques_applied` as keys of the dict it receives, but `bug_to_user_story_v1.yml` nests its fields under the prompt name. If v2 follows that layout, pass the inner dict to the validator.
- The v2 prompt must use Few-shot plus at least one other technique, and the tests expect a persona, a required format, examples, no `[TODO]`, and at least 2 techniques listed in the YAML metadata.
- Each evaluation makes about 60 LLM calls (15 answers and 45 judge calls). Some Gemini free-tier models allow only 20 requests per day, which ends a run early with 429 errors, and failed examples score 0.0. All-zero scores mean a technical failure, so read the run errors in LangSmith. `gemini-3.1-flash-lite` completed a full run on the free tier.
- A model listed by the Gemini API may still be unusable: `gemini-2.5-flash` returned 404 for new users and `gemini-3.8-flash` timed out.
