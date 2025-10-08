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
        "https://seo-engine-gold.vercel.app",  # ✅ Add your actual frontend
        "http://localhost:3000",               # local dev
        "https://seo-engine.onrender.com"      # backend can call itself if needed
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
# OAuth callback - UPDATED VERSION
@app.get("/api/connect/callback")
async def oauth_callback(code: str = None, state: str = None, error: str = None):
    """Handle OAuth callback from Google"""
    
    if error:
        # Redirect to frontend with error
        return RedirectResponse(
            url=f"https://seo-engine-gold.vercel.app/?oauth_error={error}"
        )
    
    if not code:
        return RedirectResponse(
            url="https://seo-engine-gold.vercel.app/?oauth_error=no_code"
        )
    
    # Validate state
    if state and state not in oauth_states:
        return RedirectResponse(
            url="https://seo-engine-gold.vercel.app/?oauth_error=invalid_state"
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
                return RedirectResponse(
                    url=f"https://seo-engine-gold.vercel.app/?oauth_error=token_exchange_failed"
                )
            
            tokens = token_response.json()
            
            # Store tokens in database
            if DATABASE_URL:
                try:
                    import psycopg2
                    from psycopg2.extras import Json
                    
                    conn = psycopg2.connect(DATABASE_URL)
                    cur = conn.cursor()
                    
                    # Store in connectors table
                    cur.execute("""
                        INSERT INTO connectors (site_id, type, credentials_meta, status)
                        VALUES (%s, %s, %s, %s)
                        RETURNING id
                    """, (
                        None,  # site_id will be set later when user adds site
                        'gsc',
                        Json({
                            'access_token': tokens.get('access_token'),
                            'refresh_token': tokens.get('refresh_token'),
                            'token_expiry': tokens.get('expires_in'),
                            'scopes': tokens.get('scope', '').split()
                        }),
                        'active'
                    ))
                    
                    connector_id = cur.fetchone()[0]
                    conn.commit()
                    cur.close()
                    conn.close()
                    
                    # Success! Redirect to frontend with success flag
                    return RedirectResponse(
                        url=f"https://seo-engine-gold.vercel.app/?oauth_success=true&connector_id={connector_id}"
                    )
                    
                except Exception as db_error:
                    print(f"Database error: {db_error}")
                    # Still redirect with success but note DB issue
                    return RedirectResponse(
                        url=f"https://seo-engine-gold.vercel.app/?oauth_success=true&db_warning=true"
                    )
            else:
                # No database configured, but OAuth worked
                return RedirectResponse(
                    url="https://seo-engine-gold.vercel.app/?oauth_success=true&no_db=true"
                )
            
    except Exception as e:
        return RedirectResponse(
            url=f"https://seo-engine-gold.vercel.app/?oauth_error=exception"
        )

# Run with: uvicorn main:app --host 0.0.0.0 --port $PORT
# ==================== SITES MANAGEMENT ====================

@app.post("/api/sites")
async def create_site(site_data: dict):
    """Create a new site"""
    if not DATABASE_URL:
        return {"error": "Database not configured"}
    
    try:
        import psycopg2
        
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        
        # Insert site (owner_id = 1 for now, will add proper auth later)
        # Store tokens in connectors table (upsert)
cur.execute("""
    INSERT INTO connectors (site_id, type, credentials_meta, status)
    VALUES (%s, %s, %s, %s)
    ON CONFLICT (type) 
    DO UPDATE SET 
        credentials_meta = EXCLUDED.credentials_meta,
        status = EXCLUDED.status,
        updated_at = NOW()
    RETURNING id
""", (
    None,  # site_id will be set later when user adds site
    'gsc',
    Json({
        'access_token': tokens.get('access_token'),
        'refresh_token': tokens.get('refresh_token'),  # sometimes may be None
        'token_expiry': tokens.get('expires_in'),
        'scopes': tokens.get('scope', '').split()
    }),
    'active'
))

connector_id = cur.fetchone()[0]
conn.commit()
cur.close()
conn.close()

        
        return {
            "success": True,
            "site": {
                "id": site[0],
                "domain": site[1],
                "sitemap_url": site[2],
                "created_at": site[3].isoformat()
            }
        }
        
    except Exception as e:
        return {"error": str(e)}

@app.get("/api/sites")
async def get_sites():
    """Get all sites"""
    if not DATABASE_URL:
        return {"error": "Database not configured"}
    
    try:
        import psycopg2
        
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        
        cur.execute("""
            SELECT id, domain, sitemap_url, created_at, last_scan_at
            FROM sites
            ORDER BY created_at DESC
        """)
        
        sites = []
        for row in cur.fetchall():
            sites.append({
                "id": row[0],
                "domain": row[1],
                "sitemap_url": row[2],
                "created_at": row[3].isoformat() if row[3] else None,
                "last_scan_at": row[4].isoformat() if row[4] else None
            })
        
        cur.close()
        conn.close()
        
        return {"sites": sites}
        
    except Exception as e:
        return {"error": str(e)}

# ==================== GSC DATA FETCHING ====================

@app.post("/api/fetch-gsc-data")
async def fetch_gsc_data(request_data: dict):
    """Fetch GSC data for a site"""
    site_id = request_data.get('site_id')
    
    if not DATABASE_URL:
        return {"error": "Database not configured"}
    
    try:
        import psycopg2
        from psycopg2.extras import Json
        from datetime import datetime, timedelta
        
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        
        # Get site details
        cur.execute("SELECT domain FROM sites WHERE id = %s", (site_id,))
        site = cur.fetchone()
        
        if not site:
            return {"error": "Site not found"}
        
        domain = site[0]
        
        # Get OAuth credentials
        cur.execute("""
            SELECT credentials_meta 
            FROM connectors 
            WHERE type = 'gsc' AND status = 'active'
            ORDER BY created_at DESC
            LIMIT 1
        """)
        
        connector = cur.fetchone()
        
        if not connector:
            return {"error": "No GSC connector found. Please connect Google account first."}
        
        credentials = connector[0]
        access_token = credentials.get('access_token')
        
        if not access_token:
            return {"error": "No access token found"}
        
        # Fetch data from GSC API
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=90)
        
        gsc_api_url = f"https://www.googleapis.com/webmasters/v3/sites/{domain}/searchAnalytics/query"
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                gsc_api_url,
                json={
                    "startDate": start_date.isoformat(),
                    "endDate": end_date.isoformat(),
                    "dimensions": ["page", "query"],
                    "rowLimit": 1000
                },
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json"
                },
                timeout=30.0
            )
            
            if response.status_code != 200:
                return {
                    "error": "Failed to fetch GSC data",
                    "details": response.text,
                    "status_code": response.status_code
                }
            
            gsc_data = response.json()
            rows = gsc_data.get('rows', [])
            
            # Store in database
            for row in rows:
                keys = row.get('keys', [])
                page_url = keys[0] if len(keys) > 0 else None
                query = keys[1] if len(keys) > 1 else None
                
                impressions = row.get('impressions', 0)
                clicks = row.get('clicks', 0)
                ctr = row.get('ctr', 0.0)
                position = row.get('position', 0.0)
                
                cur.execute("""
                    INSERT INTO gsc_metrics 
                    (site_id, url, query, impressions, clicks, ctr, position, date)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT DO NOTHING
                """, (
                    site_id,
                    page_url,
                    query,
                    impressions,
                    clicks,
                    ctr,
                    position,
                    datetime.now()
                ))
            
            conn.commit()
            
            # Update last_scan_at
            cur.execute("""
                UPDATE sites 
                SET last_scan_at = NOW()
                WHERE id = %s
            """, (site_id,))
            
            conn.commit()
            cur.close()
            conn.close()
            
            return {
                "success": True,
                "rows_imported": len(rows),
                "message": f"Successfully imported {len(rows)} rows from GSC"
            }
            
    except Exception as e:
        return {"error": str(e)}

# ==================== GET GSC DATA ====================

@app.get("/api/gsc-data/{site_id}")
async def get_gsc_data(site_id: int):
    """Get GSC data for a site"""
    if not DATABASE_URL:
        return {"error": "Database not configured"}
    
    try:
        import psycopg2
        
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        
        # Get aggregated data
        cur.execute("""
            SELECT 
                url,
                SUM(impressions) as total_impressions,
                SUM(clicks) as total_clicks,
                AVG(ctr) as avg_ctr,
                AVG(position) as avg_position
            FROM gsc_metrics
            WHERE site_id = %s
            GROUP BY url
            ORDER BY total_impressions DESC
            LIMIT 100
        """, (site_id,))
        
        pages = []
        for row in cur.fetchall():
            pages.append({
                "url": row[0],
                "impressions": int(row[1] or 0),
                "clicks": int(row[2] or 0),
                "ctr": float(row[3] or 0),
                "position": float(row[4] or 0)
            })
        
        cur.close()
        conn.close()
        
        return {"pages": pages, "count": len(pages)}
        
    except Exception as e:
        return {"error": str(e)}
