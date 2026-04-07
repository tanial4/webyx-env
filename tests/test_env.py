# tests/test_environment.py

import pytest
from webyx_env.models import WebyxAction
from webyx_env.server.webyx_env_environment import WebyxEnvironment


@pytest.fixture
def env():
    e = WebyxEnvironment()
    e.reset(task_id="easy")
    return e


def test_reset_easy(env):
    obs = env.reset(task_id="easy")
    assert obs.task_id == "easy"
    assert obs.step_number == 0
    assert obs.done == False
    assert obs.reward == 0.0
    assert obs.episode_score == 0.0
    assert len(obs.violations) == 4


def test_reset_medium():
    env = WebyxEnvironment()
    obs = env.reset(task_id="medium")
    assert obs.task_id == "medium"
    assert len(obs.violations) == 4
    assert obs.remaining_violations["AA"] == 4


def test_reset_hard():
    env = WebyxEnvironment()
    obs = env.reset(task_id="hard")
    assert obs.task_id == "hard"
    assert len(obs.violations) == 6
    assert obs.remaining_violations["A"] == 2
    assert obs.remaining_violations["AA"] == 3
    assert obs.remaining_violations["AAA"] == 1


def test_fix_correct_gives_positive_reward(env):
    action = WebyxAction(
        action_type="fix",
        target="#hero",
        proposed_fix='alt="Hero image"',
    )
    obs = env.step(action)
    assert obs.reward == 0.40
    assert obs.metadata["event"] == "fix"
    assert len(obs.violations) == 3


def test_fix_incorrect_gives_negative_reward(env):
    action = WebyxAction(
        action_type="fix",
        target="#hero",
        proposed_fix='alt=""',
    )
    obs = env.step(action)
    assert obs.reward == -0.20


def test_fix_wrong_target_gives_negative_reward(env):
    action = WebyxAction(
        action_type="fix",
        target="#nonexistent",
        proposed_fix='alt="Hero image"',
    )
    obs = env.step(action)
    assert obs.reward == -0.20


def test_detect_correct_gives_positive_reward(env):
    action = WebyxAction(
        action_type="detect",
        target="#hero",
        proposed_fix="",
    )
    obs = env.step(action)
    assert obs.reward == 0.15
    assert obs.metadata["event"] == "detect"


def test_detect_duplicate_gives_penalty(env):
    action = WebyxAction(action_type="detect", target="#hero", proposed_fix="")
    env.step(action)
    obs = env.step(action)
    assert obs.reward == -0.05


def test_skip_level_a_gives_penalty(env):
    action = WebyxAction(action_type="skip", target="#hero", proposed_fix="")
    obs = env.step(action)
    assert obs.reward == -0.20


def test_invalid_action_gives_penalty(env):
    action = WebyxAction(action_type="banana", target="#hero", proposed_fix="")
    obs = env.step(action)
    assert obs.reward == -0.10
    assert obs.metadata["event"] == "invalid_action"


def test_episode_score_increases_with_fixes(env):
    assert env.reset(task_id="easy").episode_score == 0.0
    action = WebyxAction(action_type="fix", target="#hero", proposed_fix='alt="Hero image"')
    obs = env.step(action)
    assert obs.episode_score > 0.0


def test_done_when_all_violations_fixed():
    env = WebyxEnvironment()
    env.reset(task_id="easy")
    fixes = [
        ("#hero", 'alt="Hero image"'),
        ("#team", 'alt="Team photo"'),
        ("#office", 'alt="Office space"'),
        ("#award", 'alt="Award ceremony"'),
    ]
    obs = None
    for target, fix in fixes:
        obs = env.step(WebyxAction(action_type="fix", target=target, proposed_fix=fix))
    assert obs.done == True
    assert obs.episode_score == 1.0


def test_deterministic_same_fix_same_reward():
    rewards = []
    for _ in range(3):
        env = WebyxEnvironment()
        env.reset(task_id="easy")
        obs = env.step(WebyxAction(action_type="fix", target="#hero", proposed_fix='alt="Hero image"'))
        rewards.append(obs.reward)
    assert rewards[0] == rewards[1] == rewards[2]


def test_reset_invalid_task_id_cycles_normally():
    env = WebyxEnvironment()
    obs = env.reset(task_id="nonexistent")
    assert obs.task_id in ["easy", "medium", "hard"]


def test_step_before_reset_triggers_auto_reset():
    env = WebyxEnvironment()
    action = WebyxAction(action_type="detect", target="#hero", proposed_fix="")
    obs = env.step(action)
    assert obs.task_id in ["easy", "medium", "hard"]