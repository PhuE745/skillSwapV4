from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from app.routers import auth, users, skills, matches, exchanges, admin, messages, posts, reviews
import threading
import time
from app.routers import sessions
from app.routers import upload
from app.routers import fcm
from app.routers import badges

load_dotenv()

app = FastAPI(title="SkillSwap API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://v4frontend-production.up.railway.app",
        "https://skillswapph-production.up.railway.app",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://127.0.0.1:5500",
        "http://localhost:5500",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5501",
        
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(skills.router)
app.include_router(matches.router)
app.include_router(exchanges.router)
app.include_router(admin.router)
app.include_router(messages.router)
app.include_router(posts.router)
app.include_router(reviews.router)
app.include_router(sessions.router)
app.include_router(upload.router)
app.include_router(fcm.router)
app.include_router(badges.router)

@app.get("/")
def root():
    return {"message": "SkillSwap API is running"}

@app.get("/health")
def health():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, http="h11")