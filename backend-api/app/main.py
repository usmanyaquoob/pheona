# backend-api/app/main.py
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .config import settings
from .routes.agents import router as agents_router

app = FastAPI(title="Pheona Backend", version="0.1.0")

# CORS: allow localhost in dev, and optionally a regex (e.g., *.streamlit.app) on deploy.
# FastAPI/Starlette CORS supports allow_origin_regex. :contentReference[oaicite:3]{index=3}
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_origin_regex=settings.FRONTEND_ALLOWED_ORIGIN_REGEX,
    allow_credentials=False,  # keep false unless you actually use cookies
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(agents_router)

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=False)
