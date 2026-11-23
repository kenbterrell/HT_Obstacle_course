def baofeng_keypresses(text: str) -> str:
    """
    Convert a string into Baofeng UV-5R multi-tap style keypresses.
    - Input is padded/truncated to exactly 12 characters (spaces on the right).
    - Each character is encoded with classic multi-tap presses.
    - '#' is used as the separator between characters.
    - Keypad layout is identical to a classic Nokia, so the mapping stays the same.
    """
    # Multi-tap mapping (same as Nokia / standard phone keypad)
    keypad = {
        'A': '2',    'B': '22',   'C': '222',
        'D': '3',    'E': '33',   'F': '333',
        'G': '4',    'H': '44',   'I': '444',
        'J': '5',    'K': '55',   'L': '555',
        'M': '6',    'N': '66',   'O': '666',
        'P': '7',    'Q': '77',   'R': '777',  'S': '7777',
        'T': '8',    'U': '88',   'V': '888',
        'W': '9',    'X': '99',   'Y': '999',  'Z': '9999',
        ' ': '0',
    }

    # Force exactly 12 characters (pad with spaces on the right, truncate if longer)
    text = text.upper()[:6].ljust(6)

    sequences = []
    for char in text:
        if char in keypad:
            sequences.append(keypad[char])
        else:
            # Unsupported character → treat as space
            sequences.append('0')

    # Join with '#' as separator
    return '#'.join(sequences)


# Example usage
if __name__ == "__main__":
    text = input("Enter text (will be padded/truncated to 12 chars): ")
    print(baofeng_keypresses(text))