# src/main.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.interfaces.api.v1.api import router as api_router
import uvicorn

app = FastAPI(
    title="BossNET API",
    description="A data intelligence platform for Bangladesh and beyond.",
    version="1.0.0",
    openapi_tags=[
        {"name": "Auth", "description": "Authentication operations"},
        {"name": "Users", "description": "User data and management"},
        {"name": "Students", "description": "Student data and performance"},
    ]
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # ⚠️ Replace with specific domains in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API route
app.include_router(api_router, prefix="/api/v1")

@app.get("/", tags=["Health Check"])
async def root():
    return {"message": "BossNET API is running!"}

# Optional: for i18n preparation (Bangla, English)
@app.get("/language", tags=["Internationalization"])
async def get_languages():
    return {"languages_supported": ["bn", "en"]}

if __name__ == "__main__":
    uvicorn.run("src.main:app", host="0.0.0.0", port=8000, reload=True)
