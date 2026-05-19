from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from app.supabase_client import supabase
from app.utils.auth import get_current_user
from urllib.parse import unquote

router = APIRouter(prefix="/api/v1/users", tags=["users"])

class ProfileUpdate(BaseModel):
    username: Optional[str] = None
    full_name: Optional[str] = None
    location: Optional[str] = None
    bio: Optional[str] = None

class AddSkillRequest(BaseModel):
    skill_name: str

class AddInterestRequest(BaseModel):
    skill_name: str

@router.get("/me")
def get_me(current_user = Depends(get_current_user)):
    return current_user

@router.get("/{user_id}")
def get_user_by_id(user_id: str, current_user = Depends(get_current_user)):
    # Fetch user profile by ID
    response = supabase.table("profiles").select("*").eq("id", user_id).execute()
    
    if not response.data:
        raise HTTPException(status_code=404, detail="User not found")
    
    return response.data[0]

@router.put("/me")
def update_me(update: ProfileUpdate, current_user = Depends(get_current_user)):
    update_data = {k: v for k, v in update.dict().items() if v is not None}
    
    if update_data:
        supabase.table("profiles").update(update_data).eq("id", current_user["id"]).execute()
    
    updated = supabase.table("profiles").select("*").eq("id", current_user["id"]).execute()
    
    return updated.data[0]

@router.post("/skills")
def add_skill(skill: AddSkillRequest, current_user = Depends(get_current_user)):
    # Convert spaces to underscores for database format
    skill_name = skill.skill_name.replace(" ", "_")
    
    # Check if skill exists in skills table
    skill_exists = supabase.table("skills").select("name").eq("name", skill_name).execute()
    
    if not skill_exists.data:
        raise HTTPException(status_code=404, detail=f"Skill '{skill_name}' not found")
    
    # Fetch fresh profile
    fresh_profile = supabase.table("profiles").select("*").eq("id", current_user["id"]).execute()
    current_skills = fresh_profile.data[0].get("skills_offered")
    
    # Handle None value
    if current_skills is None:
        current_skills = []
    
    # Add new skill if not already there
    if skill_name not in current_skills:
        current_skills.append(skill_name)
    
    # Update in Supabase
    supabase.table("profiles").update({"skills_offered": current_skills}).eq("id", current_user["id"]).execute()
    
    # Return updated profile
    updated = supabase.table("profiles").select("*").eq("id", current_user["id"]).execute()
    
    return updated.data[0]

@router.delete("/skills/{skill_name}")
def remove_skill(skill_name: str, current_user = Depends(get_current_user)):
    skill_name = unquote(skill_name).replace(" ", "_")
    
    # Fetch fresh profile from Supabase
    fresh_profile = supabase.table("profiles").select("*").eq("id", current_user["id"]).execute()
    current_skills = fresh_profile.data[0].get("skills_offered")
    
    # Handle None value
    if current_skills is None:
        current_skills = []
    
    # Create new list without the skill
    new_skills = [s for s in current_skills if s != skill_name]
    
    # Update in Supabase
    supabase.table("profiles").update({"skills_offered": new_skills}).eq("id", current_user["id"]).execute()
    
    # Return updated profile
    updated = supabase.table("profiles").select("*").eq("id", current_user["id"]).execute()
    
    return updated.data[0]

@router.post("/interests")
def add_interest(interest: AddInterestRequest, current_user = Depends(get_current_user)):
    # Convert spaces to underscores for database format
    skill_name = interest.skill_name.replace(" ", "_")
    
    # Check if skill exists in skills table
    skill_exists = supabase.table("skills").select("name").eq("name", skill_name).execute()
    
    if not skill_exists.data:
        raise HTTPException(status_code=404, detail=f"Skill '{skill_name}' not found")
    
    # Fetch fresh profile from Supabase
    fresh_profile = supabase.table("profiles").select("*").eq("id", current_user["id"]).execute()
    current_interests = fresh_profile.data[0].get("skills_wanted")
    
    # Handle None value
    if current_interests is None:
        current_interests = []
    
    # Add new interest if not already there
    if skill_name not in current_interests:
        current_interests.append(skill_name)
    
    # Update in Supabase
    supabase.table("profiles").update({"skills_wanted": current_interests}).eq("id", current_user["id"]).execute()
    
    # Return updated profile
    updated = supabase.table("profiles").select("*").eq("id", current_user["id"]).execute()
    
    return updated.data[0]

@router.delete("/interests/{skill_name}")
def remove_interest(skill_name: str, current_user = Depends(get_current_user)):
    skill_name = unquote(skill_name).replace(" ", "_")
    
    # Fetch fresh profile from Supabase
    fresh_profile = supabase.table("profiles").select("*").eq("id", current_user["id"]).execute()
    current_interests = fresh_profile.data[0].get("skills_wanted")
    
    # Handle None value
    if current_interests is None:
        current_interests = []
    
    # Create new list without the skill
    new_interests = [s for s in current_interests if s != skill_name]
    
    # Update in Supabase
    supabase.table("profiles").update({"skills_wanted": new_interests}).eq("id", current_user["id"]).execute()
    
    # Return updated profile
    updated = supabase.table("profiles").select("*").eq("id", current_user["id"]).execute()
    
    return updated.data[0]