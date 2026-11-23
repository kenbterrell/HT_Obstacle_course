#!/usr/bin/env python3

import re

def to_base36(n: int) -> str:
    """Convert a non-negative integer to uppercase base-36 string."""
    if n == 0:
        return '0'
    digits = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ'
    result = []
    while n:
        result.append(digits[n % 36])
        n //= 36
    return ''.join(reversed(result))


def is_valid_us_callsign(call: str) -> bool:
    """Basic check for a plausible US amateur callsign (1x1 … 2x3)."""
    pattern = re.compile(
        r'^('
        r'[AKNW][0-9][A-Z]{1,3}|'          # 1×1, 1×2, 1×3
        r'[AKNW][A-Z][0-9][A-Z]{1,3}'     # 2×1, 2×2, 2×3
        r')$'
    )
    return bool(pattern.match(call))


def callsign_codec(value: str) -> str:
    """
    Bi-directional converter:
      - Callsign  → 10-digit number (zero-padded)
      - 10-digit number → Callsign

    Raises ValueError on invalid input.
    """
    value = value.strip().upper()

    # ----- Number → Callsign -----
    if value.isdigit() and len(value) == 10:
        number = int(value)
        call = to_base36(number)
        if not is_valid_us_callsign(call):
            raise ValueError(f"Decoded '{call}' is not a valid US callsign")
        return call

    # ----- Callsign → Number -----
    # Strip common indicators (/P, /M, /7, etc.)
    call = re.sub(r'/.*$', '', value)

    if not is_valid_us_callsign(call):
        raise ValueError(f"'{value}' does not look like a valid US amateur callsign")

    number = int(call, 36)
    return f"{number:010d}"   # exactly 10 digits


# ------------------------------------------------------------------
# Interactive usage
# ------------------------------------------------------------------
if __name__ == "__main__":
    print("US Callsign ↔ 10-digit number converter")
    print("Enter a callsign or a 10-digit number (Ctrl-C to quit)\n")

    while True:
        try:
            user_input = input("> ").strip()
            if not user_input:
                continue
            result = callsign_codec(user_input)
            print(f"→ {result}\n")
        except ValueError as e:
            print(f"Error: {e}\n")
        except KeyboardInterrupt:
            print("\nBye.")
            break
