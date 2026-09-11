"""Session task messages, independent of the transient viewport HUD."""
import time
import re


TASKS = []


def record_update(title, status, progress, details=None, summary="", next_steps=None):
    now = time.time()
    previous = TASKS[-1] if TASKS else None
    if (previous is None or previous["title"] != title
            or (previous["progress"] >= 100 and progress < 100)
            or progress < previous["progress"]):
        previous = {"title": title, "started": now, "progress": progress,
                    "messages": [], "last_snapshot": None, "details": [],
                    "state": "Running", "finished": None}
        TASKS.append(previous)
    detail_lines = details if isinstance(details, list) else [details] if details else []
    steps = next_steps if isinstance(next_steps, list) else [next_steps] if next_steps else []
    snapshot = (status, progress, tuple(map(str, detail_lines)), summary, tuple(map(str, steps)))
    if snapshot == previous["last_snapshot"]:
        return
    messages = previous["messages"]
    if status and (not messages or previous["last_snapshot"][0] != status):
        messages.append((now, str(status)))
    old_details = previous["details"]
    lines = list(map(str, detail_lines))
    added = lines[len(old_details):] if lines[:len(old_details)] == old_details else lines
    messages.extend((now, line) for line in added if line)
    if isinstance(details, list):
        previous["details"] = lines
    if summary and (previous["last_snapshot"] is None or previous["last_snapshot"][3] != summary):
        messages.append((now, str(summary)))
    if steps and (previous["last_snapshot"] is None or previous["last_snapshot"][4] != snapshot[4]):
        messages.extend((now, "Next: " + str(step)) for step in steps)
    previous["last_snapshot"] = snapshot
    previous["progress"] = progress
    failed = re.search(r"\b(failed|failure|error|rolled back)\b", str(status), re.I)
    cancelled = re.search(r"\bcancelled\b", str(status), re.I)
    previous["state"] = "Failure" if failed else "Cancelled" if cancelled else "Success" if progress >= 100 else "Running"
    if previous["state"] != "Running" and previous["finished"] is None:
        previous["finished"] = now
