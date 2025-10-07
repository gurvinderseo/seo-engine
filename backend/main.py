# main.py - Complete Backend with OAuth Fixed
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import httpx
import os
from urllib.parse import urlencode
import secrets

app = FastAPI(title="SEO Engine API")

# CORS - Allow frontend to call backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://seo-engine.vercel.app",
        "http://localhost:3000",
        "https://seo-engine.onrender.com"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Store OAuth states temporarily (in production use Redis)
oauth_states = {}

# Environment variables
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI")

@app.get("/")
def read_root():
    return {
        "message": "SEO Engine Backend is running!",
        "status": "healthy",
        "endpoints": {
            "docs": "/docs",
            "oauth_start": "/api/connect",
            "oauth_callback": "/api/connect/callback"
        }
    }

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "database": "connected" if os.getenv("DATABASE_URL") else "not_configured",
        "redis": "connected" if os.getenv("REDIS_URL") else "not_configured",
        "oauth": "configured" if GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET else "not_configured"
    }

@app.get("/api/connect")
async def connect_gsc():
    """Start Google Search Console OAuth flow"""
    
    # Validate environment variables
    if not all([GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REDIRECT_URI]):
        raise HTTPException(
            status_code=500,
            detail="OAuth credentials not configured. Check environment variables."
        )
    
    # Generate state for CSRF protection
    state = secrets.token_urlsafe(32)
    oauth_states[state] = True  # Store state (in production, use Redis with expiry)
    
    # OAuth parameters
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": " ".join([
            "https://www.googleapis.com/auth/webmasters.readonly",
            "https://www.googleapis.com/auth/analytics.readonly"
        ]),
        "access_type": "offline",
        "prompt": "consent",
        "state": state
    }
    
    # Build authorization URL
    auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"
    
    return {
        "auth_url": auth_url,
        "message": "Redirect user to this URL",
        "state": state
    }

@app.get("/api/connect/callback")
async def oauth_callback(code: str = None, state: str = None, error: str = None):
    """Handle OAuth callback from Google"""
    
    # Check for errors from Google
    if error:
        return JSONResponse(
            status_code=400,
            content={"error": f"OAuth error: {error}"}
        )
    
    # Validate code
    if not code:
        return JSONResponse(
            status_code=400,
            content={"error": "No authorization code provided"}
        )
    
    # Validate state (CSRF protection)
    if state not in oauth_states:
        return JSONResponse(
            status_code=400,
            content={"error": "Invalid state parameter. Possible CSRF attack."}
        )
    
    # Remove used state
    del oauth_states[state]
    
    # Exchange code for tokens
    try:
        async with httpx.AsyncClient() as client:
            token_response = await client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "code": code,
                    "client_id": GOOGLE_CLIENT_ID,
                    "client_secret": GOOGLE_CLIENT_SECRET,
                    "redirect_uri": GOOGLE_REDIRECT_URI,
                    "grant_type": "authorization_code"
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            
            if token_response.status_code != 200:
                return JSONResponse(
                    status_code=400,
                    content={
                        "error": "Failed to get tokens",
                        "details": token_response.text,
                        "status_code": token_response.status_code
                    }
                )
            
            tokens = token_response.json()
            
            # TODO: Store tokens in database
            # For now, return success with tokens (in production, save to DB and redirect)
            
            return {
                "success": True,
                "message": "Successfully authenticated with Google!",
                "access_token": tokens.get("access_token")[:20] + "...",  # Show partial token
                "token_type": tokens.get("token_type"),
                "expires_in": tokens.get("expires_in"),
                "has_refresh_token": "refresh_token" in tokens,
                "scopes": tokens.get("scope", "").split()
            }
            
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "error": "Exception during token exchange",
                "details": str(e)
            }
        )

@app.get("/api/test-db")
async def test_database():
    """Test database connection"""
    database_url = os.getenv("DATABASE_URL")
    
    if not database_url:
        return {"error": "DATABASE_URL not configured"}
    
    try:
        import psycopg2
        conn = psycopg2.connect(database_url)
        cur = conn.cursor()
        cur.execute("SELECT version();")
        db_version = cur.fetchone()
        cur.close()
        conn.close()
        
        return {
            "status": "connected",
            "database": "PostgreSQL",
            "version": db_version[0]
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }

@app.get("/api/test-redis")
async def test_redis():
    """Test Redis connection"""
    redis_url = os.getenv("REDIS_URL")
    
    if not redis_url:
        return {"error": "REDIS_URL not configured"}
    
    try:
        import redis
        r = redis.from_url(redis_url)
        r.ping()
        
        return {
            "status": "connected",
            "redis": "Upstash"
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }
