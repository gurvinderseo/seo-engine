from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import httpx
import os
from urllib.parse import urlencode
import secrets

app = FastAPI(title="SEO Engine API")

# CORS Configuration
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

# Temporary storage for OAuth states (use Redis in production)
oauth_states = {}

# Get environment variables
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI")
DATABASE_URL = os.getenv("DATABASE_URL")
REDIS_URL = os.getenv("REDIS_URL")

# Root endpoint
@app.get("/")
def read_root():
    return {
        "message": "SEO Engine Backend is running!",
        "status": "healthy",
        "version": "1.0.0",
        "endpoints": {
            "api_docs": "/docs",
            "health_check": "/health",
            "oauth_start": "/api/connect",
            "oauth_callback": "/api/connect/callback",
            "test_database": "/api/test-db",
            "test_redis": "/api/test-redis"
        }
    }

# Health check endpoint - CRITICAL
@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": "2024-01-15T10:00:00Z",
        "services": {
            "database": "connected" if DATABASE_URL else "not_configured",
            "redis": "connected" if REDIS_URL else "not_configured",
            "oauth": "configured" if GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET else "not_configured"
        },
        "environment": {
            "google_client_id": "configured" if GOOGLE_CLIENT_ID else "missing",
            "google_client_secret": "configured" if GOOGLE_CLIENT_SECRET else "missing",
            "redirect_uri": "configured" if GOOGLE_REDIRECT_URI else "missing",
            "database_url": "configured" if DATABASE_URL else "missing",
            "redis_url": "configured" if REDIS_URL else "missing",
            "secret_key": "configured" if os.getenv("SECRET_KEY") else "missing"
        }
    }

# Test database connection
@app.get("/api/test-db")
async def test_database():
    """Test PostgreSQL connection"""
    if not DATABASE_URL:
        return {"error": "DATABASE_URL not configured in environment variables"}
    
    try:
        import psycopg2
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        cur.execute("SELECT version();")
        db_version = cur.fetchone()
        cur.close()
        conn.close()
        
        return {
            "status": "connected",
            "database": "PostgreSQL",
            "version": db_version[0][:50] + "..."
        }
    except ImportError:
        return {
            "status": "error",
            "error": "psycopg2 not installed. Add 'psycopg2-binary' to requirements.txt"
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "hint": "Check DATABASE_URL format and Supabase credentials"
        }

# Test Redis connection
@app.get("/api/test-redis")
async def test_redis():
    """Test Redis connection"""
    if not REDIS_URL:
        return {"error": "REDIS_URL not configured in environment variables"}
    
    try:
        import redis
        r = redis.from_url(REDIS_URL)
        r.ping()
        r.set("test_key", "test_value", ex=10)
        value = r.get("test_key")
        
        return {
            "status": "connected",
            "redis": "Upstash",
            "test": "write and read successful",
            "value": value.decode() if value else None
        }
    except ImportError:
        return {
            "status": "error",
            "error": "redis not installed. Add 'redis' to requirements.txt"
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "hint": "Check REDIS_URL format and Upstash credentials"
        }

# Start OAuth flow
@app.get("/api/connect")
async def connect_gsc():
    """Start Google OAuth flow"""
    
    if not all([GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REDIRECT_URI]):
        missing = []
        if not GOOGLE_CLIENT_ID: missing.append("GOOGLE_CLIENT_ID")
        if not GOOGLE_CLIENT_SECRET: missing.append("GOOGLE_CLIENT_SECRET")
        if not GOOGLE_REDIRECT_URI: missing.append("GOOGLE_REDIRECT_URI")
        
        return JSONResponse(
            status_code=500,
            content={
                "error": "OAuth not configured",
                "missing_variables": missing,
                "hint": "Add these in Render Environment settings"
            }
        )
    
    # Generate state for CSRF protection
    state = secrets.token_urlsafe(32)
    oauth_states[state] = True
    
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
    
    auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"
    
    return {
        "oauth_url": auth_url,
        "state": state,
        "instructions": "Visit oauth_url in browser to authorize"
    }

# OAuth callback
@app.get("/api/connect/callback")
async def oauth_callback(code: str = None, state: str = None, error: str = None):
    """Handle OAuth callback from Google"""
    
    # Check for errors
    if error:
        return JSONResponse(
            status_code=400,
            content={"error": f"Google OAuth error: {error}"}
        )
    
    if not code:
        return JSONResponse(
            status_code=400,
            content={"error": "No authorization code received from Google"}
        )
    
    # Validate state (CSRF protection)
    if state and state not in oauth_states:
        return JSONResponse(
            status_code=400,
            content={
                "error": "Invalid state parameter",
                "hint": "Start OAuth flow again from /api/connect"
            }
        )
    
    # Remove used state
    if state in oauth_states:
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
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=30.0
            )
            
            if token_response.status_code != 200:
                return JSONResponse(
                    status_code=token_response.status_code,
                    content={
                        "error": "Token exchange failed",
                        "status_code": token_response.status_code,
                        "details": token_response.text,
                        "hint": "Check GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in Render"
                    }
                )
            
            tokens = token_response.json()
            
            # SUCCESS! Return tokens (in production, save to database)
            return {
                "success": True,
                "message": "✅ Successfully authenticated with Google!",
                "token_info": {
                    "access_token": tokens.get("access_token")[:20] + "..." if tokens.get("access_token") else None,
                    "token_type": tokens.get("token_type"),
                    "expires_in": tokens.get("expires_in"),
                    "has_refresh_token": "refresh_token" in tokens,
                    "scopes": tokens.get("scope", "").split()
                },
                "next_steps": [
                    "Store tokens in database",
                    "Use access_token to call GSC/GA4 APIs",
                    "Implement token refresh logic"
                ]
            }
            
    except httpx.TimeoutException:
        return JSONResponse(
            status_code=504,
            content={
                "error": "Request to Google timed out",
                "hint": "Try again in a few seconds"
            }
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "error": "Exception during token exchange",
                "details": str(e),
                "type": type(e).__name__
            }
        )

# Run with: uvicorn main:app --host 0.0.0.0 --port $PORT
