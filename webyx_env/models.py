from typing import Dict, List, Literal

from openenv.core.env_server.types import Action, Observation
from pydantic import BaseModel
from pydantic import Field


class ViolationView(BaseModel):
    level: Literal["A", "AA", "AAA"] = Field(..., description="WCAG severity level")
    selector: str = Field(..., description="CSS selector pointing to the affected element")
    description: str = Field(..., description="Human-readable accessibility issue")


class WebyxAction(Action):
    action_type: str = Field(
        ..., description="Type of action to perform for accessibility auditing"
    )
    target: str = Field(..., description="CSS selector of the element being acted on")
    proposed_fix: str = Field(
        default="",
        description="Corrected HTML attribute, text, class, or element markup",
    )


class WebyxObservation(Observation):
    task_id: str = Field(..., description="Current benchmark task identifier")
    task_title: str = Field(..., description="Human-readable task title")
    html_snippet: str = Field(..., description="Current HTML page under audit")
    violations: List[ViolationView] = Field(
        default_factory=list,
        description="Detected violations that remain active in the current HTML",
    )
    remaining_violations: Dict[str, int] = Field(
        default_factory=dict,
        description="Remaining violations by WCAG level",
    )
    step_number: int = Field(default=0, description="Current step number")
    max_steps: int = Field(default=0, description="Maximum steps allowed for the task")
