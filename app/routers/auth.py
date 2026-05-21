import os
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from datetime import datetime, timedelta
from typing import Optional
from app.supabase_client import supabase
from app.auth import hash_password, create_access_token
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

class RegisterRequest(BaseModel):
    email: str
    password: str
    username: str
    pin: str  # 4-digit PIN for password reset

class LoginRequest(BaseModel):
    email: str
    password: str
    pin: str

class VerifyPinRequest(BaseModel):
    email: str
    pin: str

class ResetPasswordRequest(BaseModel):
    email: str
    pin: str
    new_password: str

@router.post("/register")
def register(user: RegisterRequest):
    try:
        # Validate PIN
        if not user.pin or not user.pin.isdigit() or len(user.pin) != 4:
            raise HTTPException(status_code=400, detail="PIN must be 4 digits")
        
        # Check if user exists
        existing = supabase.table("profiles").select("*").eq("email", user.email).execute()
        if existing.data:
            raise HTTPException(status_code=400, detail="Email already registered")
        
        # ENSURE PASSWORD IS ASCII AND TRUNCATED TO 72 BYTES
        safe_password = user.password.encode('ascii', 'ignore').decode()[:72]
        
        # Create user in Supabase Auth
        auth_response = supabase.auth.sign_up({
            "email": user.email,
            "password": safe_password,
        })
        
        if not auth_response.user:
            raise HTTPException(status_code=400, detail="Registration failed")
        
        # Hash the password and PIN
        hashed_password = hash_password(user.password)
        hashed_pin = pwd_context.hash(user.pin)
        
        # UPDATE existing profile (created by Supabase Auth trigger) instead of INSERT
        supabase.table("profiles").update({
            "password_hash": hashed_password,
            "pin_hash": hashed_pin,
            "pin_attempts": 0,
            "pin_locked_until": None,
            "role": "client",
            "skills_offered": [],
            "skills_wanted": []
        }).eq("id", auth_response.user.id).execute()
        
        # FORCE update username to override any trigger
        supabase.table("profiles").update({
            "username": user.username
        }).eq("id", auth_response.user.id).execute()
        
        # Create token
        token = create_access_token({"sub": auth_response.user.id})
        
        return {"access_token": token, "token_type": "bearer", "user": {"id": auth_response.user.id, "email": user.email, "username": user.username}}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/login")
