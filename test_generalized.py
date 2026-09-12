from orbit_agent import orbit_instance

mixed_bulk_input = """
Here is what I need done from my semester syllabus and weekend tasks:
1. Systems Lab: Mondays and Wednesdays at 10:00 AM to 11:30 AM starting next week.
2. Read and summarize the Paxos consensus paper, then locate related Raft comparison papers on Scholar.
3. Order 2 boxes of CR2032 batteries and an HDMI switch from Amazon.
4. Watch the 3-part distributed systems tutorial playlist on YouTube.
5. Note down: WiFi router recovery key is 8841-B92A.
"""

print("Submitting bulk context to Orbit Agent...\n")
response = orbit_instance(mixed_bulk_input)
print("=== Orbit Agent Reasoning & Dispatched Work ===")
print(response)