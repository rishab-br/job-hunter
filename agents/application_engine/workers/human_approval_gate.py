from langgraph.types import interrupt

from state import GlobalState


def run(state: GlobalState) -> GlobalState:
    """
    Pauses the graph for each pending application and waits for explicit human
    confirmation. Uses LangGraph's interrupt() primitive — the graph must be
    compiled with a checkpointer (e.g. MemorySaver) for this to work.

    To resume after an interrupt, call:
        graph.invoke(Command(resume={"approved": True}), config=thread_config)
    or:
        graph.invoke(Command(resume={"approved": False}), config=thread_config)
    """
    pending = list(state.get("pending_approvals") or [])
    confirmed: list[dict] = []
    skipped: list[dict] = []

    for item in pending:
        # Interrupt and surface the application details to the human reviewer
        response = interrupt({
            "type": "application_approval",
            "message": (
                f"Review application for {item['job_title']} at {item['company']} "
                f"({item['platform']})\n"
                f"Job URL: {item['job_url']}\n"
                f"Resume: {item['resume_path']}\n"
                f"Cover letter: {item['cover_letter_path']}\n"
                f"Form screenshot: {item.get('form_screenshot_path', 'N/A')}"
            ),
            "job": item,
            "instructions": "Respond with {\"approved\": true} to submit, or {\"approved\": false} to skip.",
        })

        if isinstance(response, dict) and response.get("approved"):
            confirmed.append({**item, "approved": True})
        else:
            skipped.append({**item, "approved": False})

    logs = list(state.get("logs") or [])
    logs.append(
        f"[human_approval_gate] {len(confirmed)} approved, {len(skipped)} skipped."
    )

    return {
        **state,
        "pending_approvals": confirmed,
        "logs": logs,
    }
