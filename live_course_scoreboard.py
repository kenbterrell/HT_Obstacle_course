#!/usr/bin/env python3
"""
Live course scoreboard.
Reads the shared course_state.json produced by the check-in script
and displays all participants with live (or final) elapsed times.
Updates every 10 seconds.
"""

import json
import os
import time
import platform
from datetime import datetime
from pathlib import Path

STATE_FILE = Path("course_state.json")
REFRESH_SECONDS = 3


def clear_screen():
    os.system("cls" if platform.system() == "Windows" else "clear")


def format_elapsed(seconds: float) -> str:
    """Return elapsed time as 'MM:SS'."""
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{minutes:02d}:{secs:02d}"


def format_time(dt: datetime) -> str:
    """Return time as e.g. '7:05 pm'."""
    return dt.strftime("%I:%M %p").lstrip("0").lower()


def load_state() -> dict:
    """Load the current state from the JSON file."""
    if not STATE_FILE.exists():
        return {"active": {}, "finished": {}}
    try:
        with open(STATE_FILE, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"active": {}, "finished": {}}


def display(state: dict):
    clear_screen()
    now = datetime.now()

    print("=" * 58)
    print(f"    SABINE VALLEY A.R.A. HT OBSTACLE COURSE SCOREBOARD")
    print("=" * 58)
    print()

    active = state.get("active", {})
    finished = state.get("finished", {})

    if not active and not finished:
        print("  No activity recorded yet.")
        print()
        print(f"(updating every {REFRESH_SECONDS} seconds – Ctrl-C to quit)")
        return

    finished_list = []
    active_list = []

    # Finished participants
    for call, info in finished.items():
        try:
            joined = datetime.fromisoformat(info["joined"])
            if "elapsed_seconds" in info:
                elapsed = info["elapsed_seconds"]
            else:
                left = datetime.fromisoformat(info["left"])
                elapsed = (left - joined).total_seconds()
            finished_list.append({
                "call": call,
                "joined": joined,
                "elapsed": elapsed,
                "status": "FINISHED"
            })
        except Exception:
            continue

    # Active participants
    for call, info in active.items():
        try:
            joined = datetime.fromisoformat(info["joined"])
            elapsed = (now - joined).total_seconds()
            active_list.append({
                "call": call,
                "joined": joined,
                "elapsed": elapsed,
                "status": "ON COURSE"
            })
        except Exception:
            continue

    # Sort both lists by elapsed time (least → most)
    finished_list.sort(key=lambda x: x["elapsed"])
    active_list.sort(key=lambda x: x["elapsed"])

    # Finished people go at the top
    all_participants = finished_list + active_list

    print(f"{'Callsign':<10} {'Joined':<12} {'Elapsed':<10} Status")
    print("-" * 58)

    for p in all_participants:
        joined_str = format_time(p["joined"])
        elapsed_str = format_elapsed(p["elapsed"])
        print(f"{p['call']:<10} {joined_str:<12} {elapsed_str:<10} {p['status']}")

    print()
    print(f"(updating every {REFRESH_SECONDS} seconds – Ctrl-C to quit)")


def main():
    print("Starting live scoreboard...")
    print(f"Watching {STATE_FILE.resolve()}")
    print()

    try:
        while True:
            state = load_state()
            display(state)
            time.sleep(REFRESH_SECONDS)
    except KeyboardInterrupt:
        print("\nScoreboard stopped.")


if __name__ == "__main__":
    main()