def login(request: LoginRequest):
    """
    Authenticate a user with email, password, and PIN.
    """
    try:
        # First, get user profile from database
        profile = supabase.table("profiles").select("*").eq("email", request.email).execute()
        
        if not profile.data:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        user = profile.data[0]
        
        # Check if account is locked due to too many failed PIN attempts
        if user.get("pin_locked_until"):
            lock_until = datetime.fromisoformat(user["pin_locked_until"])
            if datetime.utcnow() < lock_until:
                remaining_minutes = int((lock_until - datetime.utcnow()).total_seconds() / 60)
                raise HTTPException(status_code=429, detail=f"Account locked. Try again in {remaining_minutes} minutes")
        
        # Verify PIN first
        if not pwd_context.verify(request.pin, user["pin_hash"]):
            # Increment failed PIN attempts
            new_attempts = user.get("pin_attempts", 0) + 1
            
            # Lock after 5 failed attempts
            if new_attempts >= 5:
                lock_until = datetime.utcnow() + timedelta(minutes=15)
                supabase.table("profiles").update({
                    "pin_attempts": new_attempts,
                    "pin_locked_until": lock_until.isoformat()
                }).eq("id", user["id"]).execute()
                raise HTTPException(status_code=429, detail="Too many failed PIN attempts. Account locked for 15 minutes")
            else:
                supabase.table("profiles").update({"pin_attempts": new_attempts}).eq("id", user["id"]).execute()
            
            raise HTTPException(status_code=401, detail="Invalid PIN")
        
        # Reset PIN attempts on successful verification
        supabase.table("profiles").update({
            "pin_attempts": 0,
            "pin_locked_until": None
        }).eq("id", user["id"]).execute()
        
        # Now verify password with Supabase Auth
        safe_password = request.password[:72]
        
        auth_response = supabase.auth.sign_in_with_password({
            "email": request.email,
            "password": safe_password,
        })
        
        if not auth_response.user:
            raise HTTPException(status_code=401, detail="Invalid password")
        
        # Create JWT token
        token = create_access_token({"sub": auth_response.user.id})
        
        return {
            "access_token": token, 
            "token_type": "bearer", 
            "user": user
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/verify-pin")
def verify_pin(request: VerifyPinRequest):
    """
    Verify user's 4-digit PIN for password reset.
    Includes rate limiting (5 attempts = 15 min lockout).
    """
    try:
        # Get user profile
        profile = supabase.table("profiles").select("*").eq("email", request.email).execute()
        
        if not profile.data:
            raise HTTPException(status_code=404, detail="Email not found")
        
        user = profile.data[0]
        
        # Check if account is locked
        if user.get("pin_locked_until"):
            lock_until = datetime.fromisoformat(user["pin_locked_until"])
            if datetime.utcnow() < lock_until:
                remaining_minutes = int((lock_until - datetime.utcnow()).total_seconds() / 60)
                raise HTTPException(status_code=429, detail=f"Too many attempts. Try again in {remaining_minutes} minutes")
        
        # Verify PIN
        if not pwd_context.verify(request.pin, user["pin_hash"]):
            # Increment failed attempts
            new_attempts = user.get("pin_attempts", 0) + 1
            
            # Lock after 5 failed attempts
            if new_attempts >= 5:
                lock_until = datetime.utcnow() + timedelta(minutes=15)
                supabase.table("profiles").update({
                    "pin_attempts": new_attempts,
                    "pin_locked_until": lock_until.isoformat()
                }).eq("id", user["id"]).execute()
                raise HTTPException(status_code=429, detail="Too many failed attempts. Account locked for 15 minutes")
            else:
                supabase.table("profiles").update({"pin_attempts": new_attempts}).eq("id", user["id"]).execute()
            
            raise HTTPException(status_code=401, detail="Invalid PIN")
        
        # Reset attempts on successful verification
        supabase.table("profiles").update({
            "pin_attempts": 0,
            "pin_locked_until": None
        }).eq("id", user["id"]).execute()
        
        # Return temporary token for password reset (valid for 10 minutes)
        reset_token = create_access_token(
            {"sub": user["id"], "purpose": "password_reset"},
            expires_delta=timedelta(minutes=10)
        )
        
        return {"success": True, "reset_token": reset_token}
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/reset-password")
def reset_password(request: ResetPasswordRequest):
    """
    Reset password after PIN verification.
    Updates both profiles table AND Supabase Auth password.
    """
    try:
        # Get user profile
        profile = supabase.table("profiles").select("*").eq("email", request.email).execute()
        
        if not profile.data:
            raise HTTPException(status_code=404, detail="Email not found")
        
        user = profile.data[0]
        
        # Verify PIN
        if not pwd_context.verify(request.pin, user["pin_hash"]):
            raise HTTPException(status_code=401, detail="Invalid PIN")
        
        # Hash new password
        new_hashed_password = hash_password(request.new_password)
        
        # Update password in profiles table
        supabase.table("profiles").update({
            "password_hash": new_hashed_password
        }).eq("id", user["id"]).execute()
        
        # ALSO UPDATE SUPABASE AUTH PASSWORD using admin API
        try:
            # Get the service role key from environment variable
            supabase_admin_url = os.getenv("SUPABASE_URL")
            supabase_service_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
            
            if supabase_service_key:
                from supabase import create_client
                supabase_admin = create_client(supabase_admin_url, supabase_service_key)
                
                # Update user password in Supabase Auth
                supabase_admin.auth.admin.update_user_by_id(
                    user["id"],
                    {"password": request.new_password}
                )
        except Exception:
            # Don't fail the request - profile password is updated
            pass
        
        return {"success": True, "message": "Password reset successfully"}
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))