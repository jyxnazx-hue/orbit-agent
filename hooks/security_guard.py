from typing import Dict, Any

# Tool Risk Classification
DESTRUCTIVE_TOOLS = {"delete_event", "cancel_meeting", "purge_vault"}
COMMUNICATION_TOOLS = {"send_email", "post_message"}

class SafetyGuardrailError(Exception):
    def __init__(self, message: str, tool_name: str, payload: Dict[str, Any], reason: str):
        super().__init__(message)
        self.tool_name = tool_name
        self.payload = payload
        self.reason = reason

def evaluate_tool_safety(tool_name: str, tool_args: Dict[str, Any], user_confirmed: bool = False) -> None:
    """
    Deterministic interception checkpoint:
    1. Blocks destructive operations unless human-confirmed.
    2. Flags missing critical arguments that require voice disambiguation.
    """
    if tool_name in DESTRUCTIVE_TOOLS and not user_confirmed:
        raise SafetyGuardrailError(
            message=f"I need your explicit confirmation before executing '{tool_name}'. Should I proceed?",
            tool_name=tool_name,
            payload=tool_args,
            reason="DESTRUCTIVE_OPERATION"
        )

    if tool_name in COMMUNICATION_TOOLS and not user_confirmed:
        raise SafetyGuardrailError(
            message=f"I have prepared '{tool_name}' for {tool_args.get('recipient', 'the contact')}. Confirm to send?",
            tool_name=tool_name,
            payload=tool_args,
            reason="EXTERNAL_COMMUNICATION"
        )

    # Ambiguity check for scheduling without times
    if tool_name == "manage_calendar_event":
        start_time = tool_args.get("start_time", "").strip()
        if not start_time or start_time.lower() == "unspecified":
            raise SafetyGuardrailError(
                message=f"What time would you like to schedule '{tool_args.get('title', 'this event')}'?",
                tool_name=tool_name,
                payload=tool_args,
                reason="AMBIGUOUS_TIME"
            )