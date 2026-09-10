from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from orbit_core import orbit_agent

app = FastAPI(title="Orbit Orchestrator API")

class UserInputRequest(BaseModel):
    raw_prompt: str

@app.post("/api/orbit/process")
async def process_orbit_input(req: UserInputRequest):
    try:
        # Run agentic loop with Strands SDK
        result = orbit_agent(req.raw_prompt)
        return {
            "status": "success",
            "agent_response": result.text,
            "tool_calls": [call for call in result.tool_calls]
        }
    except PermissionError as pe:
        # Caught by security hook (Tier 3 Guardrail)
        return {
            "status": "requires_confirmation",
            "warning": str(pe),
            "action_frozen": True
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="[IP_ADDRESS]", port=8000)
