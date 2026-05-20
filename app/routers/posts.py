from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from app.supabase_client import supabase
from app.utils.auth import get_current_user

router = APIRouter(prefix="/api/v1/posts", tags=["posts"])

class CreatePostRequest(BaseModel):
    content: str
    skill_tag: Optional[str] = None
    attachment_url: Optional[str] = None
    attachment_name: Optional[str] = None
    attachment_type: Optional[str] = None
    attachment_size: Optional[int] = None

class UpdatePostRequest(BaseModel):
    content: Optional[str] = None
    skill_tag: Optional[str] = None

class CommentRequest(BaseModel):
    comment: str

@router.post("")
def create_post(request: CreatePostRequest, current_user = Depends(get_current_user)):
    try:
        user_id = current_user["id"]
        
        new_post = {
            "user_id": user_id,
            "content": request.content,
            "skill_tag": request.skill_tag,
            "attachment_url": request.attachment_url,
            "attachment_name": request.attachment_name,
            "attachment_type": request.attachment_type,
            "attachment_size": request.attachment_size,
            "likes_count": 0,
            "comment_count": 0,
            "created_at": datetime.utcnow().isoformat()
        }
        
        result = supabase.table("posts").insert(new_post).execute()
        
        post = result.data[0]
        post["username"] = current_user.get("username", "Unknown")
        post["user_avatar"] = (current_user.get("username", "U")[:2]).upper()
        
        return post
    
    except Exception as e:
        print(f"Create post error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("")
def get_posts(
    skill_filter: Optional[str] = None,
    limit: int = 20,
    current_user = Depends(get_current_user)
):
    try:
        user_id = current_user["id"]
        
        # Get user's skills for priority scoring
        user_profile = supabase.table("profiles").select("skills_offered, skills_wanted").eq("id", user_id).execute()
        user_offered = user_profile.data[0].get("skills_offered", []) if user_profile.data else []
        user_wanted = user_profile.data[0].get("skills_wanted", []) if user_profile.data else []
        
        # Build query
        query = supabase.table("posts").select("*")
        
        if skill_filter and skill_filter != "all":
            if skill_filter == "my_skills":
                # Filter by user's offered skills
                if user_offered:
                    query = query.in_("skill_tag", user_offered)
            elif skill_filter == "my_interests":
                # Filter by user's wanted skills
                if user_wanted:
                    query = query.in_("skill_tag", user_wanted)
        
        posts = query.order("created_at", desc=True).limit(limit).execute()
        
        # Get user info for each post
        result = []
        for post in posts.data:
            author = supabase.table("profiles").select("username").eq("id", post["user_id"]).execute()
            username = author.data[0]["username"] if author.data else "Unknown"
            
            # Calculate priority score
            priority = 0
            if post.get("skill_tag"):
                if post["skill_tag"] in user_offered:
                    priority += 50
                if post["skill_tag"] in user_wanted:
                    priority += 30
            
            # Check if user liked
            user_liked = supabase.table("post_likes").select("id").eq("post_id", post["id"]).eq("user_id", user_id).execute()
            
            # Get comments (last 3)
            comments = supabase.table("post_comments").select("*").eq("post_id", post["id"]).order("created_at", desc=True).limit(3).execute()
            comments_with_names = []
            for c in comments.data:
                commenter = supabase.table("profiles").select("username").eq("id", c["user_id"]).execute()
                comments_with_names.append({
                    "id": c["id"],
                    "user_id": c["user_id"],
                    "username": commenter.data[0]["username"] if commenter.data else "Unknown",
                    "comment": c["comment"],
                    "created_at": c["created_at"]
                })
            
            result.append({
                "id": post["id"],
                "user_id": post["user_id"],
                "username": username,
                "user_avatar": username[:2].upper() if username else "U",
                "content": post["content"],
                "skill_tag": post.get("skill_tag"),
                "attachment_url": post.get("attachment_url"),
                "attachment_name": post.get("attachment_name"),
                "attachment_type": post.get("attachment_type"),
                "attachment_size": post.get("attachment_size"),
                "likes_count": post.get("likes_count", 0),
                "comment_count": post.get("comment_count", 0),
                "user_liked": len(user_liked.data) > 0,
                "comments": comments_with_names,
                "priority_score": priority,
                "created_at": post["created_at"]
            })
        
        # Sort by priority score (higher first) then by date
        result.sort(key=lambda x: (-x["priority_score"], x["created_at"]), reverse=True)
        
        return result
    
    except Exception as e:
        print(f"Get posts error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# NEW ENDPOINT - Get posts by a specific user ID
@router.get("/user/{user_id}")
def get_user_posts(user_id: str, current_user = Depends(get_current_user)):
    try:
        # Get posts for a specific user
        posts = supabase.table("posts").select("*").eq("user_id", user_id).order("created_at", desc=True).execute()
        
        # Get user info for each post
        result = []
        for post in posts.data:
            author = supabase.table("profiles").select("username").eq("id", post["user_id"]).execute()
            username = author.data[0]["username"] if author.data else "Unknown"
            
            # Check if current user liked this post
            user_liked = supabase.table("post_likes").select("id").eq("post_id", post["id"]).eq("user_id", current_user["id"]).execute()
            
            result.append({
                "id": post["id"],
                "user_id": post["user_id"],
                "username": username,
                "user_avatar": username[:2].upper() if username else "U",
                "content": post["content"],
                "skill_tag": post.get("skill_tag"),
                "attachment_url": post.get("attachment_url"),
                "attachment_name": post.get("attachment_name"),
                "attachment_type": post.get("attachment_type"),
                "attachment_size": post.get("attachment_size"),
                "likes_count": post.get("likes_count", 0),
                "comment_count": post.get("comment_count", 0),
                "user_liked": len(user_liked.data) > 0,
                "created_at": post["created_at"]
            })
        
        return result
    
    except Exception as e:
        print(f"Get user posts error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{post_id}")
def update_post(post_id: int, request: UpdatePostRequest, current_user = Depends(get_current_user)):
    try:
        user_id = current_user["id"]
        
        post = supabase.table("posts").select("*").eq("id", post_id).execute()
        if not post.data:
            raise HTTPException(status_code=404, detail="Post not found")
        if post.data[0]["user_id"] != user_id:
            raise HTTPException(status_code=403, detail="Not authorized to edit this post")
        
        update_data = {}
        if request.content is not None:
            update_data["content"] = request.content
        if request.skill_tag is not None:
            update_data["skill_tag"] = request.skill_tag
        update_data["updated_at"] = datetime.utcnow().isoformat()
        
        supabase.table("posts").update(update_data).eq("id", post_id).execute()
        
        return {"message": "Post updated successfully"}
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"Update post error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{post_id}")
def delete_post(post_id: int, current_user = Depends(get_current_user)):
    try:
        user_id = current_user["id"]
        
        post = supabase.table("posts").select("*").eq("id", post_id).execute()
        if not post.data:
            raise HTTPException(status_code=404, detail="Post not found")
        if post.data[0]["user_id"] != user_id:
            raise HTTPException(status_code=403, detail="Not authorized to delete this post")
        
        supabase.table("posts").delete().eq("id", post_id).execute()
        
        return {"message": "Post deleted successfully"}
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"Delete post error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{post_id}/like")
def like_post(post_id: int, current_user = Depends(get_current_user)):
    try:
        user_id = current_user["id"]
        
        # Check if already liked
        existing = supabase.table("post_likes").select("*").eq("post_id", post_id).eq("user_id", user_id).execute()
        
        if existing.data:
            # Unlike
            supabase.table("post_likes").delete().eq("post_id", post_id).eq("user_id", user_id).execute()
            # Get current count
            post = supabase.table("posts").select("likes_count").eq("id", post_id).execute()
            current_count = post.data[0].get("likes_count", 0)
            supabase.table("posts").update({"likes_count": current_count - 1}).eq("id", post_id).execute()
            return {"message": "Post unliked", "liked": False}
        else:
            # Like
            supabase.table("post_likes").insert({"post_id": post_id, "user_id": user_id}).execute()
            # Get current count
            post = supabase.table("posts").select("likes_count").eq("id", post_id).execute()
            current_count = post.data[0].get("likes_count", 0)
            supabase.table("posts").update({"likes_count": current_count + 1}).eq("id", post_id).execute()
            return {"message": "Post liked", "liked": True}
    
    except Exception as e:
        print(f"Like post error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{post_id}/comment")
