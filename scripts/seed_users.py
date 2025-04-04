# scripts/seed_users.py
import os
import sys
from sqlalchemy.orm import Session
from sqlalchemy import select

# Add project root to sys.path to allow importing 'app' modules
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(PROJECT_ROOT)

# Import necessary components from the app
from app.database import SessionLocal # Import session factory
from app.models import User, UserRoleEnum # Import ORM model and enum

# User data (username, hashed password, role)
USERS_TO_SEED = [
    {
        "username": "smuk",
        "hashed_password": "$2b$12$aKB7SHq.vDLOW7Ln9YhpaeEbfn.rorKbAUZEcZ/KHp02fK5Q4gVby",
        "role": UserRoleEnum.USER,
        "email": None, # Optional fields
        "disabled": False,
    },
    {
        "username": "admin",
        "hashed_password": "$2b$12$BaKodnki2XiF0l2yoJIRC.jY5G2iSdMneB/UpJkvt2kXiHc9Imeni",
        "role": UserRoleEnum.ADMIN,
        "email": None, # Optional fields
        "disabled": False,
    },
]

def seed_users(db: Session):
    print("--- Seeding Users ---")
    user_count = 0
    for user_data in USERS_TO_SEED:
        # Check if user exists
        existing_user = db.execute(
            select(User).filter(User.username == user_data["username"])
        ).scalar_one_or_none()

        if existing_user:
            print(f"User '{user_data['username']}' already exists. Skipping.")
        else:
            print(f"Creating user '{user_data['username']}' (Role: {user_data['role'].value})...")
            db_user = User(
                username=user_data["username"],
                hashed_password=user_data["hashed_password"],
                role=user_data["role"],
                email=user_data.get("email"), 
                disabled=user_data.get("disabled", False),
            )
            db.add(db_user)
            user_count += 1
    
    if user_count > 0:
        try:        
            db.commit()
            print(f"Successfully committed {user_count} new user(s).")
        except Exception as e:
            print(f"ERROR committing users: {e}")
            db.rollback()
            print("Rolled back changes.")
    else:
        print("No new users to add.")
    print("--- User Seeding Complete ---")

if __name__ == "__main__":
    print("Creating database session...")
    # Create a new session explicitly for this script
    db = SessionLocal()
    try:
        # Ensure tables exist first (optional but safe)
        # You might need to import Base and engine if you uncomment this
        # from app.models import Base
        # from app.database import engine
        # Base.metadata.create_all(bind=engine)
        
        # Seed the users
        seed_users(db)
    except Exception as e:
        print(f"An error occurred during seeding: {e}")
    finally:
        print("Closing database session.")
        db.close() 