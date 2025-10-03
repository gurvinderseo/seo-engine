from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
import os
import requests

app = FastAPI()

# In-memory token storage (for testing)
tokens = {}

@app.get("/")
def read_root():
    return {"message": "SEO Engine Backend is running!"}

@app.get("/api/connect")
def connect_to_google():
    GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID")
    GOOGLE_REDIRECT_URI = os.environ.get("GOOGLE_REDIRECT_URI")
    
    if not GOOGLE_CLIENT_ID or not GOOGLE_REDIRECT_URI:
        return {"error": "Google OAuth not configured. Please check environment variables."}
    
    oauth_url = (
        f"https://accounts.google.com/o/oauth2/v2/auth"
        f"?client_id={GOOGLE_CLIENT_ID}"
        f"&redirect_uri={GOOGLE_REDIRECT_URI}"
        f"&response_type=code"
        f"&scope=https://www.googleapis.com/auth/webmasters.readonly"
        f"&access_type=offline"
        f"&prompt=consent"
    )
    
    return {"oauth_url": oauth_url}

@app.get("/api/connect/callback")
def oauth_callback(code: str):
    GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID")
    GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET")
    GOOGLE_REDIRECT_URI = os.environ.get("GOOGLE_REDIRECT_URI")
    
    # Exchange authorization code for access token
    token_url = "https://oauth2.googleapis.com/token"
    payload = {
        "code": code,
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "grant_type": "authorization_code"
    }
    
    response = requests.post(token_url, data=payload)
    token_data = response.json()
    
    # Store token in memory (for testing)
    tokens["google"] = token_data
    
    return {
        "message": "Google OAuth successful!",
        "token_data": token_data
    }

@app.get("/api/token")
def get_stored_token():
    # Returns the stored token for testing
    if "google" in tokens:
        return tokens["google"]
    return {"error": "No token stored yet. Complete OAuth first."}
