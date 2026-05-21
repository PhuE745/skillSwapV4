from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from app.supabase_client import supabase
from app.utils.auth import get_current_user

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])

# ========== MODELS ==========

class UserUpdate(BaseModel):
    username: Optional[str] = None
    role: Optional[str] = None

class ExchangeStatusUpdate(BaseModel):
    status: str

# ========== USERS ==========

@router.get("/users")
def get_all_users(current_user = Depends(get_current_user)):
    """Get all users (admin only)"""
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    users = supabase.table("profiles").select("*").execute()
    
    # Enrich with exchange counts
    result = []
    for user in users.data:
        exchanges = supabase.table("exchanges").select("*")\
            .or_(f"requester_id.eq.{user['id']},provider_id.eq.{user['id']}")\
            .execute()
        user["total_exchanges"] = len(exchanges.data)
        result.append(user)
    
    return result

@router.put("/users/{user_id}")
def update_user(user_id: str, update: UserUpdate, current_user = Depends(get_current_user)):
    """Update a user (admin only)"""
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    update_data = {}
    if update.username:
        update_data["username"] = update.username
    if update.role:
        if update.role not in ["client", "admin"]:
            raise HTTPException(status_code=400, detail="Role must be 'client' or 'admin'")
        update_data["role"] = update.role
    
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")
    
    result = supabase.table("profiles").update(update_data).eq("id", user_id).execute()
    
    if not result.data:
        raise HTTPException(status_code=404, detail="User not found")
    
    return result.data[0]

@router.delete("/users/{user_id}")
def delete_user(user_id: str, current_user = Depends(get_current_user)):
    """Delete a user (admin only)"""
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    if user_id == current_user["id"]:
        raise HTTPException(status_code=400, detail="Cannot delete your own account")
    
    user = supabase.table("profiles").select("id").eq("id", user_id).execute()
    if not user.data:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Try using your RPC function
    try:
        supabase.rpc("delete_user", {"user_id": user_id}).execute()
    except:
        # Fallback to direct delete
        supabase.table("profiles").delete().eq("id", user_id).execute()
    
    return {"message": "User deleted successfully"}

@router.put("/users/{user_id}/role")
def change_role(user_id: str, role: str, current_user = Depends(get_current_user)):
    """Set a user's role (admin only)"""
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    if role not in ["client", "admin"]:
        raise HTTPException(status_code=400, detail="Role must be 'client' or 'admin'")
    
    user = supabase.table("profiles").select("id").eq("id", user_id).execute()
    if not user.data:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Try using your RPC function
    try:
        supabase.rpc("update_user_role", {"user_id": user_id, "new_role": role}).execute()
    except:
        # Fallback to direct update
        supabase.table("profiles").update({"role": role}).eq("id", user_id).execute()
    
    return {"message": f"User role changed to {role}"}

# ========== EXCHANGES ==========

@router.get("/exchanges")
def get_all_exchanges(current_user = Depends(get_current_user)):
    """Get all exchanges (admin only)"""
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    exchanges = supabase.table("exchanges").select("*").execute()
    
    result = []
    for exchange in exchanges.data:
        # Get skill name
        skill = supabase.table("skills").select("name").eq("id", exchange["skill_id"]).execute()
        exchange["skill_name"] = skill.data[0]["name"] if skill.data else "Unknown"
        
        # Get requester username
        requester = supabase.table("profiles").select("username").eq("id", exchange["requester_id"]).execute()
        exchange["requester_name"] = requester.data[0]["username"] if requester.data else "Unknown"
        
        # Get provider username
        provider = supabase.table("profiles").select("username").eq("id", exchange["provider_id"]).execute()
        exchange["provider_name"] = provider.data[0]["username"] if provider.data else "Unknown"
        
        result.append(exchange)
    
    return result

@router.put("/exchanges/{exchange_id}/status")
def update_exchange_status(exchange_id: int, update: ExchangeStatusUpdate, current_user = Depends(get_current_user)):
    """Update exchange status (admin only)"""
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    allowed = ["pending", "accepted", "declined", "completed", "cancelled"]
    if update.status not in allowed:
        raise HTTPException(status_code=400, detail=f"Status must be one of {allowed}")
    
    result = supabase.table("exchanges").update({"status": update.status}).eq("id", exchange_id).execute()
    
    if not result.data:
        raise HTTPException(status_code=404, detail="Exchange not found")
    
    return {"message": f"Exchange {update.status} successfully"}

@router.delete("/exchanges/{exchange_id}")
def delete_exchange(exchange_id: int, current_user = Depends(get_current_user)):
    """Delete an exchange (admin only)"""
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    result = supabase.table("exchanges").delete().eq("id", exchange_id).execute()
    
    if not result.data:
        raise HTTPException(status_code=404, detail="Exchange not found")
    
    return {"message": "Exchange deleted successfully"}