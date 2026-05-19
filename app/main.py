from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from app.routers import auth, users, skills, matches, exchanges, admin, messages, posts, reviews
import threading
import time
from app.scheduler_worker import process_scheduled_messages

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

@app.get("/")
def root():
    return {"message": "SkillSwap API is running"}

@app.get("/health")
def health():
    return {"status": "healthy"}

# Start background scheduler for scheduled messages
def start_scheduler():
    print("🕐 Scheduler thread started")
    while True:
        time.sleep(60)
        try:
            process_scheduled_messages()
        except Exception as e:
            print(f"Scheduler error: {e}")

scheduler_thread = threading.Thread(target=start_scheduler, daemon=True)
scheduler_thread.start()

# For Vercel serverless