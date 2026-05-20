from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from app.supabase_client import supabase
from app.utils.auth import get_current_user
import firebase_admin
from datetime import datetime
from firebase_admin import credentials, messaging
import os

router = APIRouter(prefix="/api/v1/fcm", tags=["fcm"])

# Initialize Firebase Admin SDK (only once)
cred_path = os.path.join(os.path.dirname(__file__), "..", "..", "firebase-key.json")
if not firebase_admin._apps:
    cred = credentials.Certificate(cred_path)
    firebase_admin.initialize_app(cred)

class FCMTokenRequest(BaseModel):
    token: str

class SendNotificationRequest(BaseModel):
    user_id: str
    title: str
    body: str
    data: Optional[dict] = None

@router.post("/register-token")
def register_fcm_token(
    request: FCMTokenRequest,
    current_user = Depends(get_current_user)
):
    """Save user's FCM token for push notifications"""
    try:
        user_id = current_user["id"]
        
        # Check if token already exists
        existing = supabase.table("fcm_tokens").select("*").eq("user_id", user_id).eq("token", request.token).execute()
        
        if not existing.data:
            # Insert new token
            supabase.table("fcm_tokens").insert({
                "user_id": user_id,
                "token": request.token,
                "created_at": datetime.utcnow().isoformat()
            }).execute()
        
        return {"message": "Token registered successfully"}
    
    except Exception as e:
        print(f"Register token error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/unregister-token")
def unregister_fcm_token(
    request: FCMTokenRequest,
    current_user = Depends(get_current_user)
):
    """Remove user's FCM token"""
    try:
        user_id = current_user["id"]
        
        supabase.table("fcm_tokens").delete().eq("user_id", user_id).eq("token", request.token).execute()
        
        return {"message": "Token unregistered successfully"}
    
    except Exception as e:
        print(f"Unregister token error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

def send_push_notification(user_id: str, title: str, body: str, data: dict = None):
    """Send push notification to a specific user"""
    try:
        # Get user's FCM tokens
        tokens = supabase.table("fcm_tokens").select("token").eq("user_id", user_id).execute()
        
        if not tokens.data:
            return {"message": "No tokens found for user"}
        
        # Send to all user's tokens
        for token_data in tokens.data:
            token = token_data["token"]
            
            message = messaging.Message(
                notification=messaging.Notification(
                    title=title,
                    body=body,
                ),
                data=data or {},
                token=token,
            )
            
            response = messaging.send(message)
            print(f"Notification sent to {user_id}: {response}")
        
        return {"message": "Notifications sent"}
    
    except Exception as e:
        print(f"Send notification error: {e}")
        return {"error": str(e)}