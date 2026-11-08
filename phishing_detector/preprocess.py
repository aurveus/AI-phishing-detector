"""Text cleaning shared by training, evaluation and the app.

The model learned from text cleaned this way, so the app has to clean what it gets in the same way. The first version
of the app skipped this and missed more phishing emails (see docs/SECURITY_AND_REVIEW.md).
"""
import re

_URL = re.compile(r"http\S+")
_EMAIL = re.compile(r"\S+@\S+")
_NON_LETTERS = re.compile(r"[^a-zA-Z\s]")


def clean_text(text: str) -> str:
    """Lowercase, turn links and addresses into the words "url" and "email", and drop everything except letters."""
    text = text.lower()
    text = _URL.sub("url", text)
    text = _EMAIL.sub("email", text)
    return _NON_LETTERS.sub("", text)
