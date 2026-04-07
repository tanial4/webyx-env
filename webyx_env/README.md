---
title: Webyx Accessibility Benchmark
emoji: 👁️
colorFrom: green
colorTo: blue
sdk: docker
pinned: false
app_port: 8000
base_path: /web
tags:
  - openenv
  - accessibility
  - reinforcement-learning
---

# Webyx Accessibility Benchmark

`webyx_env` is an OpenEnv reinforcement-learning environment for benchmarking web accessibility auditing agents. Each episode simulates a QA engineer reviewing and fixing HTML for WCAG violations.

## Environment design

- Observation includes the current HTML snippet, active WCAG violations, remaining counts by severity, and the current step budget.
- Action is structured as `detect`, `fix`, or `skip` with a CSS selector target and an optional proposed fix string.
- Reward gives positive signal for correct detection and remediation, penalizes invalid or ineffective fixes, and applies a stronger penalty for skipping level-A issues.
- Episode score is deterministic in `[0.0, 1.0]` and is exposed in `observation.metadata["episode_score"]`.

## Tasks

- `easy`: add non-empty `alt` attributes to four images.
- `medium`: repair AA form issues including missing labels, unnamed controls, and low-contrast text.
- `hard`: audit a mixed-severity page with landmark, alt text, autocomplete, label, contrast, and AAA readability issues.

`reset()` cycles through the tasks in the order above, which keeps evaluation deterministic.

## Quick start

```bash
python3 -m pip install -e .
python -m webyx_env.server.app --port 8000
```

Example client usage:

```python
from webyx_env import WebyxAction, WebyxEnv

with WebyxEnv(base_url="http://localhost:8000") as env:
    result = env.reset()
    print(result.observation.task_id)
    print(result.observation.violations)

    result = env.step(
        WebyxAction(
            action_type="fix",
            target="#hero",
            proposed_fix='alt="Hero banner showcasing the product"',
        )
    )
    print(result.reward)
    print(result.observation.metadata["episode_score"])
```

## Valid fix formats

- Alt text: `alt="Descriptive text"`
- Label insertion: `<label for="email">Email address</label>`
- Accessible name: `aria-label="Submit form"`
- Class update: `class="muted high-contrast"`
- Autocomplete: `autocomplete="email"`
- Landmark replacement: `<nav id="nav-links">...</nav>`

## Validation

```bash
openenv validate .
```
