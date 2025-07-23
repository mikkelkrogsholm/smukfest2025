from fastapi import Depends, HTTPException, status, Request, Response
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from datetime import datetime, timedelta, timezone
from pydantic import BaseModel
from typing import Optional
import os
from dotenv import load_dotenv

# SQLAlchemy and DB dependencies
from sqlalchemy.orm import Session
from .database import get_db

# Import ORM models and CRUD functions
from . import models, crud, schemas # Import schemas for Token

# Load environment variables from .env file
load_dotenv()

# --- Configuration --- 
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
COOKIE_NAME = "smukfest_session"

if not SECRET_KEY:
    raise EnvironmentError("SECRET_KEY not found in environment variables. Please set it in .env")

# --- Password Hashing --- 
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Pydantic model for data within the JWT token
class TokenData(BaseModel):
    username: Optional[str] = None
    role: Optional[models.UserRoleEnum] = None # Use the enum from models

# OAuth2 scheme (for potential future use or Swagger UI integration)
# Note: We are primarily using cookie-based auth flow
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token") # Adjust tokenUrl if needed

# --- Password Verification --- 
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

# --- Password Hashing --- 
def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

# --- User Authentication --- 
def authenticate_user(db: Session, username: str, password: str) -> Optional[models.User]:
    """Authenticates a user based on username and password."""
    user = crud.get_user_by_username(db, username=username)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user

# --- JWT Creation --- 
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    # Expect 'sub' (username) and 'role' (enum value) in data
    if "sub" not in to_encode or "role" not in to_encode:
        raise ValueError("Missing 'sub' or 'role' in data for JWT creation")
        
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# --- Decode JWT and Get User (Internal Helper) ---
def get_user_from_token(db: Session, token: str) -> Optional[models.User]:
    """Decodes JWT, validates, and retrieves the user from DB."""
    # Debug logging removed for security - was exposing partial token
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"}, # Or appropriate scheme
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        role_str: str = payload.get("role") # Role stored as string in token
        if username is None or role_str is None:
            # Raise exception if essential data is missing
            # Invalid token payload - missing required fields
            raise credentials_exception 
        
        # Validate role string against enum
        try:
            token_role = models.UserRoleEnum(role_str)
            # Token successfully decoded
        except ValueError:
             # Invalid role value in token
            # Invalid role value in token
            raise credentials_exception
            
        token_data = TokenData(username=username, role=token_role)
    except JWTError as e:
        # Token invalid or expired
        # Token invalid or expired
        raise credentials_exception
    except Exception as e:
        # Catch any other unexpected error during decoding
        # Unexpected error during token decode
        raise credentials_exception # Re-raise as credentials error
    
    # Look up user in database
    user = crud.get_user_by_username(db, username=token_data.username)
    if user is None:
        # User from token doesn't exist in DB
        # User from token doesn't exist in DB
        raise credentials_exception

    # Verify role consistency between token and DB
    # Optional: Verify role from token matches role in DB for extra security
    if user.role != token_data.role:
        # Role mismatch between token and database
        raise credentials_exception
        
    # User validation successful
    return user

# --- Get Current User from Cookie (Used in main.py login check) --- 
def get_current_user_from_cookie(request: Request, db: Session = Depends(get_db)) -> Optional[models.User]:
    """Attempts to get the user from cookie, requires DB session. Returns User or None."""
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        return None
    try:
        # Use the helper function which handles DB lookup and validation
        user = get_user_from_token(db, token)
        return user
    except HTTPException:
        # Catches credentials_exception from get_user_from_token (invalid/expired token)
        return None 
    except Exception as e:
        # Catch unexpected errors during token processing
        print(f"Error processing cookie token: {e}")
        return None

# --- Dependency: Get Current Active User --- 
# This is the main dependency used to protect routes
async def get_current_active_user(
    request: Request, # Need request to get cookie
    db: Session = Depends(get_db) # Inject DB session
) -> models.User:
    """Dependency to get the current logged-in, active user. Raises HTTPException if inactive or not authenticated."""
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        # --- START Redirect Logic --- 
        # If no token, redirect to login, passing the original path
        original_path = request.url.path
        query_string = request.url.query
        # Basic url encoding might be needed for complex paths, but keep simple for now
        # Ensure we handle query strings correctly in the next parameter
        next_param_value = original_path
        if query_string:
            next_param_value = f"{original_path}?{query_string}"
        
        # Construct the redirect URL
        # Note: Ensure RedirectResponse is imported in main.py if not handled by exception
        redirect_url = f"/login?next={next_param_value}" # Pass original path as query param
        
        raise HTTPException(
             status_code=status.HTTP_307_TEMPORARY_REDIRECT,
             detail="Not authenticated", # Detail may not be shown on redirect
             headers={"Location": redirect_url} # Set Location header for redirect
         )
        # --- END Redirect Logic ---
    
    # Use the helper to decode token and fetch user from DB
    # This will raise 401 if token is invalid/expired or user not found
    user = get_user_from_token(db, token) 
    
    # Check if user is disabled/inactive
    if user.disabled:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user")
        
    return user # Return the ORM User object

# --- Utility to set cookie --- 
def set_auth_cookie(response: Response, token: str):
    # Determine if we're in production (HTTPS) mode
    is_production = os.getenv("PRODUCTION_MODE", "true").lower() == "true"
    
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,       # Prevent JS access
        samesite="lax",      # Good default for CSRF protection
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60, # In seconds
        secure=is_production, # Set to True in production (HTTPS), False in development
        path="/"             # Cookie applies to entire site
    )

# --- Utility to delete cookie --- 
def delete_auth_cookie(response: Response):
    response.delete_cookie(key=COOKIE_NAME, path="/")