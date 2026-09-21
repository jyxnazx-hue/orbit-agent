import os
from dotenv import load_dotenv
from strands import Agent
from strands.models import BedrockModel

from orbit_tools import (
    parse_uploaded_document,
    execute_batch_operations,
    request_user_confirmation
)

load_dotenv()

SYSTEM_ORCHESTRATOR_PROMPT = """
You are Orbit, an autonomous life orchestrator built on AWS Bedrock.
Your job is to do >50% of the tedious cognitive and organizing work for the user.

Core Operating Principles:
1. Multi-Modal Context: Users will supply unstructured requests, voice transcripts, or file paths (PDFs, docs).
2. Document Parsing: If given a file path, immediately invoke `parse_uploaded_document` to inspect the full contents.
3. Batch Processing: You must never drop items. If a schedule has 10 classes, extract all 10. If a shopping list has 6 items, extract all 6. If a paper needs research, break down the citations and topics.
4. Categorization & Execution:
   - Identify the functional domain for each item ('scheduling', 'tasks', 'notes', 'shopping', 'media', 'research', 'vault').
   - Package all identified items and pass them to `execute_batch_operations`.
5. Human-In-The-Loop (HITL) Guardrail:
   - If any operation involves spending money (shopping checkouts) or destructive operations (deletions), DO NOT proceed silently. Call `request_user_confirmation`.
6. Ambiguity Resolution:
   - If critical information is missing to complete a task, ask the user concisely while keeping the rest of the valid tasks staged.
"""

def build_orbit_agent() -> Agent:
    model = BedrockModel(
        model_id="us.amazon.nova-lite-v1:0",
        region_name=os.getenv("AWS_DEFAULT_REGION", "us-east-1")
    )
    return Agent(
        model=model,
        system_prompt=SYSTEM_ORCHESTRATOR_PROMPT,
        tools=[
            parse_uploaded_document,
            execute_batch_operations,
            request_user_confirmation
        ]
    )

# Shared singleton instance maintaining conversation context across turns
orbit_instance = build_orbit_agent()
