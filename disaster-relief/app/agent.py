import os
from pydantic import BaseModel, Field
from typing import Literal, Optional

from google.adk.agents import Agent
from google.adk.apps import App
from google.adk.models import Gemini
from google.genai import types

from app.prompts import CLASSIFIER_INSTRUCTION


class ClassificationResult(BaseModel):
    route: Literal["shelter", "medical", "emergency"] = Field(
        description="The target category for routing the request. Use 'emergency' for critical danger or vulnerable status, 'shelter' for evacuation/displacement/camps, and 'medical' for non-life-threatening medical questions."
    )
    priority: Literal["low", "medium", "high", "critical"] = Field(
        description="The priority level of the emergency request."
    )
    vulnerable_person: Optional[str] = Field(
        description="Type of vulnerable person if present (e.g. pregnant, infant, elderly, disabled, unconscious, chest pain, blocked roads). None if not specified."
    )
    disaster_type: Optional[str] = Field(
        description="The type of disaster identified (e.g. flood, landslide, cyclone, heavy rain). None if not specified."
    )


root_agent = Agent(
    name="classifier_agent",
    model=Gemini(
        model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction=CLASSIFIER_INSTRUCTION,
    output_schema=ClassificationResult,
    output_key="classification",
)

app = App(
    root_agent=root_agent,
    name="app",
)
