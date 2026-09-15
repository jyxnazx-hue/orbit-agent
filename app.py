import os
import shutil
import sqlite3
from typing import Dict, Any, Optional
from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from orbit_agent import orbit_instance

load_dotenv()

app = FastAPI(title="Orbit Agent Engine")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = os.path.abspath("./uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

class CommandPayload(BaseModel):
    query: str
    confirmed: bool = False

@app.post("/api/command")
async def process_command(payload: CommandPayload):
    try:
        user_input = payload.query
        if payload.confirmed:
            user_input = f"User has explicitly confirmed: {payload.query}. Proceed with execution."

        # Strands agent conversational call
        agent_response = orbit_instance(user_input)
        response_text = str(agent_response)

        needs_confirmation = "HITL_PAUSE" in response_text or "Pending Operation" in response_text or "pending your confirmation" in response_text

        return {
            "status": "pending_confirmation" if needs_confirmation else "completed",
            "spoken_summary": response_text,
            "requires_confirmation": needs_confirmation
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/upload")
async def upload_document(file: UploadFile = File(...), note: Optional[str] = Form(None)):
    try:
        saved_path = os.path.join(UPLOAD_DIR, file.filename)
        with open(saved_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        prompt = f"I uploaded a document saved at '{saved_path}'."
        if note:
            prompt += f" Context/Instructions: {note}"
        else:
            prompt += " Please extract all tasks, schedules, readings, and action items and execute them."

        agent_response = orbit_instance(prompt)
        response_text = str(agent_response)

        needs_confirmation = "HITL_PAUSE" in response_text or "Pending Operation" in response_text

        return {
            "status": "pending_confirmation" if needs_confirmation else "completed",
            "file": file.filename,
            "spoken_summary": response_text,
            "requires_confirmation": needs_confirmation
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/vault")
def get_vault_entries():
    conn = sqlite3.connect("orbit_vault.db")
    cur = conn.cursor()
    cur.execute("SELECT id, category, title, raw_payload, target_app, status, created_at FROM vault ORDER BY id DESC")
    rows = cur.fetchall()
    conn.close()
    return [
        {
            "id": r[0],
            "category": r[1],
            "title": r[2],
            "payload": r[3],
            "target_app": r[4],
            "status": r[5],
            "created_at": r[6]
        }
        for r in rows
    ]
