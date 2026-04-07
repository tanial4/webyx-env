from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Callable, List, Literal, Optional
from uuid import uuid4

from bs4 import BeautifulSoup
from openenv.core.env_server.interfaces import Environment
from openenv.core.env_server.types import State

try:
    from ..models import ViolationView, WebyxAction, WebyxObservation
except ImportError:
    from models import ViolationView, WebyxAction, WebyxObservation


Level = Literal["A", "AA", "AAA"]


@dataclass(frozen=True)
class ViolationSpec:
    violation_id: str
    level: Level
    selector: str
    description: str
    fix_checker: Callable[[BeautifulSoup], bool]
    apply_fix: Callable[[BeautifulSoup, str], bool]


@dataclass(frozen=True)
class TaskSpec:
    task_id: str
    title: str
    max_steps: int
    initial_html: str
    violations: List[ViolationSpec]


def _normalize_markup(markup: str) -> str:
    return " ".join(markup.split())


def _has_non_empty_alt(selector: str) -> Callable[[BeautifulSoup], bool]:
    def _check(soup: BeautifulSoup) -> bool:
        element = soup.select_one(selector)
        return bool(element and element.has_attr("alt") and str(element["alt"]).strip())

    return _check


def _apply_alt(selector: str) -> Callable[[BeautifulSoup, str], bool]:
    def _apply(soup: BeautifulSoup, proposed_fix: str) -> bool:
        element = soup.select_one(selector)
        if element is None:
            return False
        fix = proposed_fix.strip()
        if "=" not in fix:
            return False
        attr_name, raw_value = fix.split("=", 1)
        attr_name = attr_name.strip()
        value = raw_value.strip().strip('"').strip("'")
        if attr_name != "alt" or not value:
            return False
        element["alt"] = value
        return True

    return _apply


def _label_exists(for_id: str) -> Callable[[BeautifulSoup], bool]:
    def _check(soup: BeautifulSoup) -> bool:
        label = soup.select_one(f'label[for="{for_id}"]')
        return bool(label and label.get_text(strip=True))

    return _check


def _apply_label(before_selector: str, required_for: str) -> Callable[[BeautifulSoup, str], bool]:
    expected_open = f'<label for="{required_for}">'

    def _apply(soup: BeautifulSoup, proposed_fix: str) -> bool:
        target = soup.select_one(before_selector)
        if target is None:
            return False
        fix = proposed_fix.strip()
        normalized = _normalize_markup(fix)
        if not normalized.startswith(_normalize_markup(expected_open)) or not normalized.endswith("</label>"):
            return False
        replacement = BeautifulSoup(fix, "html.parser")
        label = replacement.find("label")
        if label is None or label.get("for") != required_for or not label.get_text(strip=True):
            return False
        target.insert_before(label)
        return True

    return _apply


def _button_has_accessible_name(selector: str) -> Callable[[BeautifulSoup], bool]:
    def _check(soup: BeautifulSoup) -> bool:
        button = soup.select_one(selector)
        if button is None:
            return False
        return bool(button.get("aria-label") or button.get_text(strip=True))

    return _check


def _apply_aria_label(selector: str) -> Callable[[BeautifulSoup, str], bool]:
    def _apply(soup: BeautifulSoup, proposed_fix: str) -> bool:
        button = soup.select_one(selector)
        if button is None:
            return False
        fix = proposed_fix.strip()
        if "=" not in fix:
            return False
        attr_name, raw_value = fix.split("=", 1)
        value = raw_value.strip().strip('"').strip("'")
        if attr_name.strip() != "aria-label" or not value:
            return False
        button["aria-label"] = value
        return True

    return _apply


def _has_high_contrast_class(selector: str) -> Callable[[BeautifulSoup], bool]:
    def _check(soup: BeautifulSoup) -> bool:
        element = soup.select_one(selector)
        if element is None:
            return False
        classes = element.get("class", [])
        return "high-contrast" in classes

    return _check


