from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from app.supabase_client import supabase
from app.utils.auth import get_current_user

router = APIRouter(prefix="/api/v1/messages", tags=["messages"])

class SendMessageRequest(BaseModel):
    receiver_id: str
    message: str

@router.post("/send")
def send_message(request: SendMessageRequest, current_user = Depends(get_current_user)):
    sender_id = current_user["id"]
    
    # Check if receiver exists
    receiver = supabase.table("profiles").select("id").eq("id", request.receiver_id).execute()
    if not receiver.data:
        raise HTTPException(status_code=404, detail="Receiver not found")
    
    # Insert message
    new_message = {
        "sender_id": sender_id,
        "receiver_id": request.receiver_id,
        "message": request.message,
        "is_read": False,
        "created_at": datetime.utcnow().isoformat()
    }
    
    result = supabase.table("messages").insert(new_message).execute()
    
    return {"message": "Message sent successfully", "data": result.data[0]}

@router.get("/conversations")
def get_conversations(current_user = Depends(get_current_user)):
    user_id = current_user["id"]
    
    # Get all messages where user is sender or receiver
    messages = supabase.table("messages").select("*")\
        .or_(f"sender_id.eq.{user_id},receiver_id.eq.{user_id}")\
        .order("created_at", desc=True)\
        .execute()
    
    # Group by other user
    conversations = {}
    for msg in messages.data:
        other_id = msg["receiver_id"] if msg["sender_id"] == user_id else msg["sender_id"]
        
        if other_id not in conversations:
            other_user = supabase.table("profiles").select("username").eq("id", other_id).execute()
            other_name = other_user.data[0]["username"] if other_user.data else "Unknown"
            
            conversations[other_id] = {
                "user_id": other_id,
                "username": other_name,
                "last_message": msg["message"],
                "last_message_time": msg["created_at"],
                "unread_count": 0 if msg["sender_id"] == user_id else (0 if msg["is_read"] else 1)
            }
    
    return list(conversations.values())

@router.get("/{other_user_id}")
def get_messages(other_user_id: str, current_user = Depends(get_current_user)):
    user_id = current_user["id"]
    
    # Get all messages between current user and other user
    messages = supabase.table("messages").select("*")\
        .or_(f"and(sender_id.eq.{user_id},receiver_id.eq.{other_user_id}),and(sender_id.eq.{other_user_id},receiver_id.eq.{user_id})")\
        .order("created_at")\
        .execute()
    
    # Mark messages as read
    for msg in messages.data:
        if msg["receiver_id"] == user_id and not msg["is_read"]:
            supabase.table("messages").update({"is_read": True}).eq("id", msg["id"]).execute()
    
    # Get other user's name
    other_user = supabase.table("profiles").select("username").eq("id", other_user_id).execute()
    other_name = other_user.data[0]["username"] if other_user.data else "Unknown"
    
    result = []
    for msg in messages.data:
        result.append({
            "id": msg["id"],
            "sender_id": msg["sender_id"],
            "receiver_id": msg["receiver_id"],
            "message": msg["message"],
            "is_read": msg["is_read"],
            "created_at": msg["created_at"],
            "is_mine": msg["sender_id"] == user_id
        })
    
    return {"other_user_name": other_name, "messages": result}

class ScheduleMessageRequest(BaseModel):
    receiver_id: str
    message: str
    scheduled_for: str

@router.post("/schedule")
def schedule_message(request: ScheduleMessageRequest, current_user = Depends(get_current_user)):
    sender_id = current_user["id"]
    
    # Check if receiver exists
    receiver = supabase.table("profiles").select("id").eq("id", request.receiver_id).execute()
    if not receiver.data:
        raise HTTPException(status_code=404, detail="Receiver not found")
    
    # Insert scheduled message
    scheduled_message = {
        "sender_id": sender_id,
        "receiver_id": request.receiver_id,
        "message": request.message,
        "scheduled_for": request.scheduled_for,
        "status": "pending"
    }
    
    result = supabase.table("scheduled_messages").insert(scheduled_message).execute()
    
    return {"message": "Message scheduled successfully", "data": result.data[0]}