from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from app.supabase_client import supabase
from app.utils.auth import get_current_user
from app.routers.fcm import send_push_notification

router = APIRouter(prefix="/api/v1/messages", tags=["messages"])

class SendMessageRequest(BaseModel):
    receiver_id: str
    message: str
    attachment_url: Optional[str] = None
    attachment_name: Optional[str] = None
    attachment_type: Optional[str] = None
    attachment_size: Optional[int] = None

@router.post("/send")
def send_message(request: SendMessageRequest, current_user = Depends(get_current_user)):
    sender_id = current_user["id"]
    
    # Check if receiver exists
    receiver = supabase.table("profiles").select("id, username").eq("id", request.receiver_id).execute()
    if not receiver.data:
        raise HTTPException(status_code=404, detail="Receiver not found")
    
    # Insert message with attachment support
    new_message = {
        "sender_id": sender_id,
        "receiver_id": request.receiver_id,
        "message": request.message,
        "attachment_url": request.attachment_url,
        "attachment_name": request.attachment_name,
        "attachment_type": request.attachment_type,
        "attachment_size": request.attachment_size,
        "is_read": False,
        "created_at": datetime.utcnow().isoformat()
    }
    
    result = supabase.table("messages").insert(new_message).execute()
    
    # Send push notification to receiver (don't notify yourself)
    if sender_id != request.receiver_id:
        sender = supabase.table("profiles").select("username").eq("id", sender_id).execute()
        sender_name = sender.data[0]["username"] if sender.data else "Someone"
        
        # Get message preview (truncate if too long)
        message_preview = request.message[:50] + "..." if len(request.message) > 50 else request.message
        
        send_push_notification(
            user_id=request.receiver_id,
            title=f"📩 New message from {sender_name}",
            body=message_preview,
            data={
                "type": "message",
                "sender_id": sender_id,
                "sender_name": sender_name,
                "message_id": result.data[0]["id"]
            }
        )
    
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
            
            # Check if last message has attachment
            last_message = msg["message"]
            if msg.get("attachment_name") and not last_message:
                last_message = f"📎 {msg['attachment_name']}"
            
            conversations[other_id] = {
                "user_id": other_id,
                "username": other_name,
                "last_message": last_message,
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
            "attachment_url": msg.get("attachment_url"),
            "attachment_name": msg.get("attachment_name"),
            "attachment_type": msg.get("attachment_type"),
            "attachment_size": msg.get("attachment_size"),
            "is_read": msg["is_read"],
            "created_at": msg["created_at"],
            "is_mine": msg["sender_id"] == user_id
        })
    
    return {"other_user_name": other_name, "messages": result}