from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse, JSONResponse
import os
import requests
import psycopg2
from urllib.parse import urlencode
from datetime import datetime, timedelta

app = FastAPI()

# Environment variables
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET")
GOOGLE_REDIRECT_URI = os.environ.get("GOOGLE_REDIRECT_URI")
DATABASE_URL = os.environ.get("DATABASE_URL")

# Connect to Postgres
def get_db_connection():
    conn = psycopg2.connect(DATABASE_URL)
    return conn

@app.get("/")
def read_root():
    return {"message": "SEO Engine Backend is running!"}

@app.get("/api/connect")
def connect_to_google():
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": "https://www.googleapis.com/auth/webmasters.readonly",
        "access_type": "offline",  # This is required to get a refresh token
        "prompt": "consent"
    }
    oauth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"
    return {"oauth_url": oauth_url}

@app.get("/api/connect/callback")
def oauth_callback(code: str, email: str = "admin@seoengine.com"):
    """
    code: OAuth code from Google
    email: Your user email in `users` table (change dynamically if needed)
    """
    # Exchange code for tokens
    token_url = "https://oauth2.googleapis.com/token"
    data = {
        "code": code,
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "grant_type": "authorization_code"
    }
    response = requests.post(token_url, data=data)
    if response.status_code != 200:
        return JSONResponse({"error": "Failed to get tokens", "details": response.text}, status_code=400)

    token_data = response.json()
    access_token = token_data.get("access_token")
    refresh_token = token_data.get("refresh_token")
    expires_in = token_data.get("expires_in")  # seconds
    expiry_time = datetime.utcnow() + timedelta(seconds=expires_in)

    # Save tokens in database for the user
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE users
            SET google_access_token = %s,
                google_refresh_token = %s,
                google_token_expiry = %s
            WHERE email = %s
            """,
            (access_token, refresh_token, expiry_time, email)
        )
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        return JSONResponse({"error": "Database error", "details": str(e)}, status_code=500)

    return {"message": "Google OAuth successful!", "token_data": token_data}
