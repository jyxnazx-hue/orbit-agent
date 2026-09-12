import os
from agents.supervisor import orbit_supervisor

# Test 1: Unstructured bulk text with conversational memory
print("--- Test 1: Conversational Bulk Request ---")
response_1 = orbit_supervisor(
    "Hi Orbit! For this semester, add Advanced ML Lab on Tuesdays at 2 PM, "
    "put 3 black fine-tip pens on my shopping list, and note down that my student ID is A0982."
)
print(response_1)

# Test 2: Follow-up question maintaining conversational context
print("\n--- Test 2: Follow-up Query ---")
response_2 = orbit_supervisor("What was that student ID I just asked you to note?")
print(response_2)

print("\n--- Test 3: Multimodal PDF Ingestion ---")
script_dir = os.path.dirname(os.path.abspath(__file__))
image_path = os.path.join(script_dir, "test_img.png")
response_3 = orbit_supervisor(f"Analyze this PDF document: {image_path}")
print(response_3)