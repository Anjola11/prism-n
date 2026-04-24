import argparse
import asyncio
import getpass
import os
import sys

from sqlmodel import select

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from src.auth.models import User, UserRole
from src.db.main import async_session_maker
from src.utils.auth import generate_password_hash


def parse_args():
    parser = argparse.ArgumentParser(description="Bootstrap or rotate a Prism admin user.")
    parser.add_argument("--email", required=True, help="Admin email to create or update")
    parser.add_argument(
        "--bootstrap-secret",
        required=True,
        help="One-time bootstrap secret. Must match PRISM_ADMIN_BOOTSTRAP_SECRET in the environment.",
    )
    return parser.parse_args()


async def upsert_admin(email: str, password: str):
    async with async_session_maker() as session:
        result = await session.exec(select(User).where(User.email == email.lower()))
        existing = result.first()

        password_hash = generate_password_hash(password.strip())

        if existing:
            existing.password_hash = password_hash
            existing.email_verified = True
            existing.role = UserRole.ADMIN
            session.add(existing)
        else:
            session.add(
                User(
                    email=email.lower(),
                    email_verified=True,
                    role=UserRole.ADMIN,
                    password_hash=password_hash,
                )
            )

        await session.commit()


async def main():
    args = parse_args()
    expected_secret = os.getenv("PRISM_ADMIN_BOOTSTRAP_SECRET")
    if not expected_secret:
        raise RuntimeError("PRISM_ADMIN_BOOTSTRAP_SECRET is not set in the environment.")
    if args.bootstrap_secret != expected_secret:
        raise RuntimeError("Invalid bootstrap secret.")

    password = getpass.getpass("Enter admin password: ")
    confirm_password = getpass.getpass("Confirm admin password: ")

    if not password or len(password.strip()) < 12:
        raise RuntimeError("Admin password must be at least 12 characters.")
    if password != confirm_password:
        raise RuntimeError("Passwords do not match.")

    await upsert_admin(email=args.email, password=password)
    print(f"Admin user bootstrapped successfully for {args.email}")


if __name__ == "__main__":
    asyncio.run(main())
