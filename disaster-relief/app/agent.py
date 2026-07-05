import os
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env"), override=True)
os.environ["GEMINI_MODEL"] = "gemini-2.0-flash"

from pydantic import BaseModel, Field
from typing import Literal, Optional

from google.adk.agents import Agent
from google.adk.apps import App
from google.adk.models import Gemini
from google.adk.workflow import Workflow
from google.adk.agents.context import Context
from google.adk.events.event import Event
from google.genai import types

from app.prompts import CLASSIFIER_INSTRUCTION, SHELTER_INSTRUCTION, MEDICAL_INSTRUCTION, EMERGENCY_INSTRUCTION, GENERAL_INSTRUCTION, GUIDANCE_INSTRUCTION
from app.tools import lookup_shelters, lookup_hospitals, lookup_helplines
from app.rag_pipeline import retrieve_knowledge


# --- 1. Schemas ---

class ClassificationResult(BaseModel):
    route: Literal["shelter", "medical", "emergency", "general", "guidance"] = Field(
        description="The target category for routing the request. Use 'emergency' for critical danger or vulnerable status, 'shelter' for evacuation/displacement/camps, 'medical' for non-life-threatening medical questions, 'general' for generic greetings, and 'guidance' for general recovery instructions or disaster safety guidelines."
    )
    priority: Literal["low", "medium", "high", "critical"] = Field(
        description="The priority level of the emergency request."
    )
    vulnerable_person: Optional[str] = Field(
        default=None,
        description="Type of vulnerable person if present (e.g. pregnant, infant, elderly, disabled, unconscious, chest pain, blocked roads). None if not specified."
    )
    disaster_type: Optional[str] = Field(
        default=None,
        description="The type of disaster identified (e.g. flood, landslide, cyclone, heavy rain). None if not specified."
    )


# --- 2. Agents ---

classifier_agent = Agent(
    name="classifier_agent",
    model=Gemini(
        model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction=CLASSIFIER_INSTRUCTION,
    output_schema=ClassificationResult,
    output_key="classification",
)

shelter_agent = Agent(
    name="shelter_agent",
    model=Gemini(
        model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction=SHELTER_INSTRUCTION,
    tools=[lookup_shelters],
)

medical_agent = Agent(
    name="medical_agent",
    model=Gemini(
        model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction=MEDICAL_INSTRUCTION,
    tools=[lookup_hospitals],
)

emergency_agent = Agent(
    name="emergency_agent",
    model=Gemini(
        model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction=EMERGENCY_INSTRUCTION,
    tools=[lookup_helplines],
)

general_agent = Agent(
    name="general_agent",
    model=Gemini(
        model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction=GENERAL_INSTRUCTION,
)

guidance_agent = Agent(
    name="guidance_agent",
    model=Gemini(
        model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction=GUIDANCE_INSTRUCTION,
    tools=[retrieve_knowledge],
)


# --- 3. Workflow Nodes & Routing ---

def route_decision(ctx: Context, node_input: dict) -> Event:
    """Extracts classification results, updates state, checks escalation rules, and routes."""
    # Check if classifier results are wrapped under 'classification' key
    classification = node_input.get("classification")
    
    if classification:
        if isinstance(classification, dict):
            route = classification.get("route", "shelter")
            priority = classification.get("priority", "medium")
            vulnerable_person = classification.get("vulnerable_person")
            disaster_type = classification.get("disaster_type")
        else:  # Pydantic schema object
            route = getattr(classification, "route", "shelter")
            priority = getattr(classification, "priority", "medium")
            vulnerable_person = getattr(classification, "vulnerable_person", None)
            disaster_type = getattr(classification, "disaster_type", None)
    else:
        route = node_input.get("route", "shelter")
        priority = node_input.get("priority", "medium")
        vulnerable_person = node_input.get("vulnerable_person")
        disaster_type = node_input.get("disaster_type")

    # Critical Escalation Conditions:
    # pregnant, infant, elderly, disabled, unconscious, chest pain, blocked roads, priority == critical
    escalation_triggers = {
        "pregnant", "infant", "elderly", "disabled", "unconscious", "chest pain", "blocked roads"
    }
    
    is_vulnerable = str(vulnerable_person).lower() in escalation_triggers if vulnerable_person else False
    
    if (priority == "critical" and route != "shelter") or is_vulnerable:
        route = "emergency"

    # Merge into context state
    state_updates = {
        "route": route,
        "priority": priority,
        "vulnerable_person": vulnerable_person,
        "disaster_type": disaster_type,
    }

    return Event(
        output=node_input,
        route=route,
        state=state_updates
    )


# --- 4. Workflow Definition ---

root_agent = Workflow(
    name="disaster_relief_workflow",
    edges=[
        ('START', classifier_agent),
        (classifier_agent, route_decision),
        (route_decision, {
            "shelter": shelter_agent,
            "medical": medical_agent,
            "emergency": emergency_agent,
            "general": general_agent,
            "guidance": guidance_agent,
        }),
    ],
)

app = App(
    root_agent=root_agent,
    name="app",
)
