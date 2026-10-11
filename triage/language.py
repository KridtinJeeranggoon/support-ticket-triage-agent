"""A small script heuristic for this assignment's English/Thai conversations.

Not a general language detector: other Latin-script languages are not identified.
Ambiguous/non-Latin conversations receive no automated language constraint.
"""


def reply_language(text: str) -> str | None:
    thai = sum("\u0e00" <= char <= "\u0e7f" for char in text)
    latin = sum(char.isascii() and char.isalpha() for char in text)
    other = sum(char.isalpha() and not char.isascii() and not ("\u0e00" <= char <= "\u0e7f") for char in text)
    if other > max(thai, latin):
        return None
    if thai > latin:
        return "th"
    if latin > thai:
        return "en"
    return None
