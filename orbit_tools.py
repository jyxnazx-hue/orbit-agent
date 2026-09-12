import os
import json
import sqlite3
import asyncio
from typing import List, Dict, Any
# pyrefly: ignore [missing-import]
from pypdf import PdfReader
from strands import tool

# Persistent Vault Setup
VAULT_DB = "orbit_vault.db"

def init_vault():
    conn = sqlite3.connect(VAULT_DB)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS vault (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT,
            title TEXT,
            raw_payload TEXT,
            target_app TEXT,
            status TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

init_vault()

def get_config() -> Dict[str, Any]:
    cfg_path = os.path.join(os.path.dirname(__file__), "config", "user_config.json")
    if os.path.exists(cfg_path):
        with open(cfg_path, "r") as f:
            return json.load(f)
    return {
        "user_preferences": {},
        "authorized_apps": [],
        "security_policies": {"require_confirmation_for_purchases": True}
    }

def record_to_vault(category: str, title: str, payload: Any, target_app: str, status: str):
    conn = sqlite3.connect(VAULT_DB)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO vault (category, title, raw_payload, target_app, status) VALUES (?, ?, ?, ?, ?)",
        (category, title, json.dumps(payload), target_app, status)
    )
    conn.commit()
    conn.close()

# -------------------------------------------------------------
# Tool 1: Ingest and Extract Raw Documents (PDF / Text)
# -------------------------------------------------------------
@tool
def parse_uploaded_document(file_path: str) -> str:
    """Extracts raw text content from uploaded files (PDFs, text files, markdown) for analysis."""
    if not os.path.exists(file_path):
        return f"Error: File '{file_path}' does not exist."
    
    if file_path.lower().endswith(".pdf"):
        reader = PdfReader(file_path)
        extracted = []
        for idx, page in enumerate(reader.pages):
            text = page.extract_text()
            if text:
                extracted.append(f"--- Page {idx+1} ---\n{text}")
        return "\n".join(extracted)
    else:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()

# -------------------------------------------------------------
# Tool 2: Batch App Dispatcher with Permission Checks
# -------------------------------------------------------------
@tool
def execute_batch_operations(operations: List[Dict[str, Any]]) -> str:
    """
    Executes a list of categorized tasks.
    Each operation should be: {"category": str, "title": str, "details": dict}
    Categories include: 'scheduling', 'tasks', 'notes', 'shopping', 'media', 'research', 'vault'
    """
    config = get_config()
    prefs = config.get("user_preferences", {})
    authorized = config.get("authorized_apps", [])
    results = []

    for op in operations:
        cat = op.get("category", "vault").lower()
        title = op.get("title", "Untitled Task")
        details = op.get("details", {})
        target_app = prefs.get(cat, "vault")

        # Check authorization
        if target_app not in authorized and cat != "vault":
            record_to_vault(cat, title, details, target_app, status="unauthorized_parked")
            results.append(f"• Parked '{title}' in local vault (App '{target_app}' is not authorized).")
            continue

        # Dynamic routing
        record_to_vault(cat, title, details, target_app, status="staged_for_execution")
        results.append(f"• Staged for {target_app} [{cat.upper()}]: '{title}'")

    return "\n".join(results)

# -------------------------------------------------------------
# Tool 3: Human-in-the-Loop Confirmation Gate
# -------------------------------------------------------------
@tool
def request_user_confirmation(action_summary: str, risk_level: str) -> str:
    """
    Invoked whenever an operation requires human authorization (e.g. monetary purchases, destructive actions, or ambiguity).
    """
    return f"HITL_PAUSE: Action '{action_summary}' with risk '{risk_level}' intercepted. Awaiting user consent."