from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from app.supabase_client import supabase
from app.utils.auth import get_current_user
from app.routers.fcm import send_push_notification

router = APIRouter(prefix="/api/v1/sessions", tags=["sessions"])

class CreateSessionRequest(BaseModel):
    receiver_id: str
    skill_tag: str
    scheduled_date: datetime
    notes: Optional[str] = None

class UpdateSessionRequest(BaseModel):
    status: str

@router.post("")
def create_session(request: CreateSessionRequest, current_user = Depends(get_current_user)):
    try:
        proposer_id = current_user["id"]
        
        # Check if receiver exists
        receiver = supabase.table("profiles").select("id, username").eq("id", request.receiver_id).execute()
        if not receiver.data:
            raise HTTPException(status_code=404, detail="Receiver not found")
        
        # Create session
        new_session = {
            "proposer_id": proposer_id,
            "receiver_id": request.receiver_id,
            "skill_tag": request.skill_tag,
            "scheduled_date": request.scheduled_date.isoformat(),
            "status": "pending",
            "notes": request.notes,
            "created_at": datetime.utcnow().isoformat()
        }
        
        result = supabase.table("sessions").insert(new_session).execute()
        session = result.data[0]
        
        # Send push notification to receiver
        proposer = supabase.table("profiles").select("username").eq("id", proposer_id).execute()
        proposer_name = proposer.data[0]["username"] if proposer.data else "Someone"
        
        session_date = datetime.fromisoformat(request.scheduled_date.isoformat()).strftime("%B %d at %I:%M %p")
        
        send_push_notification(
            user_id=request.receiver_id,
            title=f"📅 Session proposal from {proposer_name}",
            body=f"{proposer_name} proposed a session about {request.skill_tag} on {session_date}",
            data={
                "type": "session_proposal",
                "proposer_id": proposer_id,
                "session_id": session["id"],
                "skill_tag": request.skill_tag
            }
        )
        
        # Get names for response
        proposer_name_data = supabase.table("profiles").select("username").eq("id", proposer_id).execute()
        receiver_name = supabase.table("profiles").select("username").eq("id", request.receiver_id).execute()
        
        session["proposer_name"] = proposer_name_data.data[0]["username"] if proposer_name_data.data else "User"
        session["receiver_name"] = receiver_name.data[0]["username"] if receiver_name.data else "User"
        
        return session
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"Create session error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("")
def get_my_sessions(current_user = Depends(get_current_user)):
    try:
        user_id = current_user["id"]
        
        sessions = supabase.table("sessions").select("*")\
            .or_(f"proposer_id.eq.{user_id},receiver_id.eq.{user_id}")\
            .order("scheduled_date", desc=False).execute()
        
        result = []
        for session in sessions.data:
            proposer = supabase.table("profiles").select("username").eq("id", session["proposer_id"]).execute()
            receiver = supabase.table("profiles").select("username").eq("id", session["receiver_id"]).execute()
            
            result.append({
                "id": session["id"],
                "proposer_id": session["proposer_id"],
                "proposer_name": proposer.data[0]["username"] if proposer.data else "User",
                "receiver_id": session["receiver_id"],
                "receiver_name": receiver.data[0]["username"] if receiver.data else "User",
                "skill_tag": session.get("skill_tag"),
                "scheduled_date": session["scheduled_date"],
                "status": session["status"],
                "created_at": session["created_at"],
                "notes": session.get("notes"),
                "is_mine": session["proposer_id"] == user_id
            })
        
        return result
    
    except Exception as e:
        print(f"Get sessions error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{session_id}")
def update_session(session_id: int, request: UpdateSessionRequest, current_user = Depends(get_current_user)):
    try:
        user_id = current_user["id"]
        
        # Check if session exists and user is involved
        session = supabase.table("sessions").select("*").eq("id", session_id).execute()
        if not session.data:
            raise HTTPException(status_code=404, detail="Session not found")
        
        session_data = session.data[0]
        if session_data["proposer_id"] != user_id and session_data["receiver_id"] != user_id:
            raise HTTPException(status_code=403, detail="Not authorized")
        
        # Update status
        update_data = {"status": request.status}
        
        if request.status == "confirmed":
            update_data["confirmed_at"] = datetime.utcnow().isoformat()
            
            # Send notification to the other person
            other_user_id = session_data["proposer_id"] if user_id == session_data["receiver_id"] else session_data["receiver_id"]
            other_user = supabase.table("profiles").select("username").eq("id", other_user_id).execute()
            other_name = other_user.data[0]["username"] if other_user.data else "User"
            current_user_name = current_user.get("username", "User")
            
            send_push_notification(
                user_id=other_user_id,
                title="✅ Session confirmed!",
                body=f"{current_user_name} confirmed the session about {session_data.get('skill_tag', 'skill exchange')}",
                data={
                    "type": "session_confirmed",
                    "session_id": session_id,
                    "confirmed_by": user_id
                }
            )
            
        elif request.status == "completed":
            update_data["completed_at"] = datetime.utcnow().isoformat()
        
        supabase.table("sessions").update(update_data).eq("id", session_id).execute()
        
        return {"message": f"Session {request.status} successfully"}
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"Update session error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    
@router.delete("/{session_id}")
def delete_session(session_id: int, current_user = Depends(get_current_user)):
    try:
        user_id = current_user["id"]
        
        session = supabase.table("sessions").select("*").eq("id", session_id).execute()
        if not session.data:
            raise HTTPException(status_code=404, detail="Session not found")
        
        if session.data[0]["proposer_id"] != user_id:
            raise HTTPException(status_code=403, detail="Only the proposer can delete")
        
        supabase.table("sessions").delete().eq("id", session_id).execute()
        
        return {"message": "Session deleted successfully"}
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"Delete session error: {e}")
        raise HTTPException(status_code=500, detail=str(e))