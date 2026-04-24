import asyncio
import os
import sys

from sqlmodel import select

# Ensure the backend root is on the import path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from src.auth.models import User, UserRole
from src.db.main import async_session_maker
from src.utils.auth import generate_password_hash


async def create_admin(email: str, password: str):
    async with async_session_maker() as session:
        # Check if user already exists
        statement = select(User).where(User.email == email.lower())
        result = await session.exec(statement)
        existing_user = result.first()

        if existing_user:
            print(f"Error: User with email '{email}' already exists.")
            return

        new_user = User(
            email=email.lower(),
            email_verified=True,
            password_hash=generate_password_hash(password),
            role=UserRole.ADMIN,
        )

        session.add(new_user)
        try:
            await session.commit()
            await session.refresh(new_user)
            print(f"Successfully created admin user!")
            print(f"Email: {new_user.email}")
            print(f"User ID: {new_user.uid}")
            print(f"Role: {new_user.role}")
            print("-" * 30)
        except Exception as e:
            await session.rollback()
            print(f"Failed to create admin user: {e}")


if __name__ == "__main__":
    print("=" * 30)
    print("  Prism Admin Seeder")
    print("=" * 30)

    email = input("Enter admin email: ").strip()
    if not email:
        print("Error: Email cannot be empty.")
        sys.exit(1)

    password = input("Enter admin password: ").strip()
    if not password:
        print("Error: Password cannot be empty.")
        sys.exit(1)

    asyncio.run(create_admin(email, password))
