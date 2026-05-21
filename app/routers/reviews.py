from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from app.supabase_client import supabase
from app.utils.auth import get_current_user

router = APIRouter(prefix="/api/v1/reviews", tags=["reviews"])

class CreateReviewRequest(BaseModel):
    exchange_id: int
    rating: int
    comment: Optional[str] = None

class UpdateReviewRequest(BaseModel):
    rating: int
    comment: Optional[str] = None

@router.post("")
def create_review(request: CreateReviewRequest, current_user = Depends(get_current_user)):
    try:
        reviewer_id = current_user["id"]
        
        # Check if exchange exists and is completed
        exchange = supabase.table("exchanges").select("*").eq("id", request.exchange_id).execute()
        if not exchange.data:
            raise HTTPException(status_code=404, detail="Exchange not found")
        
        exchange_data = exchange.data[0]
        if exchange_data["status"] != "completed":
            raise HTTPException(status_code=400, detail="Can only review completed exchanges")
        
        # Check if user is part of the exchange
        if reviewer_id != exchange_data["requester_id"] and reviewer_id != exchange_data["provider_id"]:
            raise HTTPException(status_code=403, detail="Not authorized to review this exchange")
        
        # Determine who is being reviewed (the other person)
        reviewed_id = exchange_data["provider_id"] if reviewer_id == exchange_data["requester_id"] else exchange_data["requester_id"]
        
        # Check if already reviewed
        existing = supabase.table("reviews").select("*").eq("exchange_id", request.exchange_id).execute()
        if existing.data:
            raise HTTPException(status_code=400, detail="You already reviewed this exchange")
        
        # Create review
        new_review = {
            "exchange_id": request.exchange_id,
            "reviewer_id": reviewer_id,
            "reviewed_id": reviewed_id,
            "rating": request.rating,
            "comment": request.comment,
            "created_at": datetime.utcnow().isoformat()
        }
        
        supabase.table("reviews").insert(new_review).execute()
        
        # Update user's average rating
        all_reviews = supabase.table("reviews").select("rating").eq("reviewed_id", reviewed_id).execute()
        ratings = [r["rating"] for r in all_reviews.data]
        avg_rating = sum(ratings) / len(ratings) if ratings else 0
        
        supabase.table("profiles").update({"rating_avg": round(avg_rating, 2)}).eq("id", reviewed_id).execute()
        
        return {"message": "Review submitted successfully", "average_rating": round(avg_rating, 2)}
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"Create review error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/user/{user_id}")
def get_user_reviews(user_id: str, current_user = Depends(get_current_user)):
    try:
        reviews = supabase.table("reviews").select("*").eq("reviewed_id", user_id).order("created_at", desc=True).execute()
        
        # Get reviewer names
        result = []
        for review in reviews.data:
            reviewer = supabase.table("profiles").select("username").eq("id", review["reviewer_id"]).execute()
            result.append({
                "id": review["id"],
                "reviewer_id": review["reviewer_id"],
                "reviewer_name": reviewer.data[0]["username"] if reviewer.data else "Unknown",
                "rating": review["rating"],
                "comment": review["comment"],
                "created_at": review["created_at"]
            })
        
        # Get average rating
        user = supabase.table("profiles").select("rating_avg").eq("id", user_id).execute()
        avg_rating = user.data[0].get("rating_avg", 0) if user.data else 0
        
        return {"average_rating": avg_rating, "reviews": result}
    
    except Exception as e:
        print(f"Get reviews error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/exchange/{exchange_id}")
def get_review_by_exchange(exchange_id: int, current_user = Depends(get_current_user)):
    try:
        review = supabase.table("reviews").select("*").eq("exchange_id", exchange_id).execute()
        if not review.data:
            return {"exists": False}
        
        r = review.data[0]
        reviewer = supabase.table("profiles").select("username").eq("id", r["reviewer_id"]).execute()
        
        return {
            "exists": True,
            "id": r["id"],
            "exchange_id": r["exchange_id"],
            "reviewer_id": r["reviewer_id"],
            "reviewer_name": reviewer.data[0]["username"] if reviewer.data else "Unknown",
            "rating": r["rating"],
            "comment": r["comment"],
            "created_at": r["created_at"]
        }
    except Exception as e:
        print(f"Get review error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{review_id}")
def update_review(review_id: int, request: UpdateReviewRequest, current_user = Depends(get_current_user)):
    try:
        user_id = current_user["id"]
        
        # Check if review exists and belongs to user
        review = supabase.table("reviews").select("*").eq("id", review_id).execute()
        if not review.data:
            raise HTTPException(status_code=404, detail="Review not found")
        if review.data[0]["reviewer_id"] != user_id:
            raise HTTPException(status_code=403, detail="Not authorized to edit this review")
        
        # Update review
        supabase.table("reviews").update({
            "rating": request.rating,
            "comment": request.comment
        }).eq("id", review_id).execute()
        
        # Update user's average rating
        reviewed_id = review.data[0]["reviewed_id"]
        all_reviews = supabase.table("reviews").select("rating").eq("reviewed_id", reviewed_id).execute()
        ratings = [r["rating"] for r in all_reviews.data]
        avg_rating = sum(ratings) / len(ratings) if ratings else 0
        supabase.table("profiles").update({"rating_avg": round(avg_rating, 2)}).eq("id", reviewed_id).execute()
        
        return {"message": "Review updated successfully"}
    except Exception as e:
        print(f"Update review error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    
@router.get("/my")
def get_my_reviews(current_user = Depends(get_current_user)):
    """Get all reviews by the current user"""
    reviews = supabase.table("reviews").select("*").eq("reviewer_id", current_user["id"]).execute()
    return reviews.data