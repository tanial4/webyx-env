import asyncio
import json
import os
import textwrap
from typing import List, Optional

from openai import OpenAI

from webyx_env.client import WebyxEnv
from webyx_env.models import WebyxAction, WebyxObservation

IMAGE_NAME = os.getenv("LOCAL_IMAGE_NAME", "webyx-env")
HF_SPACE_URL = os.getenv("HF_SPACE_URL")
API_KEY = os.getenv("HF_TOKEN") or os.getenv("API_KEY")
API_BASE_URL = os.getenv("API_BASE_URL", "https://router.huggingface.co/v1")
MODEL_NAME = os.getenv("MODEL_NAME", "Qwen/Qwen2.5-72B-Instruct")

if not API_KEY:
    raise ValueError("HF_TOKEN o API_KEY no definido en .env")

BENCHMARK = "webyx_env"
TASKS = ["easy", "medium", "hard"]
MAX_STEPS = 12
SUCCESS_SCORE_THRESHOLD = 0.5

SYSTEM_PROMPT = textwrap.dedent("""
    You are an accessibility auditing agent. You interact with HTML pages and must
    fix WCAG violations to make the page accessible.

    You can perform exactly three action types:
    - detect: identify a violation on a specific element
    - fix: apply a concrete HTML attribute fix to resolve a violation
    - skip: skip a violation you cannot fix

    On each step you receive:
    - The current HTML snippet
    - A list of remaining violations with their CSS selector and description
    - Your current step number and max steps allowed

    Respond with a JSON object with exactly these fields:
    {
      "action_type": "detect" | "fix" | "skip",
      "target": "<css selector from the violations list>",
      "proposed_fix": "<attribute fix e.g. alt=\\"Hero image\\"> or empty string"
    }

    Fix format examples:
    - Missing alt:      alt="Descriptive text"
    - Missing label:    <label for="input-id">Label text</label>
    - Missing aria:     aria-label="Submit form"
    - Missing contrast: class="muted high-contrast"
    - Autocomplete:     autocomplete="email"
    - Nav landmark:     <nav id="nav-links"><a id="home-link" href="/home">Home</a></nav>

    Rules:
    - Always target a selector that appears in the violations list
    - proposed_fix must be non-empty for fix actions
    - proposed_fix must be empty string for detect and skip actions
    - Prioritize level A violations first, then AA, then AAA
    - Never repeat the same fix twice
    - Respond with raw JSON only — no markdown, no explanation
""").strip()


def log_start(task: str, env: str, model: str) -> None:
    print(f"[START] task={task} env={env} model={model}", flush=True)


def log_step(step: int, action: str, reward: float, done: bool, error: Optional[str]) -> None:
    error_val = error if error else "null"
    print(f"[STEP] step={step} action={action} reward={reward:.2f} done={str(done).lower()} error={error_val}", flush=True)


def log_end(success: bool, steps: int, score: float, rewards: List[float]) -> None:
    rewards_str = ",".join(f"{r:.2f}" for r in rewards)
    print(f"[END] success={str(success).lower()} steps={steps} score={score:.2f} rewards={rewards_str}", flush=True)


def build_user_prompt(obs: WebyxObservation, history: List[str]) -> str:
    violations_block = "\n".join(
        f"  - [{v.level}] {v.selector}: {v.description}"
        for v in obs.violations
    ) or "  None remaining"

    history_block = "\n".join(history[-4:]) if history else "None"

    return textwrap.dedent(f"""
        Task: {obs.task_title}
        Step: {obs.step_number} / {obs.max_steps}

        Remaining violations:
        {violations_block}

        Remaining by level: {obs.remaining_violations}

        Recent history:
        {history_block}

        HTML (current state):
        {obs.html_snippet[:2000]}

        Respond with a JSON object only.
    """).strip()


def get_action(client: OpenAI, obs: WebyxObservation, history: List[str]) -> WebyxAction:
    user_prompt = build_user_prompt(obs, history)
    try:
        completion = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,
            max_tokens=200,
            stream=False,
        )
        text = (completion.choices[0].message.content or "").strip()
        text = text.strip("```json").strip("```").strip()
        data = json.loads(text)
        return WebyxAction(
            action_type=data.get("action_type", "skip"),
            target=data.get("target", ""),
            proposed_fix=data.get("proposed_fix", ""),
        )
    except Exception as exc:
        print(f"[DEBUG] model error: {exc}", flush=True)
        if obs.violations:
            return WebyxAction(action_type="skip", target=obs.violations[0].selector, proposed_fix="")
        return WebyxAction(action_type="skip", target="", proposed_fix="")


def calculate_score(obs: WebyxObservation, rewards: List[float]) -> float:
    return round(min(max(obs.episode_score, 0.0), 1.0), 2)


async def run_episode(env: WebyxEnv, client: OpenAI, task_id: str) -> None:
    history: List[str] = []
    rewards: List[float] = []
    steps_taken = 0
    score = 0.0
    success = False

    try:
        result = await env.reset(task_id=task_id)
        obs: WebyxObservation = result.observation

        log_start(task=obs.task_id, env=BENCHMARK, model=MODEL_NAME)

        for step in range(1, MAX_STEPS + 1):
            if result.done:
                break

            action = get_action(client, obs, history)

            result = await env.step(action)
            obs = result.observation

            reward = result.reward or 0.0
            done = result.done
            rewards.append(reward)
            steps_taken = step

            action_str = f"{action.action_type}('{action.target}','{action.proposed_fix}')"
            log_step(step=step, action=action_str, reward=reward, done=done, error=None)

            history.append(
                f"Step {step}: {action.action_type} {action.target} "
                f"fix='{action.proposed_fix}' -> reward={reward:+.2f}"
            )

            if done:
                break

        score = calculate_score(obs, rewards)
        success = score >= SUCCESS_SCORE_THRESHOLD

    except Exception as e:
        print(f"[DEBUG] episode error ({task_id}): {e}", flush=True)

    finally:
        log_end(success=success, steps=steps_taken, score=score, rewards=rewards)


async def main() -> None:
    client = OpenAI(base_url=API_BASE_URL, api_key=API_KEY)

    if HF_SPACE_URL:
        env = WebyxEnv(base_url=HF_SPACE_URL)
    else:
        env = await WebyxEnv.from_docker_image(IMAGE_NAME)

    try:
        for task_id in TASKS:
            await run_episode(env, client, task_id)
    finally:
        try:
            await env.close()
        except Exception:
            pass


if __name__ == "__main__":
    asyncio.run(main())