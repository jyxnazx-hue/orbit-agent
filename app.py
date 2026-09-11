import os
import sqlite3
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

from orbit_core import orbit_agent
from hooks.security_guard import SafetyGuardrailError

load_dotenv()

app = FastAPI(title="Orbit Agent Engine")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class CommandPayload(BaseModel):
    query: str
    confirmed: bool = False
    pending_tool: Optional[str] = None
    pending_args: Optional[Dict[str, Any]] = None

@app.post("/api/command")
def process_command(payload: CommandPayload):
    """
    Ingests voice query, runs safety checks, routes to tools,
    or halts execution to request user confirmation.
    """
    try:
        if os.getenv("USE_MOCK_BEDROCK", "false").lower() == "true":
            response = orbit_agent(payload.query, user_confirmed=payload.confirmed)
        else:
            response = orbit_agent(payload.query)

        action_cards = []
        raw_calls = getattr(response, "tool_calls", [])
        for call in raw_calls:
            name = call.get("name") if isinstance(call, dict) else getattr(call, "name", "")
            inp = call.get("input") if isinstance(call, dict) else getattr(call, "input", {})
            action_cards.append({"tool": name, "input": inp})

        return {
            "status": "completed",
            "spoken_summary": getattr(response, "text", str(response)),
            "actions_executed": action_cards,
            "requires_confirmation": False
        }

    except SafetyGuardrailError as sge:
        # HITL Intercept: Returns question for the user to hear and confirm
        return {
            "status": "interrupted",
            "spoken_summary": sge.args[0],
            "actions_executed": [],
            "requires_confirmation": True,
            "pending_tool": sge.tool_name,
            "pending_args": sge.payload,
            "reason": sge.reason
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/vault")
def get_vault_entries():
    conn = sqlite3.connect("orbit_vault.db")
    cur = conn.cursor()
    cur.execute("SELECT id, category, summary, content, created_at FROM vault ORDER BY id DESC")
    rows = cur.fetchall()
    conn.close()
    return [{"id": r[0], "category": r[1], "summary": r[2], "content": r[3], "created_at": r[4]} for r in rows]