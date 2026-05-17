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
        
        # IMPORTANT: Truncate password for Supabase Auth
        safe_password = user.password[:72]  # Force truncate to 72 chars
        
        # Create user in Supabase Auth
        auth_response = supabase.auth.sign_up({
            "email": user.email,
            "password": safe_password,
        })
        
        if not auth_response.user:
            raise HTTPException(status_code=400, detail="Registration failed")
        
        # Hash password for local storage
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
    try:
        # IMPORTANT: Truncate password for Supabase Auth
        safe_password = request.password[:72]
        
        # Authenticate with Supabase
        auth_response = supabase.auth.sign_in_with_password({
            "email": request.email,
            "password": safe_password,
        })
        
        if not auth_response.user:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        # Get profile
        profile = supabase.table("profiles").select("*").eq("id", auth_response.user.id).execute()
        
        if not profile.data:
            raise HTTPException(status_code=404, detail="Profile not found")
        
        # Create token
        token = create_access_token({"sub": auth_response.user.id})
        
        return {"access_token": token, "token_type": "bearer", "user": profile.data[0]}
    
    except Exception as e:
        print(f"LOGIN ERROR: {e}")
        raise HTTPException(status_code=500, detail=str(e))