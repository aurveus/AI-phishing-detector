"""Plain-language warning signs found in an email, to sit next to the model's verdict.

These are simple, readable checks. They are NOT used by the model and do not change its score; they exist so a person
can see *why* an email looks suspicious and check it themselves.
"""
import re

URGENCY = ("urgent", "immediately", "act now", "within 24 hours", "suspended", "final notice", "expires", "last warning",
           "verify your account", "account will be closed", "limited time")
CREDENTIALS = ("password", "pin number", "social security", "ssn", "credit card", "card number", "bank account",
               "login details", "confirm your identity", "security code")
SHORTENERS = ("bit.ly", "tinyurl.com", "t.co", "goo.gl", "ow.ly", "is.gd", "cutt.ly", "rb.gy")

_URL = re.compile(r"(?:https?://|www\.)[^\s<>\"')]+", re.I)
_IP_HOST = re.compile(r"^(?:https?://)?\d{1,3}(?:\.\d{1,3}){3}(?:[:/]|$)", re.I)


def defang(url: str) -> str:
    """Make a link harmless to display and impossible to click by accident: hxxp://example[.]com"""
    return re.sub(r"^http", "hxxp", url, flags=re.I).replace(".", "[.]")


def find_signals(text: str) -> list:
    """Return a list of short, human-readable findings (empty if nothing stands out)."""
    low = text.lower()
    found = []
    urls = _URL.findall(text)
    if urls:
        found.append(f"Contains {len(urls)} link{'s' if len(urls) != 1 else ''}. Hover before you click: the visible text can hide the real address.")
    if any(_IP_HOST.match(u) for u in urls):
        found.append("A link points to a bare IP address instead of a company domain.")
    if any(s in u.lower() for u in urls for s in SHORTENERS):
        found.append("A link uses a URL shortener, which hides where it really goes.")
    if any(u.lower().startswith("http://") for u in urls):
        found.append("A link is not encrypted (http, not https).")
    hits = [w for w in URGENCY if w in low]
    if hits:
        found.append("Pressure or urgency wording: " + ", ".join(f'"{w}"' for w in hits[:4]) + ".")
    hits = [w for w in CREDENTIALS if w in low]
    if hits:
        found.append("Asks for sensitive information: " + ", ".join(f'"{w}"' for w in hits[:4]) + ".")
    letters = [c for c in text if c.isalpha()]
    if len(letters) > 40 and sum(c.isupper() for c in letters) / len(letters) > 0.4:
        found.append("Large amounts of ALL-CAPS text.")
    return found


def defanged_links(text: str, limit: int = 5) -> list:
    return [defang(u) for u in _URL.findall(text)[:limit]]
