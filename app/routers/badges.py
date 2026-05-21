from fastapi import APIRouter, Depends
from app.supabase_client import supabase
from app.utils.auth import get_current_user

router = APIRouter(prefix="/api/v1/badges", tags=["badges"])

# All possible badges with their requirements
BADGES_CONFIG = {
    "First Step": {"icon": "🌱", "description": "Complete your first exchange", "requirement_type": "exchanges_count", "requirement_value": 1},
    "Skill Sharer": {"icon": "📚", "description": "Complete 5 exchanges as teacher", "requirement_type": "exchanges_as_teacher", "requirement_value": 5},
    "Eager Learner": {"icon": "🎓", "description": "Complete 5 exchanges as learner", "requirement_type": "exchanges_as_learner", "requirement_value": 5},
    "Master Teacher": {"icon": "⭐", "description": "Complete 20 exchanges as teacher", "requirement_type": "exchanges_as_teacher", "requirement_value": 20},
    "Dedicated Learner": {"icon": "💪", "description": "Complete 20 exchanges as learner", "requirement_type": "exchanges_as_learner", "requirement_value": 20},
    "Skill Swapper": {"icon": "🤝", "description": "Complete 10 total exchanges", "requirement_type": "exchanges_count", "requirement_value": 10},
}

@router.get("/my-badges")
def get_my_badges(current_user = Depends(get_current_user)):
    try:
        user_id = current_user["id"]
        
        # Get user's badges from profiles table
        user = supabase.table("profiles").select("badges").eq("id", user_id).execute()
        user_badges = user.data[0].get("badges", []) if user.data else []
        
        # Format badges for display
        result = []
        for badge_name in user_badges:
            if badge_name in BADGES_CONFIG:
                result.append({
                    "name": badge_name,
                    "icon": BADGES_CONFIG[badge_name]["icon"],
                    "description": BADGES_CONFIG[badge_name]["description"]
                })
        
        return result
    
    except Exception as e:
        print(f"Get badges error: {e}")
        return []

def check_and_award_badges_for_user(user_id: str):
    """Check badges for a specific user by ID"""
    try:
        # Get user stats
        user = supabase.table("profiles").select("*").eq("id", user_id).execute()
        user_data = user.data[0] if user.data else {}
        current_badges = user_data.get("badges", []) or []
        
        # Get exchange stats
        exchanges_as_requester = supabase.table("exchanges").select("*").eq("requester_id", user_id).execute()
        exchanges_as_requester = len(exchanges_as_requester.data)
        
        exchanges_as_provider = supabase.table("exchanges").select("*").eq("provider_id", user_id).execute()
        exchanges_as_provider = len(exchanges_as_provider.data)
        
        total_exchanges = exchanges_as_requester + exchanges_as_provider
        
        new_badges = []
        
        if total_exchanges >= 1 and "First Step" not in current_badges:
            new_badges.append("First Step")
        
        if exchanges_as_provider >= 5 and "Skill Sharer" not in current_badges:
            new_badges.append("Skill Sharer")
        
        if exchanges_as_requester >= 5 and "Eager Learner" not in current_badges:
            new_badges.append("Eager Learner")
        
        if exchanges_as_provider >= 20 and "Master Teacher" not in current_badges:
            new_badges.append("Master Teacher")
        
        if exchanges_as_requester >= 20 and "Dedicated Learner" not in current_badges:
            new_badges.append("Dedicated Learner")
        
        if total_exchanges >= 10 and "Skill Swapper" not in current_badges:
            new_badges.append("Skill Swapper")
        
        updated_badges = current_badges
        
        if new_badges:
            updated_badges = current_badges + new_badges
            supabase.table("profiles").update({"badges": updated_badges}).eq("id", user_id).execute()
        
        return {"new_badges": new_badges, "all_badges": updated_badges}
    
    except Exception as e:
        print(f"Check badges error for user {user_id}: {e}")
        return {"new_badges": [], "all_badges": []}

@router.post("/check-and-award")
def check_and_award_badges(current_user = Depends(get_current_user)):
    return check_and_award_badges_for_user(current_user["id"])