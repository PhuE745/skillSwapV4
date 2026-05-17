from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from app.routers import auth, users, skills, matches, exchanges, admin, messages, posts, reviews

load_dotenv()

app = FastAPI(title="SkillSwap API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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

# For Vercel serverless
