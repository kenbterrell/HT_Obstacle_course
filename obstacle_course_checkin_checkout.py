#!/usr/bin/env python3
"""
Course check-in / check-out script.
"""

import json
import os
import re
import shutil
import subprocess
import threading
import time
from datetime import datetime
from pathlib import Path

STATE_FILE = Path("course_state.json")
MY_CALL = "AC0TG"
ID_INTERVAL = 600
AUDIO_DEVICE = "plughw:3,0"
DTMF_SAMPLE_RATE = 22050
DTMF_GAP_SECONDS = 2.5

PHONETICS = {
    "A": "Alfa", "B": "Bravo", "C": "Charlie", "D": "Delta",
    "E": "Echo", "F": "Foxtrot", "G": "Golf", "H": "Hotel",
    "I": "India", "J": "Juliett", "K": "Kilo", "L": "Lima",
    "M": "Mike", "N": "November", "O": "Oscar", "P": "Papa",
    "Q": "Quebec", "R": "Romeo", "S": "Sierra", "T": "Tango",
    "U": "Uniform", "V": "Victor", "W": "Whiskey", "X": "X-ray",
    "Y": "Yankee", "Z": "Zulu",
    "0": "Zero", "1": "One", "2": "Two", "3": "Three",
    "4": "Four", "5": "Five", "6": "Six", "7": "Seven",
    "8": "Eight", "9": "Niner",
}


def to_phonetic(call):
    return " ".join(PHONETICS.get(ch, ch) for ch in call.upper())


def to_base36(n):
    if n == 0:
        return "0"
    digits = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    result = []
    while n:
        result.append(digits[n % 36])
        n //= 36
    return "".join(reversed(result))


def format_code(digits):
    digits = re.sub(r"\D", "", str(digits))
    digits = digits.zfill(10)[-10:]
    return "%s-%s-%s" % (digits[0:3], digits[3:6], digits[6:10])


def normalize_code(text):
    return re.sub(r"\D", "", text or "")


def callsign_to_code(call):
    number = int(call.upper(), 36)
    return format_code("%010d" % number)


def is_valid_us_callsign(call):
    pattern = re.compile(
        r"^([AKNW][0-9][A-Z]{1,3}|[AKNW][A-Z][0-9][A-Z]{1,3})$"
    )
    return bool(pattern.match(call))


def decode_callsign(digits):
    digits = normalize_code(digits)
    if len(digits) != 10:
        return None
    try:
        call = to_base36(int(digits))
        if is_valid_us_callsign(call):
            return call
    except ValueError:
        pass
    return None


def format_time(dt=None):
    if dt is None:
        dt = datetime.now()
    return dt.strftime("%I:%M %p").lstrip("0").lower()


speak_lock = threading.Lock()