def _apply_class(selector: str, required_class: str) -> Callable[[BeautifulSoup, str], bool]:
    def _apply(soup: BeautifulSoup, proposed_fix: str) -> bool:
        element = soup.select_one(selector)
        if element is None:
            return False
        fix = proposed_fix.strip()
        if not fix.startswith('class="') or not fix.endswith('"'):
            return False
        classes = fix[len('class="') : -1].split()
        if required_class not in classes:
            return False
        element["class"] = classes
        return True

    return _apply


def _field_has_autocomplete(selector: str, expected_value: str) -> Callable[[BeautifulSoup], bool]:
    def _check(soup: BeautifulSoup) -> bool:
        element = soup.select_one(selector)
        return bool(element and element.get("autocomplete") == expected_value)

    return _check


def _apply_autocomplete(selector: str, expected_value: str) -> Callable[[BeautifulSoup, str], bool]:
    def _apply(soup: BeautifulSoup, proposed_fix: str) -> bool:
        element = soup.select_one(selector)
        if element is None:
            return False
        fix = proposed_fix.strip()
        if fix != f'autocomplete="{expected_value}"':
            return False
        element["autocomplete"] = expected_value
        return True

    return _apply


def _landmark_present(selector: str) -> Callable[[BeautifulSoup], bool]:
    def _check(soup: BeautifulSoup) -> bool:
        return soup.select_one(selector) is not None

    return _check


def _apply_replace_tag(selector: str, expected_tag: str) -> Callable[[BeautifulSoup, str], bool]:
    def _apply(soup: BeautifulSoup, proposed_fix: str) -> bool:
        element = soup.select_one(selector)
        if element is None:
            return False
        fix = proposed_fix.strip()
        replacement = BeautifulSoup(fix, "html.parser")
        new_tag = next((child for child in replacement.contents if getattr(child, "name", None)), None)
        if new_tag is None or new_tag.name != expected_tag:
            return False
        element.replace_with(new_tag)
        return True

    return _apply


def _skip_reward(level: Level) -> float:
    return -0.20 if level == "A" else -0.10


