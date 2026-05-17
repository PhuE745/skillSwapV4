from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from app.supabase_client import supabase
from app.utils.auth import get_current_user

router = APIRouter(prefix="/api/v1/exchanges", tags=["exchanges"])

class CreateExchangeRequest(BaseModel):
    provider_id: str
    skill_name: str
    scheduled_date: str

class UpdateExchangeRequest(BaseModel):
    status: str  # "accepted", "declined", "completed"

@router.post("")
def create_exchange(request: CreateExchangeRequest, current_user = Depends(get_current_user)):
    try:
        requester_id = current_user["id"]
        
        # Prevent self-exchange
        if requester_id == request.provider_id:
            raise HTTPException(status_code=400, detail="Cannot request exchange with yourself")
        
        # Get skill_id from skill name
        skill = supabase.table("skills").select("id").eq("name", request.skill_name).execute()
        
        if not skill.data:
            raise HTTPException(status_code=404, detail=f"Skill '{request.skill_name}' not found")
        
        skill_id = skill.data[0]["id"]
        
        # Check if provider exists
        provider = supabase.table("profiles").select("id").eq("id", request.provider_id).execute()
        
        if not provider.data:
            raise HTTPException(status_code=404, detail="Provider not found")
        
        # Create exchange
        new_exchange = {
            "requester_id": requester_id,
            "provider_id": request.provider_id,
            "skill_id": skill_id,
            "status": "pending",
            "scheduled_date": request.scheduled_date,
            "created_at": datetime.utcnow().isoformat()
        }
        
        result = supabase.table("exchanges").insert(new_exchange).execute()
        
        return result.data[0]
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"ERROR: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("")
def get_my_exchanges(current_user = Depends(get_current_user)):
    user_id = current_user["id"]
    
    # Get exchanges where user is requester or provider
    exchanges = supabase.table("exchanges").select("*")\
        .or_(f"requester_id.eq.{user_id},provider_id.eq.{user_id}")\
        .execute()
    
    # Enrich with skill names and user details
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

@router.put("/{exchange_id}")
def update_exchange(exchange_id: int, request: UpdateExchangeRequest, current_user = Depends(get_current_user)):
    user_id = current_user["id"]
    
    # Get the exchange
    exchange = supabase.table("exchanges").select("*").eq("id", exchange_id).execute()
    
    if not exchange.data:
        raise HTTPException(status_code=404, detail="Exchange not found")
    
    exchange = exchange.data[0]
    
    # Check if user is part of this exchange
    if user_id != exchange["requester_id"] and user_id != exchange["provider_id"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Validate status
    allowed = ["accepted", "declined", "completed"]
    if request.status not in allowed:
        raise HTTPException(status_code=400, detail=f"Status must be one of {allowed}")
    
    # Update
    supabase.table("exchanges").update({"status": request.status}).eq("id", exchange_id).execute()
    
    return {"message": f"Exchange {request.status} successfully"}