import os
from dotenv import load_dotenv
from strands import Agent
from strands.models import BedrockModel

load_dotenv()

# Verify Strands Agent with Amazon Nova Lite
model = BedrockModel(
    model_id="us.amazon.nova-lite-v1:0",
    region_name=os.getenv("AWS_DEFAULT_REGION", "us-east-1")
)

agent = Agent(
    model=model,
    system_prompt="You are Orbit, an autonomous life orchestrator. Acknowledge readiness."
)

response = agent("Orbit status check.")
print(response)