from dotenv import load_dotenv
load_dotenv()

from orbit_core import orbit_agent

test_prompt = (
    "Reschedule the Distributed Systems lab to next Tuesday 2pm. "
    "Save the MIT Paxos lecture to my study playlist, "
    "and remember that my bike locker code is 4912."
)

print(f"Sending prompt to Orbit:\n\"{test_prompt}\"\n")
response = orbit_agent(test_prompt)

print("=== Orbit Agent Response ===")
print(getattr(response, "text", str(response)))
print("\n=== Tool Calls Executed ===")
tool_calls = getattr(response, "tool_calls", [])
for call in tool_calls:
    if isinstance(call, dict):
        print(f"• Tool: {call.get('name')} | Input: {call.get('input')}")
    else:
        print(f"• Tool: {getattr(call, 'name', '')} | Input: {getattr(call, 'input', {})}")