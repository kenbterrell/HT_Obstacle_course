def nokia_keypresses(text: str) -> str:
    """
    Convert a string into Nokia multi-tap keypresses.
    Letters are case-insensitive. Space = 0.
    Unsupported characters are skipped.
    """
    # Mapping: letter → (key, number of presses)
    keypad = {
        'A': ('2', 1), 'B': ('2', 2), 'C': ('2', 3),
        'D': ('3', 1), 'E': ('3', 2), 'F': ('3', 3),
        'G': ('4', 1), 'H': ('4', 2), 'I': ('4', 3),
        'J': ('5', 1), 'K': ('5', 2), 'L': ('5', 3),
        'M': ('6', 1), 'N': ('6', 2), 'O': ('6', 3),
        'P': ('7', 1), 'Q': ('7', 2), 'R': ('7', 3), 'S': ('7', 4),
        'T': ('8', 1), 'U': ('8', 2), 'V': ('8', 3),
        'W': ('9', 1), 'X': ('9', 2), 'Y': ('9', 3), 'Z': ('9', 4),
        ' ': ('0', 1),
    }

    result = []
    prev_key = None

    for char in text.upper():
        if char not in keypad:
            continue  # skip unsupported characters

        key, presses = keypad[char]

        # If the same key is needed again, insert a pause indicator
        if key == prev_key:
            result.append('|')   # | means "wait for the timeout"

        result.append(key * presses)
        prev_key = key

    return ' '.join(result)


# Example usage
if __name__ == "__main__":
    text = input("Enter text: ")
    print(nokia_keypresses(text))