def speak(text):
    if not text.strip():
        return
    for tool in ("espeak-ng", "sox", "aplay"):
        if not shutil.which(tool):
            print("(TTS unavailable – missing %s)" % tool)
            return
    voice_args = "-v en-us-nyc -s 125 -a 150 -p 40"
    cmd = (
        "( "
        "sox -n -t raw -r 22050 -e signed -b 16 -c 1 - synth 0.1 sine 2525 vol 0.7; "
        "sox -n -t raw -r 22050 -e signed -b 16 -c 1 - trim 0 0.25; "
        "sox -n -t raw -r 22050 -e signed -b 16 -c 1 - synth 0.25 sine 2525 vol 0.7; "
        "sox -n -t raw -r 22050 -e signed -b 16 -c 1 - trim 0 0.3; "
        "espeak-ng --stdout %s \"%s\"; "
        "sox -n -t raw -r 22050 -e signed -b 16 -c 1 - trim 0 0.2; "
        "sox -n -t raw -r 22050 -e signed -b 16 -c 1 - synth 0.25 sine 2475 vol 0.7 "
        ") | aplay -D %s -t raw -r 22050 -f S16_LE -c 1 -q"
    ) % (voice_args, text, AUDIO_DEVICE)
    with speak_lock:
        subprocess.run(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def speak_invalid():
    speak("Invalid code.")


def identification_loop():
    phonetic_id = to_phonetic(MY_CALL)
    while True:
        print("[ID] %s" % MY_CALL)
        speak(phonetic_id)
        time.sleep(ID_INTERVAL)


def empty_state():
    return {"active": {}, "finished": {}}


def load_state():
    if not STATE_FILE.exists():
        return empty_state()
    try:
        with open(str(STATE_FILE), "r", encoding="utf-8") as handle:
            data = json.load(handle)
        if "active" not in data:
            data["active"] = {}
        if "finished" not in data:
            data["finished"] = {}
        return data
    except Exception:
        return empty_state()


def save_state(state_data):
    tmp_path = str(STATE_FILE) + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as handle:
        json.dump(state_data, handle, indent=2)
    os.replace(tmp_path, str(STATE_FILE))


def ensure_state_file():
    if not STATE_FILE.exists():
        save_state(empty_state())


state_lock = threading.Lock()
state = empty_state()
mono_times = {}


def parse_call_command(line, command):
    parts = line.split()
    if len(parts) != 2 or parts[0] != command:
        return None
    call = parts[1].upper()
    if not is_valid_us_callsign(call):
        return None
    return call


def start_player(call, announce=True):
    global state
    if call in state["active"]:
        print("%s is already on the course." % call)
        if announce:
            speak("%s is already on the course." % to_phonetic(call))
        return
    if call in state.get("finished", {}):
        del state["finished"][call]
    now = datetime.now()
    state["active"][call] = {"joined": now.isoformat(timespec="seconds")}
    mono_times[call] = time.monotonic()
    save_state(state)
    print("%s has entered the course at %s  [%s]" % (call, format_time(now), callsign_to_code(call)))
    if announce:
        speak("%s has entered the course at %s" % (to_phonetic(call), format_time(now)))


def finish_player(call, announce=True):
    global state
    if call not in state["active"]:
        print("%s was not on the course." % call)
        if announce:
            speak("%s was not on the course." % to_phonetic(call))
        return
    joined_iso = state["active"][call]["joined"]
    left_dt = datetime.now()
    elapsed = time.monotonic() - mono_times.pop(call, time.monotonic())
    minutes = int(elapsed // 60)
    seconds = int(elapsed % 60)
    del state["active"][call]
    state["finished"][call] = {
        "joined": joined_iso,
        "left": left_dt.isoformat(timespec="seconds"),
        "elapsed_seconds": int(elapsed),
    }
    save_state(state)
    print("%s has left the course at %s with an elapsed time of %02d minutes and %02d seconds." % (
        call, format_time(left_dt), minutes, seconds
    ))
    if announce:
        speak("%s has left the course at %s with an elapsed time of %d minutes and %d seconds." % (
            to_phonetic(call), format_time(left_dt), minutes, seconds
        ))


def boot_player(call):
    global state
    removed = False
    if call in state.get("active", {}):
        del state["active"][call]
        mono_times.pop(call, None)
        removed = True
    if call in state.get("finished", {}):
        del state["finished"][call]
        removed = True
    save_state(state)
    if removed:
        print("%s has been removed from the course." % call)
        speak("%s has been removed from the course." % to_phonetic(call))
    else:
        print("%s was not on the scoreboard." % call)


def process_line(line):
    raw = line.strip().upper()
    if not raw:
        return
    with state_lock:
        if raw == "EXIT":
            print("Shutting down.")
            raise SystemExit(0)
        if raw == "CLEAR":
            confirm = input("Are you sure you want to clear the scoreboard? [Y/n]: ").strip().upper()
            if confirm in ("", "Y", "YES"):
                state = empty_state()
                mono_times.clear()
                save_state(state)
                print("Scoreboard cleared.")
            else:
                print("Clear cancelled.")
            return
        if raw == "SHOW":
            active = state.get("active", {})
            if not active:
                print("No one is currently on the course.")
            else:
                print("Currently on the course:")
                for call in sorted(active):
                    joined = datetime.fromisoformat(active[call]["joined"])
                    print("  %s  [%s]  -  joined at %s" % (
                        call, callsign_to_code(call), format_time(joined)
                    ))
            return
        convert_call = parse_call_command(raw, "CONVERT")
        if convert_call:
            print("%s  ->  %s" % (convert_call, callsign_to_code(convert_call)))
            return
        if raw.startswith("CONVERT"):
            print("Usage: convert CALLSIGN")
            return
        boot_call = parse_call_command(raw, "BOOT")
        if boot_call:
            boot_player(boot_call)
            return
        if raw.startswith("BOOT"):
            print("Usage: boot CALLSIGN")
            return
        start_call = parse_call_command(raw, "START")
        if start_call:
            start_player(start_call)
            return
        if raw.startswith("START"):
            print("Usage: start CALLSIGN")
            return
        finish_call = parse_call_command(raw, "FINISH")
        if finish_call:
            finish_player(finish_call)
            return
        if raw.startswith("FINISH"):
            print("Usage: finish CALLSIGN")
            return
        digits_only = normalize_code(raw)
        if raw.endswith("73") or (len(digits_only) == 12 and digits_only.endswith("73")):
            if len(digits_only) == 12 and digits_only.endswith("73"):
                call = decode_callsign(digits_only[:-2])
                if call is None:
                    print("Invalid code.")
                    speak_invalid()
                    return
                finish_player(call)
                return
            print("Invalid code.")
            speak_invalid()
            return
        if len(digits_only) == 10:
            call = decode_callsign(digits_only)
            if call is None:
                print("Invalid code.")
                speak_invalid()
                return
            start_player(call)
            return
        print("Invalid code.")
        speak_invalid()


# ------------------------------------------------------------------
# DTMF
# ------------------------------------------------------------------
dtmf_lock = threading.Lock()
dtmf_buffer = []
dtmf_last = [0.0]


def dtmf_watchdog():
    while True:
        time.sleep(0.25)
        sequence = None
        with dtmf_lock:
            if dtmf_buffer and (time.monotonic() - dtmf_last[0]) >= DTMF_GAP_SECONDS:
                sequence = "".join(dtmf_buffer)
                del dtmf_buffer[:]
        if sequence:
            if len(sequence) == 10:
                print("[DTMF] complete sequence: %s" % format_code(sequence))
            else:
                print("[DTMF] complete sequence: %s" % sequence)
            process_line(sequence)


def dtmf_listener():
    if not shutil.which("arecord") or not shutil.which("multimon-ng"):
        print("(DTMF listener disabled – install alsa-utils and multimon-ng)")
        return

    # stdbuf -oL keeps multimon-ng from holding digits in its output buffer
    decoder = "multimon-ng"
    if shutil.which("stdbuf"):
        decoder = "stdbuf -oL multimon-ng"

    cmd = (
        "arecord -D %s -t raw -r %d -f S16_LE -c 1 -q | %s -t raw -a DTMF -"
        % (AUDIO_DEVICE, DTMF_SAMPLE_RATE, decoder)
    )
    print("DTMF listener starting on %s" % AUDIO_DEVICE)
    print("DTMF command: %s" % cmd)

    try:
        proc = subprocess.Popen(
            cmd,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1
        )
    except Exception as e:
        print("(DTMF listener failed to start: %s)" % e)
        return

    def print_stderr():
        if proc.stderr is None:
            return
        for err in proc.stderr:
            err = err.strip()
            if err:
                print("[DTMF err] %s" % err)

    threading.Thread(target=print_stderr, daemon=True).start()

    if proc.stdout is None:
        print("(DTMF listener has no stdout)")
        return

    for line in proc.stdout:
        line = line.strip()
        if not line:
            continue
        if not line.startswith("DTMF:"):
            continue
        digit = line.split(":", 1)[1].strip()
        if digit not in "0123456789":
            continue
        with dtmf_lock:
            dtmf_buffer.append(digit)
            dtmf_last[0] = time.monotonic()
            current = "".join(dtmf_buffer)
        print("[DTMF] %s   buffer=%s" % (digit, current))

    print("(DTMF listener stopped)")


def main():
    global state
    ensure_state_file()
    state = load_state()
    for call, info in state.get("active", {}).items():
        try:
            joined = datetime.fromisoformat(info["joined"])
            mono_times[call] = time.monotonic() - (datetime.now() - joined).total_seconds()
        except Exception:
            mono_times[call] = time.monotonic()

    threading.Thread(target=identification_loop, daemon=True).start()
    threading.Thread(target=dtmf_listener, daemon=True).start()
    threading.Thread(target=dtmf_watchdog, daemon=True).start()

    print("Course tracker ready.")
    print("Commands: 10-digit code, code+73, convert CALL, start CALL, finish CALL, boot CALL, show, clear, exit")
    print("Example code format: %s -> %s" % (MY_CALL, callsign_to_code(MY_CALL)))
    print()

    while True:
        try:
            line = input("> ").strip().upper()
            process_line(line)
        except (KeyboardInterrupt, SystemExit):
            print("\nShutting down.")
            break
        except Exception as e:
            print("Error: %s" % e)
            speak_invalid()


if __name__ == "__main__":
    main()