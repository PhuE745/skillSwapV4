from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.supabase_client import supabase
from app.auth import hash_password, create_access_token

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

class RegisterRequest(BaseModel):
    email: str
    password: str
    username: str

class LoginRequest(BaseModel):
    email: str
    password: str

@router.post("/register")
def register(user: RegisterRequest):
    try:
        # Check if user exists
        existing = supabase.table("profiles").select("*").eq("email", user.email).execute()
        if existing.data:
            raise HTTPException(status_code=400, detail="Email already registered")
        
        # ENSURE PASSWORD IS ASCII AND TRUNCATED TO 72 BYTES
        # Convert to ASCII, ignore non-ASCII chars
        safe_password = user.password.encode('ascii', 'ignore').decode()[:72]
        
        # Create user in Supabase Auth
        auth_response = supabase.auth.sign_up({
            "email": user.email,
            "password": safe_password,
        })
        
        if not auth_response.user:
            raise HTTPException(status_code=400, detail="Registration failed")
        
        # Hash the ORIGINAL password (bcrypt handles Unicode)
        hashed = hash_password(user.password)
        
        # Create profile
        profile_data = {
            "id": auth_response.user.id,
            "email": user.email,
            "username": user.username,
            "password_hash": hashed,
            "role": "client",
            "skills_offered": [],
            "skills_wanted": []
        }
        supabase.table("profiles").insert(profile_data).execute()
        
        # Create token
        token = create_access_token({"sub": auth_response.user.id})
        
        return {"access_token": token, "token_type": "bearer", "user": {"id": auth_response.user.id, "email": user.email, "username": user.username}}
    
    except Exception as e:
        print(f"REGISTER ERROR: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/login")
def login(request: LoginRequest):
    """
    Authenticate a user.
    
    - Uses Supabase Auth for password verification (not profiles.password_hash)
    - Password truncated to 72 chars for Supabase Auth compatibility
    - Returns JWT token and user profile data
    """
    try:
        # Supabase Auth has a 72-character password limit
        safe_password = request.password[:72]
        
        # Authenticate with Supabase Auth (this verifies the password)
        auth_response = supabase.auth.sign_in_with_password({
            "email": request.email,
            "password": safe_password,
        })
        
        if not auth_response.user:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        # Get profile data from public.profiles table
        profile = supabase.table("profiles").select("*").eq("id", auth_response.user.id).execute()
        
        if not profile.data:
            raise HTTPException(status_code=404, detail="Profile not found")
        
        # Create JWT token
        token = create_access_token({"sub": auth_response.user.id})
        
        return {
            "access_token": token, 
            "token_type": "bearer", 
            "user": profile.data[0]  # password_hash is excluded from response
        }
    
    except Exception as e:
        print(f"LOGIN ERROR: {e}")
        raise HTTPException(status_code=500, detail=str(e))