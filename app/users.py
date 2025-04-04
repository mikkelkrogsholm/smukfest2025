import os
from dotenv import load_dotenv
from pydantic import BaseModel
from typing import Optional, Literal
from . import auth # To use verify_password

# Load environment variables from .env file
load_dotenv()

# --- User Model with Roles --- 
class User(BaseModel):
    username: str
    hashed_password: str
    role: Literal["user", "admin"] # Define possible roles
    # Add other fields like full_name, email, disabled, etc. in a real app

# --- Simulated User Database --- 
# In a real app, fetch this from your actual database
DEMO_USERNAME = os.getenv("DEMO_USERNAME")
DEMO_PASSWORD_HASH = os.getenv("DEMO_PASSWORD_HASH")
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME")
ADMIN_PASSWORD_HASH = os.getenv("ADMIN_PASSWORD_HASH")

# Default values if not set in .env (especially useful for initial setup/testing)
if not DEMO_USERNAME:
    print("Warning: DEMO_USERNAME not set in .env. Using default 'smuk'.")
    DEMO_USERNAME = "smuk"
if not DEMO_PASSWORD_HASH:
    print("Warning: DEMO_PASSWORD_HASH not set in .env. Using default hash for 'storcigar'.")
    # Use the known hash for 'storcigar' as a fallback if needed
    DEMO_PASSWORD_HASH = "$2b$12$aKB7SHq.vDLOW7Ln9YhpaeEbfn.rorKbAUZEcZ/KHp02fK5Q4gVby"

if not ADMIN_USERNAME:
    print("Warning: ADMIN_USERNAME not set in .env. Using default 'admin'.")
    ADMIN_USERNAME = "admin"
if not ADMIN_PASSWORD_HASH:
    print("Warning: ADMIN_PASSWORD_HASH not set in .env. Using default hash for 'adminpass'.")
    # Provide a default hash for the admin if not set
    ADMIN_PASSWORD_HASH = auth.get_password_hash("adminpass") 

# Store user info including roles
fake_users_db = {
    DEMO_USERNAME: {
        "username": DEMO_USERNAME,
        "hashed_password": DEMO_PASSWORD_HASH,
        "role": "user" # Assign role
    },
    ADMIN_USERNAME: {
        "username": ADMIN_USERNAME,
        "hashed_password": ADMIN_PASSWORD_HASH,
        "role": "admin" # Assign role
    }
}

# --- User Retrieval Functions --- 
def get_user(username: str) -> Optional[User]:
    """Retrieves user details (including role) from our fake DB."""
    if username in fake_users_db:
        user_dict = fake_users_db[username]
        return User(**user_dict)
    return None

def authenticate_user(username: str, password: str) -> Optional[User]:
    """Authenticates a user based on username and password."""
    user = get_user(username)
    if not user:
        return None # User not found
    if not auth.verify_password(password, user.hashed_password):
        return None # Invalid password
    return user # Authentication successful 