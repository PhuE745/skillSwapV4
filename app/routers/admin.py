from fastapi import APIRouter, Depends, HTTPException
from app.supabase_client import supabase
from app.utils.admin_check import require_admin

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])

# Get all users
@router.get("/users")
def get_all_users(admin = Depends(require_admin)):
    result = supabase.table("profiles").select("*").execute()
    return result.data

# Delete a user
@router.delete("/users/{user_id}")
def delete_user(user_id: str, admin = Depends(require_admin)):
    # Check if user exists
    user = supabase.table("profiles").select("id").eq("id", user_id).execute()
    if not user.data:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Delete using SQL (bypasses RLS)
    supabase.rpc("delete_user", {"user_id": user_id}).execute()
    
    return {"message": "User deleted successfully"}

# Change user role
@router.put("/users/{user_id}/role")
def change_role(user_id: str, role: str, admin = Depends(require_admin)):
    if role not in ["client", "admin"]:
        raise HTTPException(status_code=400, detail="Role must be 'client' or 'admin'")
    
    # Check if user exists
    user = supabase.table("profiles").select("id").eq("id", user_id).execute()
    if not user.data:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Update role using RPC
    supabase.rpc("update_user_role", {"user_id": user_id, "new_role": role}).execute()
    
    return {"message": f"User role changed to {role}"}