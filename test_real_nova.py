from orbit_core import orbit_agent

prompt = (
    "Schedule my HAI design review tomorrow at 3 PM, "
    "remind me that my bike locker code is 3972, "
    "and queue the MIT Paxos lecture on YouTube"
)

print(f"Sending prompt to Nova Lite:\n'{prompt}'\n")
res = orbit_agent(prompt)

print("=== Nova Spoken Reply ===")
print(res.text)

print("\n=== Tasks Dispatched ===")
for call in res.tool_calls:
    print("•", call["input"])