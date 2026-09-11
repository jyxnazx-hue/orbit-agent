import os
import sqlite3
from typing import Dict, Any, List
from dotenv import load_dotenv

from hooks.security_guard import evaluate_tool_safety, SafetyGuardrailError

load_dotenv()

USE_MOCK_BEDROCK = os.getenv("USE_MOCK_BEDROCK", "false").lower() == "true"

# -------------------------------------------------------------------
# 1. Native Fallback SQLite Store
# -------------------------------------------------------------------
conn = sqlite3.connect("orbit_vault.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute("""
    CREATE TABLE IF NOT EXISTS vault (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        category TEXT,
        summary TEXT,
        content TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
""")
conn.commit()

# -------------------------------------------------------------------
# 2. Tool Implementations
# -------------------------------------------------------------------
def save_to_orbit_vault(category: str, summary: str, content: str) -> Dict[str, Any]:
    cursor.execute(
        "INSERT INTO vault (category, summary, content) VALUES (?, ?, ?)",
        (category, summary, content)
    )
    conn.commit()
    return {
        "tool": "Local Vault",
        "action": "saved_locally",
        "category": category,
        "summary": summary,
        "deep_link": f"orbit://vault?category={category.lower().replace(' ', '_')}"
    }

def manage_calendar_event(action_type: str, title: str, start_time: str, end_time: str = "") -> Dict[str, Any]:
    query_title = title.replace(" ", "+")
    deep_link = f"https://calendar.google.com/calendar/r/eventedit?text={query_title}&dates={start_time}/{end_time}"
    return {
        "tool": "Google Calendar",
        "action": action_type,
        "title": title,
        "time_window": f"{start_time} - {end_time}",
        "deep_link": deep_link
    }

def append_to_notion(page_title: str, summary_content: str, category: str = "Inbox") -> Dict[str, Any]:
    page_slug = page_title.lower().replace(" ", "-")
    return {
        "tool": "Notion",
        "action": "appended_note",
        "title": page_title,
        "category": category,
        "summary": summary_content,
        "deep_link": f"notion://www.notion.so/{page_slug}"
    }

def search_and_queue_media(query: str, playlist_name: str = "Study") -> Dict[str, Any]:
    deep_link = f"https://www.youtube.com/results?search_query={query.replace(' ', '+')}"
    return {
        "tool": "YouTube",
        "action": "queued_video",
        "playlist": playlist_name,
        "query": query,
        "deep_link": deep_link
    }

def delete_event(event_id: str, title: str) -> Dict[str, Any]:
    """Destructive operation: removes an event from calendar."""
    return {
        "tool": "Google Calendar",
        "action": "deleted",
        "title": title,
        "event_id": event_id
    }

# -------------------------------------------------------------------
# 3. Agent Execution Engine
# -------------------------------------------------------------------
if not USE_MOCK_BEDROCK:
    from strands import Agent, tool
    from strands.models import BedrockModel
    from strands.hooks import BeforeToolCallEvent

    def strands_security_hook(event: BeforeToolCallEvent):
        tool_use = getattr(event, "tool_use", {})
        name = tool_use.get("name") if isinstance(tool_use, dict) else getattr(tool_use, "name", None)
        inp = tool_use.get("input", {}) if isinstance(tool_use, dict) else getattr(tool_use, "input", {})
        # pyrefly: ignore [bad-argument-type]
        evaluate_tool_safety(name, inp, user_confirmed=inp.get("user_confirmed", False))

    bedrock_model = BedrockModel(model_id="us.anthropic.claude-sonnet-4-5-20250929-v1:0")

    orbit_agent = Agent(
        model=bedrock_model,
        tools=[
            tool(manage_calendar_event),
            tool(append_to_notion),
            tool(search_and_queue_media),
            tool(save_to_orbit_vault),
            tool(delete_event)
        ],
        hooks=[strands_security_hook],
        system_prompt="""
        You are Orbit, an autonomous life orchestrator. Route spoken queries to Calendar, Notion, YouTube, or Local Vault.
        Always output clean action intents.
        """
    )
else:
    def orbit_agent(prompt: str, user_confirmed: bool = False):
        class MockResponse:
            def __init__(self, text: str, tool_calls: List[Dict[str, Any]]):
                self.text = text
                self.tool_calls = tool_calls

        # Split prompt into distinct intents by line or semicolon
        lines = [line.strip() for line in prompt.replace(";", "\n").split("\n") if line.strip()]
        
        # If it's a single long sentence, also split on commas or periods
        intents = []
        for line in lines:
            if "," in line and not any(k in line.lower() for k in ["e.g.", "i.e."]):
                intents.extend([part.strip() for part in line.split(",") if part.strip()])
            else:
                intents.append(line)

        calls = []
        summaries = []

        for item in intents:
            item_lower = item.lower()

            # 1. Guardrail Check (Destructive Actions)
            if any(w in item_lower for w in ["delete", "cancel", "remove"]):
                evaluate_tool_safety("delete_event", {"title": item, "event_id": "ev_demo"}, user_confirmed=user_confirmed)

            # 2. Calendar Intent
            elif any(w in item_lower for w in ["schedule", "calendar", "tomorrow", "at 2 pm", "meeting", "lab"]):
                cleaned_title = item
                for stopword in ["schedule", "to my schedule", "add", "please"]:
                    cleaned_title = cleaned_title.replace(stopword, "").replace(stopword.capitalize(), "")
                cleaned_title = cleaned_title.strip(" :-")
                
                calls.append({
                    "name": "manage_calendar_event",
                    "input": {
                        "action_type": "create",
                        "title": cleaned_title or "Scheduled Task",
                        "start_time": "20261014T140000Z"
                    }
                })
                summaries.append(f"scheduled '{cleaned_title}'")

            # 3. Media / Study Video Intent
            elif any(w in item_lower for w in ["youtube", "lecture", "video", "watch", "listen"]):
                calls.append({
                    "name": "search_and_queue_media",
                    "input": {"query": item, "playlist_name": "Focus"}
                })
                summaries.append(f"queued '{item}' on YouTube")

            # 4. Habits, Reminders, and Notes -> Local Vault
            elif any(w in item_lower for w in ["remind", "remember", "habit", "study", "work on", "vault", "note", "code"]):
                cleaned_note = item
                for stopword in ["remind me to", "remind me", "remember to", "remember"]:
                    cleaned_note = cleaned_note.replace(stopword, "").replace(stopword.capitalize(), "")
                cleaned_note = cleaned_note.strip(" :-")

                calls.append({
                    "name": "save_to_orbit_vault",
                    "input": {
                        "category": "Daily Focus",
                        "summary": cleaned_note,
                        "content": item
                    }
                })
                save_to_orbit_vault("Daily Focus", cleaned_note, item)
                summaries.append(f"saved '{cleaned_note}' to your vault")

            # Fallback
            else:
                calls.append({
                    "name": "save_to_orbit_vault",
                    "input": {"category": "Inbox", "summary": item[:30], "content": item}
                })
                save_to_orbit_vault("Inbox", item[:30], item)
                summaries.append(f"saved note '{item[:30]}'")

        spoken_text = "Got it! I " + ", ".join(summaries) + "."
        return MockResponse(spoken_text, calls)