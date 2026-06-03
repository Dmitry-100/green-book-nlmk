import re

_ABBREVIATED_NAME_RE = re.compile(r"(?:^|\s)([A-Za-zА-ЯЁ])\.\s*([A-Za-zА-ЯЁ])\.", re.U)
_LETTER_RE = re.compile(r"[A-Za-zА-Яа-яЁё]", re.U)
_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+", re.I)
_PHONE_RE = re.compile(
    r"(?:\+?7|8)?[\s\-()]*(?:\d[\s\-()]*){10,}", re.U
)
_RESERVED_DISPLAY_WORDS = {
    "admin",
    "админ",
    "администратор",
    "ecologist",
    "эколог",
    "нлмк",
}


def build_public_name(display_name: str | None, fallback: str = "Наблюдатель") -> str:
    normalized = " ".join((display_name or "").strip().split())
    if not normalized:
        return fallback
    if " " not in normalized and 2 <= len(normalized) <= 12:
        return normalized

    abbreviated = _ABBREVIATED_NAME_RE.search(normalized)
    if abbreviated:
        return f"{abbreviated.group(1)}{abbreviated.group(2)}".upper()

    initials: list[str] = []
    for part in normalized.split(" "):
        match = _LETTER_RE.search(part)
        if match:
            initials.append(match.group(0).upper())
        if len(initials) == 2:
            break

    return "".join(initials) or fallback


def mask_email(email: str | None) -> str | None:
    if not email:
        return None
    local, sep, domain = email.partition("@")
    if not sep:
        return "***"
    if len(local) <= 2:
        masked_local = local[0] + "***"
    else:
        masked_local = f"{local[0]}***{local[-1]}"
    return f"{masked_local}@{domain}"


def contains_email_or_phone(value: str | None) -> bool:
    if not value:
        return False
    return bool(_EMAIL_RE.search(value) or _PHONE_RE.search(value))


def contains_reserved_display_word(value: str | None) -> bool:
    normalized = (value or "").casefold()
    return any(word in normalized for word in _RESERVED_DISPLAY_WORDS)
