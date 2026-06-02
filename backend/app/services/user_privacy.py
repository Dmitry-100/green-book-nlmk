import re

_ABBREVIATED_NAME_RE = re.compile(r"(?:^|\s)([A-Za-zА-ЯЁ])\.\s*([A-Za-zА-ЯЁ])\.", re.U)
_LETTER_RE = re.compile(r"[A-Za-zА-Яа-яЁё]", re.U)


def build_public_name(display_name: str | None, fallback: str = "Наблюдатель") -> str:
    normalized = " ".join((display_name or "").strip().split())
    if not normalized:
        return fallback

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