def add_comment(post_id: int, request: CommentRequest, current_user = Depends(get_current_user)):
    try:
        user_id = current_user["id"]
        
        # Check if post exists
        post = supabase.table("posts").select("id").eq("id", post_id).execute()
        if not post.data:
            raise HTTPException(status_code=404, detail="Post not found")
        
        new_comment = {
            "post_id": post_id,
            "user_id": user_id,
            "comment": request.comment,
            "created_at": datetime.utcnow().isoformat()
        }
        
        supabase.table("post_comments").insert(new_comment).execute()
        
        # Get current comment count
        post_data = supabase.table("posts").select("comment_count").eq("id", post_id).execute()
        current_count = post_data.data[0].get("comment_count", 0)
        supabase.table("posts").update({"comment_count": current_count + 1}).eq("id", post_id).execute()
        
        return {"message": "Comment added successfully"}
    
    except Exception as e:
        print(f"Add comment error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/comments/{comment_id}")
def delete_comment(comment_id: int, current_user = Depends(get_current_user)):
    try:
        user_id = current_user["id"]
        
        comment = supabase.table("post_comments").select("*").eq("id", comment_id).execute()
        if not comment.data:
            raise HTTPException(status_code=404, detail="Comment not found")
        if comment.data[0]["user_id"] != user_id:
            raise HTTPException(status_code=403, detail="Not authorized to delete this comment")
        
        post_id = comment.data[0]["post_id"]
        supabase.table("post_comments").delete().eq("id", comment_id).execute()
        
        # Get current comment count
        post_data = supabase.table("posts").select("comment_count").eq("id", post_id).execute()
        current_count = post_data.data[0].get("comment_count", 0)
        supabase.table("posts").update({"comment_count": current_count - 1}).eq("id", post_id).execute()
        
        return {"message": "Comment deleted successfully"}
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"Delete comment error: {e}")
        raise HTTPException(status_code=500, detail=str(e))