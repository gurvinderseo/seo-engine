from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import httpx
import os
from urllib.parse import urlencode, quote_plus
import secrets

app = FastAPI(title="SEO Engine API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://seo-engine-gold.vercel.app",
        "http://localhost:3000",
        "https://seo-engine.onrender.com"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

oauth_states = {}

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI")
DATABASE_URL = os.getenv("DATABASE_URL")
REDIS_URL = os.getenv("REDIS_URL")

@app.get("/")
def read_root():
    return {"message": "SEO Engine Backend is running!", "status": "healthy", "version": "1.0.0"}

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "services": {
            "database": "connected" if DATABASE_URL else "not_configured",
            "redis": "connected" if REDIS_URL else "not_configured",
            "oauth": "configured" if GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET else "not_configured"
        }
    }

@app.get("/api/test-db")
async def test_database():
    if not DATABASE_URL:
        return {"error": "DATABASE_URL not configured"}
    try:
        import psycopg2
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        cur.execute("SELECT version();")
        db_version = cur.fetchone()
        cur.close()
        conn.close()
        return {"status": "connected", "database": "PostgreSQL"}
    except Exception as e:
        return {"status": "error", "error": str(e)}

@app.get("/api/connect")
async def connect_gsc():
    if not all([GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REDIRECT_URI]):
        return JSONResponse(status_code=500, content={"error": "OAuth not configured"})
    
    state = secrets.token_urlsafe(32)
    oauth_states[state] = True
    
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": " ".join([
            "https://www.googleapis.com/auth/webmasters.readonly",
            "https://www.googleapis.com/auth/analytics.readonly",
            "openid",
            "email",
            "profile"
        ]),
        "access_type": "offline",
        "prompt": "consent",
        "state": state
    }
    
    auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"
    return {"oauth_url": auth_url, "state": state}

