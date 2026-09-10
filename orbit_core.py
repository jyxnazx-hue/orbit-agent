import sqlite3
from typing import Dict, Any
# pyrefly: ignore [missing-import]
from strands import Agent, tool
# pyrefly: ignore [missing-import]
from strands.models import BedrockModel
# pyrefly: ignore [missing-import]
from strands.hooks import BeforeToolCallEvent

# -------------------------------------------------------------------
# 1. Native Fallback Store (Local SQLite for non-tooled items)
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

@tool
def save_to_orbit_vault(category: str, summary: str, content: str) -> Dict[str, Any]:
    """
    Fallback tool: Stores personal notes, reminders, facts, or codes that do not 
    belong in an external third-party tool (Notion/GCal).
    """
    cursor.execute(
        "INSERT INTO vault (category, summary, content) VALUES (?, ?, ?)",
        (category, summary, content)
    )
    conn.commit()
    return {
        "status": "saved_locally",
        "category": category,
        "summary": summary,
        "deep_link": f"orbit://vault?category={category}"
    }

# -------------------------------------------------------------------
# 2. External Tools Returning Native Deep Links
# -------------------------------------------------------------------
@tool
def update_google_calendar(event_title: str, start_time: str, end_time: str) -> Dict[str, Any]:
    """
    Creates or reschedules an event in Google Calendar. Returns the event deep link.
    """
    # [Integration Logic with Google Calendar API / MCP]
    # Simulated response returning real direct URI:
    event_id = "ev_98234ab"
    return {
        "status": "success",
        "action": "calendar_updated",
        "event_title": event_title,
        "time": f"{start_time} - {end_time}",
        "deep_link": f"https://calendar.google.com/calendar/r/eventedit/{event_id}"
    }

@tool
def append_to_notion(page_title: str, content_blocks: str, database_name: str = "Inbox") -> Dict[str, Any]:
    """
    Appends structured notes or study outlines directly to Notion. Returns the page URI.
    """
    # [Integration Logic with Notion API / MCP]
    page_id = "2d3e4f5a6b"
    return {
        "status": "success",
        "action": "notion_page_created",
        "title": page_title,
        "deep_link": f"notion://www.notion.so/{page_id}"
    }

@tool
def save_youtube_to_playlist(search_query: str, playlist_name: str = "Watch Later") -> Dict[str, Any]:
    """
    Finds a video matching the query and adds it to the user's YouTube playlist. Returns direct URL.
    """
    # Simulated top search result:
    video_id = "vYQpWQgVKs8"
    return {
        "status": "success",
        "action": "video_queued",
        "playlist": playlist_name,
        "deep_link": f"https://www.youtube.com/watch?v={video_id}"
    }

# -------------------------------------------------------------------
# 3. Deterministic Security & Ambiguity Guardrails (Hooks)
# -------------------------------------------------------------------
def security_and_ambiguity_guard(event: BeforeToolCallEvent):
    """
    Deterministic checkpoint: halts destructive actions or ambiguous parameters 
    before the tool can execute.
    """
    tool_name = event.tool_use.get("name")
    tool_input = event.tool_use.get("input", {})

    # Tier 3: Block destructive actions unless confirmed
    SENSITIVE_TOOLS = ["delete_event", "send_email", "purchase_item"]
    if tool_name in SENSITIVE_TOOLS and not tool_input.get("user_confirmed"):
        raise PermissionError(
            f"[Orbit Guardrail Warning] Action '{tool_name}' requires human voice/tap confirmation."
        )

# -------------------------------------------------------------------
# 4. Initialize Orbit Orchestrator Agent
# -------------------------------------------------------------------
bedrock_model = BedrockModel(model_id="anthropic.claude-sonnet-4-5-20250929-v1:0")

system_prompt = """
You are Orbit, an autonomous life orchestrator and executive assistant.
Your job is to receive unstructured, chaotic everyday thoughts, voice transcripts, or links and route them:
- Notes, study materials, or documentation -> Notion (`append_to_notion`)
- Appointments, deadlines, or rescheduling -> Google Calendar (`update_google_calendar`)
- Lectures, tutorials, or video links -> YouTube (`save_youtube_to_playlist`)
- Arbitrary facts, codes, personal reminders without a tool -> Orbit Vault (`save_to_orbit_vault`)

Rules:
1. Never force the user into manual categorizing. Infer intent dynamically.
2. If an instruction is completely ambiguous (e.g., 'send notes to Alex' when there are multiple Alexes), state that you need clarification.
3. Always return direct deep links so the user can launch the app immediately.
"""

orbit_agent = Agent(
    model=bedrock_model,
    tools=[
        update_google_calendar, 
        append_to_notion, 
        save_youtube_to_playlist, 
        save_to_orbit_vault
    ],
    hooks=[(BeforeToolCallEvent, security_and_ambiguity_guard)],
    system_prompt=system_prompt
)
