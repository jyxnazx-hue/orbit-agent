import json
import webbrowser
import urllib.parse
from typing import Dict, Any

# Load user-configured application preferences
def load_user_config() -> Dict[str, Any]:
    try:
        with open("config/user_config.json", "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {
            "system_defaults": {"confirm_purchases": True, "confirm_destructive": True},
            "preferred_apps": {
                "scheduling": "google_calendar",
                "documentation": "notion",
                "shopping": "amazon",
                "media": "youtube"
            }
        }

def dispatch_to_preferred_app(category: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Takes an inferred category, looks up the user's preferred tool,
    and opens the pre-filled target application/browser directly.
    """
    config = load_user_config()
    target_tool = config.get("preferred_apps", {}).get(category, "vault")

    # 1. Scheduling Handler
    if category == "scheduling":
        title = payload.get("title", "New Event")
        encoded_title = urllib.parse.quote(title)
        url = f"https://calendar.google.com/calendar/r/eventedit?text={encoded_title}"
        webbrowser.open(url)
        return {"tool": target_tool, "category": category, "action": f"Opened calendar for '{title}'"}

    # 2. Shopping Handler
    elif category == "shopping":
        item = payload.get("item", "")
        encoded_item = urllib.parse.quote(item)
        url = f"https://www.amazon.com/s?k={encoded_item}"
        webbrowser.open(url)
        return {"tool": target_tool, "category": category, "action": f"Opened Amazon search for '{item}'"}

    # 3. Documentation / Notes Handler
    elif category == "documentation":
        page_title = payload.get("title", "Notes")
        encoded = urllib.parse.quote(page_title.lower().replace(" ", "-"))
        url = f"https://www.notion.so/{encoded}"
        webbrowser.open(url)
        return {"tool": target_tool, "category": category, "action": f"Dispatched to Notion: '{page_title}'"}

    # 4. Media Handler
    elif category == "media":
        query = payload.get("query", "")
        encoded_query = urllib.parse.quote(query)
        url = f"https://www.youtube.com/results?search_query={encoded_query}"
        webbrowser.open(url)
        return {"tool": target_tool, "category": category, "action": f"Loaded YouTube search for '{query}'"}

    # Fallback to internal storage
    return {"tool": "vault", "category": "vault", "action": "Recorded to Orbit Vault"}