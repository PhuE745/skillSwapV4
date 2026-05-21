from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from app.supabase_client import supabase
from app.utils.auth import get_current_user

router = APIRouter(prefix="/api/v1/skills", tags=["skills"])

class SkillCreate(BaseModel):
    name: str
    category: str = "Coding"

class SkillUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None

@router.get("")
def get_all_skills(current_user = Depends(get_current_user)):
    """Get all skills"""
    response = supabase.table("skills").select("*").execute()
    return response.data

@router.post("")
def create_skill(skill: SkillCreate, current_user = Depends(get_current_user)):
    """Create a new skill (admin only)"""
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Check if skill already exists
    existing = supabase.table("skills").select("*").eq("name", skill.name).execute()
    if existing.data:
        raise HTTPException(status_code=400, detail="Skill already exists")
    
    response = supabase.table("skills").insert({
        "name": skill.name,
        "category": skill.category
    }).execute()
    
    return response.data[0]

@router.put("/{skill_id}")
def update_skill(skill_id: int, skill: SkillUpdate, current_user = Depends(get_current_user)):
    """Update a skill (admin only)"""
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    update_data = {}
    if skill.name:
        update_data["name"] = skill.name
    if skill.category:
        update_data["category"] = skill.category
    
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")
    
    response = supabase.table("skills").update(update_data).eq("id", skill_id).execute()
    
    if not response.data:
        raise HTTPException(status_code=404, detail="Skill not found")
    
    return response.data[0]

@router.delete("/{skill_id}")
def delete_skill(skill_id: int, current_user = Depends(get_current_user)):
    """Delete a skill (admin only)"""
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    response = supabase.table("skills").delete().eq("id", skill_id).execute()
    
    if not response.data:
        raise HTTPException(status_code=404, detail="Skill not found")
    
    return {"message": "Skill deleted successfully"}