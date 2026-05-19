import time
from datetime import datetime
from app.supabase_client import supabase

def process_scheduled_messages():
    """Send all pending messages that are due"""
    now = datetime.utcnow().isoformat()
    
    # Get pending messages scheduled for now or earlier
    messages = supabase.table("scheduled_messages")\
        .select("*")\
        .eq("status", "pending")\
        .lte("scheduled_for", now)\
        .execute()
    
    for msg in messages.data:
        try:
            # Insert into messages table
            new_message = {
                "sender_id": msg["sender_id"],
                "receiver_id": msg["receiver_id"],
                "message": msg["message"],
                "is_read": False,
                "created_at": datetime.utcnow().isoformat()
            }
            supabase.table("messages").insert(new_message).execute()
            
            # Mark as sent
            supabase.table("scheduled_messages")\
                .update({"status": "sent", "sent_at": datetime.utcnow().isoformat()})\
                .eq("id", msg["id"])\
                .execute()
            
            print(f"✅ Sent scheduled message {msg['id']}")
        except Exception as e:
            print(f"❌ Failed to send message {msg['id']}: {e}")
            supabase.table("scheduled_messages")\
                .update({"status": "failed"})\
                .eq("id", msg["id"])\
                .execute()

def run_scheduler():
    """Run continuously, check every 60 seconds"""
    print("🕐 Scheduler started. Checking for scheduled messages every 60 seconds...")
    while True:
        try:
            process_scheduled_messages()
        except Exception as e:
            print(f"Scheduler error: {e}")
        time.sleep(60)

if __name__ == "__main__":
    run_scheduler()