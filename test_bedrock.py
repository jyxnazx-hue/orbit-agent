import os
import boto3
from dotenv import load_dotenv

load_dotenv()

region = os.getenv("AWS_DEFAULT_REGION", "us-east-1")
client = boto3.client("bedrock-runtime", region_name=region)

print(f"Testing Bedrock connection in {region}...")

try:
    response = client.converse(
        modelId="us.anthropic.claude-sonnet-4-5-20250929-v1:0",
        messages=[{"role": "user", "content": [{"text": "Reply with 'Orbit Online' if connected."}]}]
    )
    output = response["output"]["message"]["content"][0]["text"]
    print(f"Success! Model responded: {output}")
except Exception as e:
    print(f"Connection test failed: {e}")
