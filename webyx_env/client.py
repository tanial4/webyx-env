from typing import Dict, Optional

from openenv.core import EnvClient
from openenv.core.client_types import StepResult
from openenv.core.env_server.types import State

from .models import ViolationView, WebyxAction, WebyxObservation


class WebyxEnv(EnvClient[WebyxAction, WebyxObservation, State]):

    def _reset_payload(self, task_id: Optional[str] = None) -> Dict:
        if task_id is not None:
            return {"task_id": task_id}
        return {}

    def _step_payload(self, action: WebyxAction) -> Dict:
        return {
            "action_type": action.action_type,
            "target": action.target,
            "proposed_fix": action.proposed_fix,
        }

    def _parse_result(self, payload: Dict) -> StepResult[WebyxObservation]:
        obs_data = payload.get("observation", {})
        observation = WebyxObservation(
            task_id=obs_data.get("task_id", ""),
            task_title=obs_data.get("task_title", ""),
            html_snippet=obs_data.get("html_snippet", ""),
            violations=[ViolationView(**item) for item in obs_data.get("violations", [])],
            remaining_violations=obs_data.get("remaining_violations", {}),
            step_number=obs_data.get("step_number", 0),
            max_steps=obs_data.get("max_steps", 0),
            done=payload.get("done", False),
            reward=payload.get("reward"),
            metadata=obs_data.get("metadata", {}),
        )
        return StepResult(
            observation=observation,
            reward=payload.get("reward"),
            done=payload.get("done", False),
        )

    def _parse_state(self, payload: Dict) -> State:
        return State(
            episode_id=payload.get("episode_id"),
            step_count=payload.get("step_count", 0),
        )