@app.get("/api/connect/callback")
async def oauth_callback(code: str = None, state: str = None, error: str = None):
    if error:
        return RedirectResponse(url=f"https://seo-engine-gold.vercel.app/?oauth_error={error}")
    
    if not code:
        return RedirectResponse(url="https://seo-engine-gold.vercel.app/?oauth_error=no_code")
    
    if state and state not in oauth_states:
        return RedirectResponse(url="https://seo-engine-gold.vercel.app/?oauth_error=invalid_state")
    
    if state in oauth_states:
        del oauth_states[state]
    
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
                return RedirectResponse(url="https://seo-engine-gold.vercel.app/?oauth_error=token_failed")
            
            tokens = token_response.json()
            
            if DATABASE_URL:
                try:
                    import psycopg2
                    from psycopg2.extras import Json
                    
                    conn = psycopg2.connect(DATABASE_URL)
                    cur = conn.cursor()
                    
                    cur.execute("""
                        INSERT INTO connectors (site_id, type, credentials_meta, status)
                        VALUES (%s, %s, %s, %s)
                        RETURNING id
                    """, (
                        None,
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
                    
                    return RedirectResponse(url=f"https://seo-engine-gold.vercel.app/?oauth_success=true&connector_id={connector_id}")
                    
                except Exception as db_error:
                    print(f"Database error: {db_error}")
                    return RedirectResponse(url="https://seo-engine-gold.vercel.app/?oauth_success=true&db_warning=true")
            else:
                return RedirectResponse(url="https://seo-engine-gold.vercel.app/?oauth_success=true")
            
    except Exception as e:
        print(f"OAuth error: {e}")
        return RedirectResponse(url="https://seo-engine-gold.vercel.app/?oauth_error=exception")

@app.post("/api/sites")
async def create_site(site_data: dict):
    if not DATABASE_URL:
        return {"error": "Database not configured"}
    
    try:
        import psycopg2
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        
        cur.execute("""
            INSERT INTO sites (owner_id, domain, sitemap_url, created_at)
            VALUES (%s, %s, %s, NOW())
            RETURNING id, domain, sitemap_url, created_at
        """, (1, site_data.get('domain'), site_data.get('sitemap_url')))
        
        site = cur.fetchone()
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
    if not DATABASE_URL:
        return {"sites": []}
    
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
        return {"sites": [], "error": str(e)}

@app.delete("/api/sites/{site_id}")
async def delete_site(site_id: int):
    if not DATABASE_URL:
        return {"error": "Database not configured"}
    
    try:
        import psycopg2
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        
        cur.execute("DELETE FROM gsc_metrics WHERE site_id = %s", (site_id,))
        cur.execute("DELETE FROM ga4_metrics WHERE site_id = %s", (site_id,))
        cur.execute("DELETE FROM issues WHERE site_id = %s", (site_id,))
        cur.execute("DELETE FROM sites WHERE id = %s", (site_id,))
        
        conn.commit()
        cur.close()
        conn.close()
        
        return {"success": True, "message": "Site deleted successfully"}
    except Exception as e:
        return {"error": str(e)}

@app.post("/api/fetch-gsc-data")
async def fetch_gsc_data(request_data: dict):
    site_id = request_data.get('site_id')
    
    if not DATABASE_URL:
        return {"error": "Database not configured"}
    
    try:
        import psycopg2
        from psycopg2.extras import Json
        from datetime import datetime, timedelta
        
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        
        cur.execute("SELECT domain FROM sites WHERE id = %s", (site_id,))
        site = cur.fetchone()
        
        if not site:
            cur.close()
            conn.close()
            return {"error": "Site not found"}
        
        domain = site[0]
        
        cur.execute("""
            SELECT credentials_meta 
            FROM connectors 
            WHERE type = 'gsc' AND status = 'active'
            ORDER BY created_at DESC
            LIMIT 1
        """)
        
        connector = cur.fetchone()
        
        if not connector:
            cur.close()
            conn.close()
            return {
                "error": "No GSC connector found",
                "solution": "Click 'Connect Google Account' button first."
            }
        
        credentials = connector[0]
        access_token = credentials.get('access_token')
        
        if not access_token:
            cur.close()
            conn.close()
            return {
                "error": "No access token",
                "solution": "Reconnect your Google account."
            }
        
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=90)
        
        # Try URL prefix formats (for verified properties like https://example.com)
        url_formats = [domain]  # Use exact domain as entered
        
        if not domain.startswith('http'):
            # If user entered "example.com", try both https and http
            url_formats = [
                f"https://{domain}",
                f"http://{domain}"
            ]
        
        last_error = None
        
        async with httpx.AsyncClient() as client:
            for attempt_url in url_formats:
                try:
                    encoded_site_url = quote_plus(attempt_url)
                    gsc_api_url = f"https://searchconsole.googleapis.com/webmasters/v3/sites/{encoded_site_url}/searchAnalytics/query"
                    
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
                    
                    if response.status_code == 200:
                        gsc_data = response.json()
                        rows = gsc_data.get('rows', [])
                        
                        if len(rows) == 0:
                            cur.close()
                            conn.close()
                            return {
                                "success": True,
                                "rows_imported": 0,
                                "message": f"No data found for {attempt_url}. Site may not have search traffic yet."
                            }
                        
                        for row in rows:
                            keys = row.get('keys', [])
                            page_url = keys[0] if len(keys) > 0 else None
                            query = keys[1] if len(keys) > 1 else None
                            
                            cur.execute("""
                                INSERT INTO gsc_metrics 
                                (site_id, url, query, impressions, clicks, ctr, position, date)
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                                ON CONFLICT DO NOTHING
                            """, (
                                site_id,
                                page_url,
                                query,
                                row.get('impressions', 0),
                                row.get('clicks', 0),
                                row.get('ctr', 0.0),
                                row.get('position', 0.0),
                                datetime.now()
                            ))
                        
                        conn.commit()
                        cur.execute("UPDATE sites SET last_scan_at = NOW() WHERE id = %s", (site_id,))
                        conn.commit()
                        
                        run_diagnostics(site_id, cur)
                        conn.commit()
                        
                        cur.close()
                        conn.close()
                        
                        return {
                            "success": True,
                            "rows_imported": len(rows),
                            "message": f"✅ Successfully imported {len(rows)} rows from GSC"
                        }
                    else:
                        last_error = {"url": attempt_url, "status": response.status_code, "details": response.text}
                        
                except Exception as e:
                    last_error = {"url": attempt_url, "error": str(e)}
                    continue
        
        cur.close()
        conn.close()
        
        if last_error:
            status_code = last_error.get('status', 0)
            
            if status_code == 403:
                return {
                    "error": "Permission denied (403)",
                    "solution": f"""This Google account doesn't have access to {domain} in GSC.

Fix:
1. Go to: https://search.google.com/search-console
2. Click on {domain} property
3. Settings → Users → Add your Google account as Owner

Tried: {', '.join(url_formats)}"""
                }
            elif status_code == 404:
                return {
                    "error": "Property not found (404)",
                    "solution": f"""Property {domain} not found.

Make sure you enter the EXACT URL from GSC:
- If GSC shows "https://example.com" → enter "https://example.com"
- If GSC shows "https://www.example.com" → enter "https://www.example.com"

Tried: {', '.join(url_formats)}"""
                }
            else:
                return {
                    "error": f"Failed (Status: {status_code})",
                    "solution": f"""Error: {last_error.get('error', last_error.get('details', 'Unknown'))}

Try:
1. Reconnect Google account
2. Check domain format matches GSC exactly

Tried: {', '.join(url_formats)}"""
                }
        
        return {"error": "Failed to fetch", "solution": "Try reconnecting Google account"}
        
    except Exception as e:
        return {"error": str(e), "solution": "Server error. Try again."}

@app.get("/api/gsc-data/{site_id}")
async def get_gsc_data(site_id: int):
    if not DATABASE_URL:
        return {"error": "Database not configured"}
    
    try:
        import psycopg2
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        
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
        return {"error": str(e), "pages": [], "count": 0}

@app.get("/api/export-gsc-data/{site_id}")
async def export_gsc_data(site_id: int):
    if not DATABASE_URL:
        return {"error": "Database not configured"}
    
    try:
        import psycopg2
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        
        cur.execute("""
            SELECT url, query, impressions, clicks, ctr, position, date
            FROM gsc_metrics
            WHERE site_id = %s
            ORDER BY impressions DESC
        """, (site_id,))
        
        rows = cur.fetchall()
        cur.close()
        conn.close()
        
        csv_data = "URL,Query,Impressions,Clicks,CTR,Position,Date\n"
        for row in rows:
            csv_data += f'"{row[0]}","{row[1]}",{row[2]},{row[3]},{row[4]},{row[5]},"{row[6]}"\n'
        
        return {"success": True, "csv_data": csv_data, "rows_count": len(rows)}
    except Exception as e:
        return {"error": str(e)}

def run_diagnostics(site_id: int, cur):
    try:
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
        """, (site_id,))
        
        pages = cur.fetchall()
        
        for page in pages:
            url, impressions, clicks, ctr, position = page
            
            if impressions >= 100 and ctr < 0.02 and 3 <= position <= 15:
                cur.execute("""
                    INSERT INTO issues (site_id, issue_type, severity, description, suggested_action, status)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT DO NOTHING
                """, (
                    site_id,
                    'low_ctr',
                    'high',
                    f'Page "{url}" has low CTR ({ctr*100:.2f}%) despite good position ({position:.1f}).',
                    f'🔧 Optimize meta title and description. Current CTR is {(ctr*100):.1f}% but should be 5%+. Add power words like "Best", "Guide", "2024".'
                ))
            
            if impressions >= 500 and clicks == 0:
                cur.execute("""
                    INSERT INTO issues (site_id, issue_type, severity, description, suggested_action, status)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT DO NOTHING
                """, (
                    site_id,
                    'zero_clicks',
                    'critical',
                    f'Page "{url}" has {impressions} impressions but ZERO clicks!',
                    f'🚨 CRITICAL: Page showing in search but nobody clicking. Check title relevance and meta description.'
                ))
            
            if impressions >= 50 and position > 20:
                cur.execute("""
                    INSERT INTO issues (site_id, issue_type, severity, description, suggested_action, status)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT DO NOTHING
                """, (
                    site_id,
                    'poor_ranking',
                    'medium',
                    f'Page "{url}" ranks at position {position:.1f} (page 3+)',
                    f'💡 Add more content (1500+ words), get backlinks, improve internal linking, add FAQ schema.'
                ))
        
    except Exception as e:
        print(f"Diagnostics error: {e}")

@app.get("/api/issues/{site_id}")
async def get_issues(site_id: int):
    if not DATABASE_URL:
        return {"issues": []}
    
    try:
        import psycopg2
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        
        cur.execute("""
            SELECT id, issue_type, severity, description, suggested_action, status, created_at
            FROM issues
            WHERE site_id = %s
            ORDER BY 
                CASE severity
                    WHEN 'critical' THEN 1
                    WHEN 'high' THEN 2
                    WHEN 'medium' THEN 3
                    ELSE 4
                END,
                created_at DESC
        """, (site_id,))
        
        issues = []
        for row in cur.fetchall():
            issues.append({
                "id": row[0],
                "type": row[1],
                "severity": row[2],
                "description": row[3],
                "suggestion": row[4],
                "status": row[5],
                "created_at": row[6].isoformat() if row[6] else None
            })
        
        cur.close()
        conn.close()
        
        return {"issues": issues, "count": len(issues)}
    except Exception as e:
        return {"issues": [], "error": str(e)}
