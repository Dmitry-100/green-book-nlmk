#!/usr/bin/env python3
"""Find or anonymize pilot user data before corporate deployment.

Dry-run by default:
    python scripts/anonymize_pilot_personal_data.py

Apply changes:
    python scripts/anonymize_pilot_personal_data.py --apply
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.database import SessionLocal
from app.models.user import User, UserRole
from app.services.user_privacy import build_public_name, contains_email_or_phone


_FULL_NAME_LIKE_RE = re.compile(r"^[А-ЯЁ][а-яё]+(?:\s+[А-ЯЁ][а-яё]+){2,}$")


def _needs_anonymization(user: User) -> bool:
    if user.role != UserRole.employee:
        return False
    if user.email:
        return True
    if contains_email_or_phone(user.display_name):
        return True
    return bool(_FULL_NAME_LIKE_RE.match(user.display_name.strip()))


def _anonymized_name(user: User) -> str:
    public_name = build_public_name(user.display_name, fallback="")
    suffix = public_name if public_name else str(user.id)
    return f"Наблюдатель {suffix}"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="write anonymized values")
    args = parser.parse_args()

    with SessionLocal() as db:
        users = db.query(User).order_by(User.id.asc()).all()
        targets = [user for user in users if _needs_anonymization(user)]
        for user in targets:
            next_name = _anonymized_name(user)
            print(
                f"user_id={user.id} login={user.login or '-'} "
                f"display_name={user.display_name!r} -> {next_name!r}; "
                f"email={'cleared' if user.email else '-'}"
            )
            if args.apply:
                user.display_name = next_name
                user.email = None
        if args.apply:
            db.commit()
            print(f"APPLIED {len(targets)} users")
        else:
            print(f"DRY RUN {len(targets)} users; pass --apply to write changes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
