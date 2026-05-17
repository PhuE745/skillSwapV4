from fastapi import APIRouter, Depends
from app.supabase_client import supabase
from app.utils.auth import get_current_user

router = APIRouter(prefix="/api/v1/matches", tags=["matches"])

def matching_algo(user_skills_wanted, other_skills_offered):
    """Machine Learning: Jaccard similarity coefficient for skill matching"""
    if not user_skills_wanted or not other_skills_offered:
        return 0
    
    intersection = set(user_skills_wanted) & set(other_skills_offered)
    union = set(user_skills_wanted) | set(other_skills_offered)
    
    if not union:
        return 0
    
    # Jaccard similarity = |A ∩ B| / |A ∪ B|
    similarity = len(intersection) / len(union)
    
    # Convert to percentage
    return round(similarity * 100, 2)

@router.get("")
def get_matches(current_user = Depends(get_current_user)):
    # Get current user's wanted skills
    user_wanted = current_user.get("skills_wanted", [])
    
    if not user_wanted:
        return {"matches": [], "message": "Add interests to see matches"}
    
    # Get all other users
    all_users = supabase.table("profiles").select("*").neq("id", current_user["id"]).execute()
    
    # Calculate similarity scores
    matches = []
    for user in all_users.data:
        offered = user.get("skills_offered", [])
        score = matching_algo(user_wanted, offered)
        
        if score > 0:
            matches.append({
                "user_id": user["id"],
                "username": user.get("username", "Unknown"),
                "match_score": score,
                "skills_matched": list(set(user_wanted) & set(offered))
            })
    
    # Sort by score descending
    matches.sort(key=lambda x: x["match_score"], reverse=True)
    
    return {
        "matches": matches[:10],
        "algorithm": "Jaccard Similarity Coefficient",
        "total_matches_found": len(matches)
    }