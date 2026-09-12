import os
import json
import sqlite3
import webbrowser
import urllib.parse
import boto3
from typing import Dict, Any, List
from dotenv import load_dotenv

load_dotenv()

AWS_REGION = os.getenv("AWS_DEFAULT_REGION", "us-east-1")
NOVA_MODEL_ID = "us.amazon.nova-lite-v1:0"

# -------------------------------------------------------------------
# 1. User Preferences
# -------------------------------------------------------------------
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config", "user_config.json")

def load_user_config() -> Dict[str, Any]:
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "system_defaults": {"confirm_purchases": True, "confirm_destructive": True},
        "preferred_apps": {
            "scheduling": "google_calendar",
            "documentation": "notion",
            "shopping": "amazon",
            "media": "youtube"
        }
    }

# -------------------------------------------------------------------
# 2. Local Vault Persistence
# -------------------------------------------------------------------
conn = sqlite3.connect("orbit_vault.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute("""
    CREATE TABLE IF NOT EXISTS vault (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        category TEXT,
        summary TEXT,
        content TEXT,
        executed_app TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
""")
conn.commit()

def record_to_vault(category: str, summary: str, content: str, executed_app: str = "local_vault"):
    cursor.execute(
        "INSERT INTO vault (category, summary, content, executed_app) VALUES (?, ?, ?, ?)",
        (category, summary, content, executed_app)
    )
    conn.commit()

# -------------------------------------------------------------------
# 3. Guardrails
# -------------------------------------------------------------------
class SafetyGuardrailError(Exception):
    def __init__(self, message: str, category: str, payload: Dict[str, Any]):
        super().__init__(message)
        self.category = category
        self.payload = payload

# -------------------------------------------------------------------
# 4. Bedrock Client & Invocation Helper
# -------------------------------------------------------------------
bedrock = boto3.client("bedrock-runtime", region_name=AWS_REGION)

# pyrefly: ignore [bad-function-definition]
def call_bedrock(system_prompt: str, user_prompt: str, tools: list = None) -> dict:
    kwargs = {
        "modelId": NOVA_MODEL_ID,
        "system": [{"text": system_prompt}],
        "messages": [{"role": "user", "content": [{"text": user_prompt}]}]
    }
    if tools:
        # pyrefly: ignore [bad-assignment]
        kwargs["toolConfig"] = {"tools": tools}
    return bedrock.converse(**kwargs)

# -------------------------------------------------------------------
# 5. Specialized Sub-Agents
# -------------------------------------------------------------------
from tools.screen_workers import (
    automate_calendar_schedule_and_save,
    automate_youtube_and_queue,
    automate_amazon_cart_addition
)

def scheduling_sub_agent(task_instruction: str) -> Dict[str, Any]:
    config = load_user_config()
    target_app = config.get("preferred_apps", {}).get("scheduling", "google_calendar")

    # Have Nova extract clean title and date parameters
    prompt = f"Extract the event title from: '{task_instruction}'"
    tools = [{
        "toolSpec": {
            "name": "create_event",
            "description": "Create calendar event",
            "inputSchema": {
                "json": {
                    "type": "object",
                    "properties": {"title": {"type": "string"}},
                    "required": ["title"]
                }
            }
        }
    }]
    res = call_bedrock("You are the Scheduling Agent. Return the event name.", prompt, tools)
    title = task_instruction
    blocks = res.get("output", {}).get("message", {}).get("content", [])
    for b in blocks:
        if "toolUse" in b:
            title = b["toolUse"]["input"].get("title", task_instruction)

    # Physically drives the browser to populate and click Save
    worker_res = automate_calendar_schedule_and_save(title)
    record_to_vault("scheduling", title, task_instruction, target_app)
    return {"agent": "Scheduling Specialist", "app": target_app, "detail": worker_res["status"]}

def commerce_sub_agent(task_instruction: str, user_confirmed: bool) -> Dict[str, Any]:
    config = load_user_config()
    target_app = config.get("preferred_apps", {}).get("shopping", "amazon")

    cleaned_item = task_instruction.replace("buy", "").replace("order", "").strip()
    payload = {"item": cleaned_item}

    if config.get("system_defaults", {}).get("confirm_purchases", True) and not user_confirmed:
        raise SafetyGuardrailError(
            f"Commerce Agent intercepted: Do you want to proceed with checking out '{cleaned_item}' on {target_app}?",
            "shopping",
            payload
        )

    # Physically navigates Amazon, finds the product, and hits Add to Cart
    worker_res = automate_amazon_cart_addition(cleaned_item)
    record_to_vault("shopping", cleaned_item, task_instruction, target_app)
    return {"agent": "Commerce Specialist", "app": target_app, "detail": worker_res["status"]}

def knowledge_sub_agent(task_instruction: str) -> Dict[str, Any]:
    task_low = task_instruction.lower()
    config = load_user_config()

    if any(k in task_low for k in ["youtube", "lecture", "video", "watch"]):
        target_app = config.get("preferred_apps", {}).get("media", "youtube")
        query = task_instruction.replace("queue", "").replace("on youtube", "").strip()
        # Physically drives YouTube and begins playback
        worker_res = automate_youtube_and_queue(query)
        record_to_vault("media", query, task_instruction, target_app)
        return {"agent": "Knowledge Specialist", "app": target_app, "detail": worker_res["status"]}
    else:
        record_to_vault("vault", task_instruction[:40], task_instruction, "local_vault")
        return {"agent": "Knowledge Specialist", "app": "local_vault", "detail": f"Stored in Vault: '{task_instruction}'"}


# -------------------------------------------------------------------
# 6. Root Supervisor Agent (Delegator)
# -------------------------------------------------------------------
SUPERVISOR_TOOLS = [{
    "toolSpec": {
        "name": "delegate_task",
        "description": "Delegates a specific sub-task to a specialized worker agent.",
        "inputSchema": {
            "json": {
                "type": "object",
                "properties": {
                    "target_agent": {
                        "type": "string",
                        "enum": ["scheduling", "commerce", "knowledge"],
                        "description": "The specialist agent to execute the task"
                    },
                    "instruction": {
                        "type": "string",
                        "description": "The exact sub-task description for that agent"
                    }
                },
                "required": ["target_agent", "instruction"]
            }
        }
    }
}]

SUPERVISOR_PROMPT = """
You are the Root Supervisor Agent of the Orbit system.
Break down complex, multi-intent voice requests into individual tasks and delegate each to the correct specialist:
- 'scheduling': calendar events, meetings, deadlines.
- 'commerce': buying, purchasing, cart additions.
- 'knowledge': notes, reminders, passcodes, YouTube lectures, vault facts.

Call delegate_task for every independent intent found.
"""

class OrbitResponse:
    def __init__(self, text: str, tool_calls: List[Dict[str, Any]]):
        self.text = text
        self.tool_calls = tool_calls

def orbit_agent(prompt: str, user_confirmed: bool = False) -> OrbitResponse:
    res = call_bedrock(SUPERVISOR_PROMPT, prompt, SUPERVISOR_TOOLS)
    output_blocks = res.get("output", {}).get("message", {}).get("content", [])

    delegated_results = []
    spoken_summary = ""

    for block in output_blocks:
        if "text" in block:
            spoken_summary += block["text"]
        elif "toolUse" in block:
            inp = block["toolUse"].get("input", {})
            agent_type = inp.get("target_agent")
            instruction = inp.get("instruction")

            if agent_type == "scheduling":
                result = scheduling_sub_agent(instruction)
            elif agent_type == "commerce":
                result = commerce_sub_agent(instruction, user_confirmed)
            elif agent_type == "knowledge":
                result = knowledge_sub_agent(instruction)
            else:
                result = {"agent": "System", "app": "vault", "detail": instruction}

            delegated_results.append({"name": f"{agent_type}_agent", "input": result})

    if not spoken_summary.strip():
        spoken_summary = f"Root Supervisor coordinated {len(delegated_results)} specialist agents across your system."

    return OrbitResponse(spoken_summary, delegated_results)