from fastapi import APIRouter, Depends
from app.supabase_client import supabase
from app.utils.auth import get_current_user

router = APIRouter(prefix="/api/v1/skills", tags=["skills"])

@router.get("")
def get_all_skills(current_user = Depends(get_current_user)):
    response = supabase.table("skills").select("*").execute()
    return response.data