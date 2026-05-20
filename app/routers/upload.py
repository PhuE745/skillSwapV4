from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from app.supabase_client import supabase
from app.utils.auth import get_current_user
import uuid
from datetime import datetime

router = APIRouter(prefix="/api/v1/upload", tags=["upload"])

@router.post("/file")
async def upload_file(
    file: UploadFile = File(...),
    current_user = Depends(get_current_user)
):
    try:
        # Validate file size (max 10MB)
        file_content = await file.read()
        file_size = len(file_content)
        
        if file_size > 10 * 1024 * 1024:  # 10MB limit
            raise HTTPException(status_code=400, detail="File too large. Max 10MB")
        
        # Generate unique filename
        original_filename = file.filename
        file_ext = original_filename.split('.')[-1] if '.' in original_filename else ''
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        unique_filename = f"{current_user['id']}/{timestamp}_{uuid.uuid4().hex[:8]}.{file_ext}"
        
        # Upload to Supabase Storage
        upload_result = supabase.storage.from_("attachments").upload(
            unique_filename,
            file_content,
            {"content-type": file.content_type}
        )
        
        # Get public URL
        file_url = supabase.storage.from_("attachments").get_public_url(unique_filename)
        
        return {
            "success": True,
            "url": file_url,
            "name": original_filename,
            "size": file_size,
            "type": file.content_type
        }
        
    except Exception as e:
        print(f"Upload error: {e}")
        raise HTTPException(status_code=500, detail=str(e))