class WebyxEnvironment(Environment):
    SUPPORTS_CONCURRENT_SESSIONS: bool = True

    def __init__(self):
        self._state = State(episode_id=str(uuid4()), step_count=0)
        self._reset_count = 0
        self._task_index = -1
        self._tasks = self._build_tasks()
        self._task: TaskSpec | None = None
        self._soup: BeautifulSoup | None = None
        self._detected: set[str] = set()
        self._resolved: set[str] = set()
        self._cumulative_reward = 0.0

    def reset(self, task_id: Optional[str] = None) -> WebyxObservation:
        self._state = State(episode_id=str(uuid4()), step_count=0)
        self._reset_count += 1

        if task_id is not None:
            index = next((i for i, t in enumerate(self._tasks) if t.task_id == task_id), None)
            self._task_index = index if index is not None else (self._task_index + 1) % len(self._tasks)
        else:
            self._task_index = (self._task_index + 1) % len(self._tasks)

        self._task = deepcopy(self._tasks[self._task_index])
        self._soup = BeautifulSoup(self._task.initial_html, "html.parser")
        self._detected = set()
        self._resolved = set()
        self._cumulative_reward = 0.0
        return self._build_observation(reward=0.0, done=False, event="reset")

    def step(self, action: WebyxAction) -> WebyxObservation:  # type: ignore[override]
        if self._task is None or self._soup is None:
            return self.reset()

        self._state.step_count += 1

        reward = 0.0
        event = "noop"

        raw_action_type = getattr(action, "action_type", "")
        action_type = str(raw_action_type).split(".")[-1].strip().lower()

        raw_target = getattr(action, "target", "")
        target = str(raw_target).strip()

        raw_proposed_fix = getattr(action, "proposed_fix", "")
        proposed_fix = "" if raw_proposed_fix is None else str(raw_proposed_fix).strip()

        active = self._active_violations()
        violation = next((item for item in active if item.selector.strip() == target), None)

        if action_type == "detect":
            event = "detect"
            if violation is not None and violation.violation_id not in self._detected:
                self._detected.add(violation.violation_id)
                reward = 0.15 if violation.level == "A" else 0.10
            else:
                reward = -0.05

        elif action_type == "fix":
            event = "fix"
            if violation is None:
                reward = -0.20
            else:
                before_count = len(active)
                applied = violation.apply_fix(self._soup, proposed_fix)

                if applied:
                    active_after_apply = self._active_violations()
                    after_count = len(active_after_apply)
                    resolved = after_count < before_count and violation.fix_checker(self._soup)

                    if resolved:
                        self._resolved.add(violation.violation_id)
                        if violation.level == "A":
                            reward = 0.40
                        elif violation.level == "AA":
                            reward = 0.30
                        else:
                            reward = 0.20
                    else:
                        reward = -0.20
                else:
                    reward = -0.20

        elif action_type == "skip":
            event = "skip"
            if violation is None:
                reward = -0.05
            else:
                reward = _skip_reward(violation.level)

        else:
            event = "invalid_action"
            reward = -0.10

        active_after = self._active_violations()

        if len(active_after) > len(active):
            reward -= 0.20

        reward = max(-1.0, min(1.0, reward))

        self._cumulative_reward += reward
        done = not active_after or self._state.step_count >= self._task.max_steps

        return self._build_observation(reward=reward, done=done, event=event)

    @property
    def state(self) -> State:
        return self._state

    def _build_observation(self, reward: float, done: bool, event: str) -> WebyxObservation:
        assert self._task is not None and self._soup is not None
        active = self._active_violations()
        remaining = {"A": 0, "AA": 0, "AAA": 0}
        for violation in active:
            remaining[violation.level] += 1

        total_violations = len(self._task.violations)
        resolved_count = total_violations - len(active)
        detect_credit = len(self._detected) * 0.1
        score = min(1.0, max(0.0, (resolved_count + detect_credit) / total_violations))

        return WebyxObservation(
            task_id=self._task.task_id,
            task_title=self._task.title,
            html_snippet=self._format_html(),
            violations=[
                ViolationView(
                    level=item.level,
                    selector=item.selector,
                    description=item.description,
                )
                for item in active
            ],
            remaining_violations=remaining,
            step_number=self._state.step_count,
            max_steps=self._task.max_steps,
            done=done,
            reward=reward,
            metadata={
                "event": event,
                "episode_score": round(score, 4),
                "cumulative_reward": round(self._cumulative_reward, 4),
                "reset_count": self._reset_count,
            },
        )

    def _active_violations(self) -> List[ViolationSpec]:
        assert self._task is not None and self._soup is not None
        return [violation for violation in self._task.violations if not violation.fix_checker(self._soup)]

    def _format_html(self) -> str:
        assert self._soup is not None
        return self._soup.prettify()

    def _build_tasks(self) -> List[TaskSpec]:
        return [
            TaskSpec(
                task_id="easy",
                title="Missing alt text on marketing images",
                max_steps=8,
                initial_html="""
<section class="gallery">
  <img id="hero" src="/img/hero.jpg">
  <img id="team" src="/img/team.jpg">
  <img id="office" src="/img/office.jpg">
  <img id="award" src="/img/award.jpg">
</section>
""".strip(),
                violations=[
                    ViolationSpec("hero-alt", "A", "#hero", "Image is missing a non-empty alt attribute.", _has_non_empty_alt("#hero"), _apply_alt("#hero")),
                    ViolationSpec("team-alt", "A", "#team", "Image is missing a non-empty alt attribute.", _has_non_empty_alt("#team"), _apply_alt("#team")),
                    ViolationSpec("office-alt", "A", "#office", "Image is missing a non-empty alt attribute.", _has_non_empty_alt("#office"), _apply_alt("#office")),
                    ViolationSpec("award-alt", "A", "#award", "Image is missing a non-empty alt attribute.", _has_non_empty_alt("#award"), _apply_alt("#award")),
                ],
            ),
            TaskSpec(
                task_id="medium",
                title="AA form audit with labels and contrast fixes",
                max_steps=10,
                initial_html="""
<form id="signup-form">
  <p id="lead" class="muted">Join our release list for product updates.</p>
  <input id="full-name" type="text" placeholder="Full name">
  <input id="email" type="email" placeholder="Email address">
  <button id="submit-btn" type="submit"></button>
</form>
""".strip(),
                violations=[
                    ViolationSpec("name-label", "AA", "#full-name", "Text input is missing an associated label.", _label_exists("full-name"), _apply_label("#full-name", "full-name")),
                    ViolationSpec("email-label", "AA", "#email", "Email input is missing an associated label.", _label_exists("email"), _apply_label("#email", "email")),
                    ViolationSpec("button-name", "AA", "#submit-btn", "Submit button has no accessible name.", _button_has_accessible_name("#submit-btn"), _apply_aria_label("#submit-btn")),
                    ViolationSpec("lead-contrast", "AA", "#lead", "Lead text uses low contrast and must add the high-contrast class.", _has_high_contrast_class("#lead"), _apply_class("#lead", "high-contrast")),
                ],
            ),
            TaskSpec(
                task_id="hard",
                title="Full page audit with mixed A, AA and AAA issues",
                max_steps=12,
                initial_html="""
<div class="page-shell">
  <div id="nav-links">
    <a id="home-link" href="/home">Home</a>
    <a id="pricing-link" href="/pricing">Pricing</a>
  </div>
  <img id="feature-shot" src="/img/feature.png">
  <form id="checkout-form">
    <input id="shipping-name" type="text" placeholder="Shipping name">
    <input id="shipping-email" type="email" placeholder="Email">
  </form>
  <p id="fine-print" class="muted tiny">All offers expire in 24 hours.</p>
</div>
""".strip(),
                violations=[
                    ViolationSpec("nav-landmark", "A", "#nav-links", "Primary navigation must use a <nav> landmark.", _landmark_present("nav#nav-links"), _apply_replace_tag("#nav-links", "nav")),
                    ViolationSpec("feature-alt", "A", "#feature-shot", "Feature image is missing a non-empty alt attribute.", _has_non_empty_alt("#feature-shot"), _apply_alt("#feature-shot")),
                    ViolationSpec("shipping-name-label", "AA", "#shipping-name", "Shipping name input is missing an associated label.", _label_exists("shipping-name"), _apply_label("#shipping-name", "shipping-name")),
                    ViolationSpec("shipping-email-autocomplete", "AA", "#shipping-email", "Email field is missing the expected autocomplete token.", _field_has_autocomplete("#shipping-email", "email"), _apply_autocomplete("#shipping-email", "email")),
                    ViolationSpec("fine-print-contrast", "AA", "#fine-print", "Fine print requires the high-contrast class.", _has_high_contrast_class("#fine-print"), _apply_class("#fine-print", "high-contrast")),
                    ViolationSpec("fine-print-aaa", "AAA", "#fine-print", "AAA readability requires removing the tiny text class.", lambda soup: "tiny" not in (soup.select_one("#fine-print") or {}).get("class", []), self._apply_remove_class("#fine-print", "tiny")),
                ],
            ),
        ]

    @staticmethod
    def _apply_remove_class(selector: str, removable: str) -> Callable[[BeautifulSoup, str], bool]:
        def _apply(soup: BeautifulSoup, proposed_fix: str) -> bool:
            element = soup.select_one(selector)
            if element is None:
                return False
            fix = proposed_fix.strip()
            if not fix.startswith('class="') or not fix.endswith('"'):
                return False
            classes = [item for item in fix[len('class="') : -1].split() if item]
            if removable in classes:
                return False
            element["class"] = classes
            return True

        return _apply