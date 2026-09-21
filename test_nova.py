import os
import boto3
from dotenv import load_dotenv

load_dotenv()

region = os.getenv("AWS_DEFAULT_REGION", "us-east-1")
client = boto3.client("bedrock-runtime", region_name=region)

print(f"Testing Amazon Nova Lite in {region}...")

# Amazon Nova Lite model ID for us-east-1
MODEL_ID = "us.amazon.nova-lite-v1:0"

try:
    response = client.converse(
        modelId=MODEL_ID,
        messages=[{"role": "user", "content": [{"text": "Reply with 'Nova Lite Online' if ready."}]}]
    )
    output = response["output"]["message"]["content"][0]["text"]
    print(f"Success! Model output: {output}")
except Exception as e:
    print(f"Status/Error: {e}")
