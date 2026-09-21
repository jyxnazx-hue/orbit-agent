import os
import json
import boto3
from typing import Dict, Any, List, Optional
from strands import Agent, tool
from strands.models import BedrockModel
from dotenv import load_dotenv

from ingestors.universal_parser import parse_any_input
from orbit_tools import (
    execute_batch_operations,
    request_user_confirmation,
    record_to_vault,
    get_config
)

load_dotenv()

AWS_REGION = os.getenv("AWS_DEFAULT_REGION", "us-east-1")
NOVA_MODEL_ID = "us.amazon.nova-lite-v1:0"

# Bedrock low-level client for multimodal parsing (images + text)
bedrock_runtime = boto3.client("bedrock-runtime", region_name=AWS_REGION)

SUPERVISOR_SYSTEM_PROMPT = """
You are Orbit, an ambient life orchestrator built to take over >50% of the user's manual cognitive load.

Your core duties:
1. Multi-Modal Context: Users will pass you spoken transcripts, raw unstructured notes, or files (images of handwritten notes, whiteboards, flyers, or documents).
2. Comprehensive Extraction: Never summarize away discrete tasks. Extract EVERY calendar slot, EVERY shopping item, EVERY tutorial/lecture, and EVERY reference note.
3. Batch Routing: Group items into operations and invoke `execute_batch_operations` with categories:
   - 'scheduling': meetings, lectures, classes, deadlines
   - 'shopping': items to purchase or add to cart
   - 'tasks': action items, to-dos
   - 'notes': summaries, raw data, meeting minutes
   - 'media': video tutorials, lectures, music playlists
   - 'research': paper searches, citations, literature review
   - 'vault': credentials, codes, sensitive or unclassified items
4. Human-In-The-Loop (HITL):
   - Whenever an action incurs money (shopping checkouts) or deletes data, you MUST invoke `request_user_confirmation`.
5. Conversational Clarity: Keep your spoken/text responses concise, natural, and helpful.
"""

# Native Strands Tool: Ingest and analyze any uploaded file artifact
@tool
def ingest_file_artifact(file_path: str) -> str:
    """
    Ingests and parses any local file artifact (PDF, image/photo, text document, CSV)
    and extracts all text, structure, or data points for Orbit to organize.
    """
    parsed = parse_any_input(file_path)
    file_type = parsed.get("type")

    if file_type == "error":
        return f"File ingestion failed: {parsed.get('content')}"

    elif file_type == "document":
        return f"Extracted Document Content ({parsed.get('format')}):\n{parsed.get('content')}"

    elif file_type == "image":
        # Process image directly with Nova's visual understanding
        try:
            response = bedrock_runtime.converse(
                modelId=NOVA_MODEL_ID,
                messages=[{
                    "role": "user",
                    "content": [
                        {
                            "image": {
                                "format": parsed["format"],
                                "source": {"bytes": parsed["bytes"]}
                            }
                        },
                        {
                            "text": "Extract all readable text, schedules, lists, action items, or diagrams from this image in detail."
                        }
                    ]
                }]
            )
            extracted_text = response["output"]["message"]["content"][0]["text"]
            return f"Extracted Visual Content from Image:\n{extracted_text}"
        except Exception as e:
            return f"Error extracting visual content from image: {str(e)}"

    elif file_type == "audio":
        return f"Audio payload staged at {parsed.get('path')}. Ready for processing."

    return "File processed but returned no textual payload."

def create_supervisor_agent() -> Agent:
    model = BedrockModel(
        model_id=NOVA_MODEL_ID,
        region_name=AWS_REGION
    )
    return Agent(
        model=model,
        system_prompt=SUPERVISOR_SYSTEM_PROMPT,
        tools=[
            ingest_file_artifact,
            execute_batch_operations,
            request_user_confirmation
        ]
    )

# Shared orchestrator instance
orbit_supervisor = create_supervisor_agent()
