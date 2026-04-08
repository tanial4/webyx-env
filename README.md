---
title: OpenEnv Webyx Accessibility Benchmark
emoji: 👁️
colorFrom: green
colorTo: blue
sdk: docker
pinned: false
app_port: 8000
base_path: /
tags:
  - openenv
  - reinforcement-learning
  - accessibility
---

# Webyx Accessibility Benchmark

`webyx_env` is an OpenEnv reinforcement-learning environment for benchmarking web accessibility auditing agents. Each episode simulates a QA engineer reviewing and fixing HTML for WCAG violations.

## Environment design

- Observation includes the current HTML snippet, active WCAG violations, remaining counts by severity, and the current step budget.
- Action is structured as `detect`, `fix`, or `skip` with a CSS selector target and an optional proposed fix string.
- Reward gives positive signal for correct detection and remediation, penalizes invalid or ineffective fixes, and applies a stronger penalty for skipping level-A issues.
- Episode score is deterministic in `[0.0, 1.0]` and is exposed as `observation.episode_score`.
- Violations with dependencies are hidden until their prerequisites are resolved, requiring the agent to discover the correct remediation order.

## Observation space

| Field                | Type  | Description                                              |
| -------------------- | ----- | -------------------------------------------------------- |
| html_snippet         | str   | Current HTML page under audit                            |
| violations           | list  | Active WCAG violations with level, selector, description |
| remaining_violations | dict  | Violation count by level — A, AA, AAA                    |
| step_number          | int   | Current step in the episode                              |
| max_steps            | int   | Maximum steps allowed for this task                      |
| episode_score        | float | Current score in [0.0, 1.0]                              |

## Action space

| Field        | Type | Values                                              |
| ------------ | ---- | --------------------------------------------------- |
| action_type  | enum | detect, fix, skip                                   |
| target       | str  | CSS selector of the element to act on               |
| proposed_fix | str  | HTML attribute fix, or empty string for detect/skip |

## Tasks

| Task     | Violations | Max steps | WCAG levels | Baseline score |
| -------- | ---------- | --------- | ----------- | -------------- |
| `easy`   | 4          | 8         | A           | 1.00           |
| `medium` | 4          | 10        | AA          | 1.00           |
| `hard`   | 8          | 16        | A, AA, AAA  | 1.00           |

- `easy`: add non-empty `alt` attributes to four marketing images.
- `medium`: repair AA form issues including missing labels, unnamed controls, and low-contrast text.
- `hard`: audit a mixed-severity page with landmark, alt text, lang, autocomplete, label, contrast, role, and AAA readability issues. Two violations are locked behind dependencies and only appear after their prerequisites are fixed.

`reset(task_id=...)` accepts `"easy"`, `"medium"`, or `"hard"` for deterministic task selection. Without a `task_id`, tasks cycle in order.

## Baseline scores

Measured with `Qwen/Qwen2.5-72B-Instruct` via HuggingFace Inference Router:
[START] task=easy env=webyx_env model=Qwen/Qwen2.5-72B-Instruct
[STEP] step=1 action=fix('#hero','alt="Hero image"') reward=0.40 done=false error=null
[STEP] step=2 action=fix('#team','alt="Team photo"') reward=0.40 done=false error=null
[STEP] step=3 action=fix('#office','alt="Office space"') reward=0.40 done=false error=null
[STEP] step=4 action=fix('#award','alt="Award ceremony"') reward=0.40 done=true error=null
[END] success=true steps=4 score=1.00 rewards=0.40,0.40,0.40,0.40
[START] task=medium env=webyx_env model=Qwen/Qwen2.5-72B-Instruct
[STEP] step=1 action=fix('#full-name','<label for="full-name">Full name</label>') reward=0.30 done=false error=null
[STEP] step=2 action=fix('#email','<label for="email">Email address</label>') reward=0.30 done=false error=null
[STEP] step=3 action=fix('#submit-btn','aria-label="Submit"') reward=0.30 done=false error=null
[STEP] step=4 action=fix('#lead','class="muted high-contrast"') reward=0.30 done=true error=null
[END] success=true steps=4 score=1.00 rewards=0.30,0.30,0.30,0.30
[START] task=hard env=webyx_env model=Qwen/Qwen2.5-72B-Instruct
[STEP] step=1 action=fix('#nav-links','<nav id="nav-links">...</nav>') reward=0.40 done=false error=null
[STEP] step=2 action=fix('#feature-shot','alt="Feature image description"') reward=0.40 done=false error=null
[STEP] step=3 action=fix('#page-root','lang="en"') reward=0.40 done=false error=null
[STEP] step=4 action=fix('#shipping-name','<label for="shipping-name">Shipping Name</label>') reward=0.30 done=false error=null
[STEP] step=5 action=fix('#shipping-email','autocomplete="email"') reward=0.30 done=false error=null
[STEP] step=6 action=fix('#fine-print','class="muted high-contrast tiny"') reward=0.30 done=false error=null
[STEP] step=7 action=fix('#promo-banner','role="region"') reward=0.20 done=false error=null
[STEP] step=8 action=fix('#fine-print','class="muted high-contrast"') reward=0.20 done=true error=null
[END] success=true steps=8 score=1.00 rewards=0.40,0.40,0.40,0.30,0.30,0.30,0.20,0.20

## Reward structure

| Action           | Level A | Level AA | Level AAA |
| ---------------- | ------- | -------- | --------- |
| `detect` correct | +0.15   | +0.10    | +0.10     |
| `fix` correct    | +0.40   | +0.30    | +0.20     |
| `skip`           | -0.20   | -0.10    | -0.10     |
| Wrong target     | -0.20   | -0.20    | -0.20     |
| Invalid action   | -0.10   | -0.10    | -0.10     |

## Quick start

```bash
# Install dependencies
pip install -e .
# Start the server
uvicorn server.app:app --host 0.0.0.0 --port 8000
```

Example client usage:

```python
from webyx_env.client import WebyxEnv
from webyx_env.models import WebyxAction

env = WebyxEnv(base_url="http://localhost:8000")
result = await env.reset(task_id="easy")
print(result.observation.task_id)
print(result.observation.violations)

result = await env.step(
    WebyxAction(
        action_type="fix",
        target="#hero",
        proposed_fix='alt="Hero banner showcasing the product"',
    )
)
print(result.reward)
print(result.observation.episode_score)
```

## Valid fix formats

- Alt text: `alt="Descriptive text"`
- Label insertion: `<label for="email">Email address</label>`
- Accessible name: `aria-label="Submit form"`
- Class update: `class="muted high-contrast"`
- Autocomplete: `autocomplete="email"`
- Lang attribute: `lang="en"`
- Role attribute: `role="region"`
- Landmark replacement: `<nav id="nav-links">...</nav>`

## Validation

```bash
openenv validate .
```
