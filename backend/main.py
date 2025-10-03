from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
import os

app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "SEO Engine Backend is running!"}

@app.get("/api/connect")
def connect_to_google():
    # Read environment variables from Render
    GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID")
    GOOGLE_REDIRECT_URI = os.environ.get("GOOGLE_REDIRECT_URI")
    
    if not GOOGLE_CLIENT_ID or not GOOGLE_REDIRECT_URI:
        return {"error": "Google OAuth not configured. Please check environment variables."}
    
    # Build Google OAuth URL
    oauth_url = (
        f"https://accounts.google.com/o/oauth2/v2/auth"
        f"?client_id={GOOGLE_CLIENT_ID}"
        f"&redirect_uri={GOOGLE_REDIRECT_URI}"
        f"&response_type=code"
        f"&scope=https://www.googleapis.com/auth/webmasters.readonly"
    )
    
    return {"oauth_url": oauth_url}

@app.get("/api/connect/callback")
def oauth_callback(code: str):
    # For now, just return the code received from Google
    return {"code_received": code}
