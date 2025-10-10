from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import httpx
import os
from urllib.parse import urlencode, quote_plus
import secrets
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
import json

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
HUGGINGFACE_API_TOKEN = os.getenv("HUGGINGFACE_API_TOKEN")
SERPER_API_KEY = os.getenv("SERPER_API_KEY")

@app.get("/")
def read_root():
    return {"message": "SEO Engine Backend is running!", "status": "healthy", "version": "2.0.0"}

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "services": {
            "database": "connected" if DATABASE_URL else "not_configured",
            "redis": "connected" if REDIS_URL else "not_configured",
            "oauth": "configured" if GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET else "not_configured",
            "ai": "configured" if HUGGINGFACE_API_TOKEN else "not_configured",
            "serper": "configured" if SERPER_API_KEY else "not_configured"
        }
    }

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
                        ON CONFLICT (type) DO UPDATE SET 
                            credentials_meta = EXCLUDED.credentials_meta,
                            status = EXCLUDED.status
                        RETURNING id
                    """, (
                        None,
                        'google',
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
    days = request_data.get('days', 90)
    
    if not DATABASE_URL:
        return {"error": "Database not configured"}
    
    try:
        import psycopg2
        from psycopg2.extras import Json
        
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
            WHERE type = 'google' AND status = 'active'
            ORDER BY created_at DESC
            LIMIT 1
        """)
        
        connector = cur.fetchone()
        
        if not connector:
            cur.close()
            conn.close()
            return {
                "error": "No Google connector found",
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
        start_date = end_date - timedelta(days=days)
        
        url_formats = [domain]
        if not domain.startswith('http'):
            url_formats = [f"https://{domain}", f"http://{domain}"]
        
        last_error = None
        
        async with httpx.AsyncClient() as client:
            for attempt_url in url_formats:
                try:
                    encoded_site_url = quote_plus(attempt_url)
                    gsc_api_url = f"https://searchconsole.googleapis.com/webmasters/v3/sites/{encoded_site_url}/searchAnalytics/query"
                    
                    # Fetch with all dimensions
                    response = await client.post(
                        gsc_api_url,
                        json={
                            "startDate": start_date.isoformat(),
                            "endDate": end_date.isoformat(),
                            "dimensions": ["page", "query", "country", "device", "date"],
                            "rowLimit": 25000
                        },
                        headers={
                            "Authorization": f"Bearer {access_token}",
                            "Content-Type": "application/json"
                        },
                        timeout=60.0
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
                                "message": f"No data found for {attempt_url}. Site may not have search traffic yet.",
                                "date_range": f"{start_date} to {end_date}"
                            }
                        
                        # Clear old data for this date range
                        cur.execute("""
                            DELETE FROM gsc_metrics 
                            WHERE site_id = %s AND date >= %s AND date <= %s
                        """, (site_id, start_date, end_date))
                        
                        for row in rows:
                            keys = row.get('keys', [])
                            page_url = keys[0] if len(keys) > 0 else None
                            query = keys[1] if len(keys) > 1 else None
                            country = keys[2] if len(keys) > 2 else None
                            device = keys[3] if len(keys) > 3 else None
                            date = keys[4] if len(keys) > 4 else None
                            
                            cur.execute("""
                                INSERT INTO gsc_metrics 
                                (site_id, url, query, country, device, impressions, clicks, ctr, position, date)
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                                ON CONFLICT DO NOTHING
                            """, (
                                site_id,
                                page_url,
                                query,
                                country,
                                device,
                                row.get('impressions', 0),
                                row.get('clicks', 0),
                                row.get('ctr', 0.0),
                                row.get('position', 0.0),
                                date or datetime.now().date()
                            ))
                        
                        conn.commit()
                        cur.execute("UPDATE sites SET last_scan_at = NOW() WHERE id = %s", (site_id,))
                        conn.commit()
                        
                        cur.close()
                        conn.close()
                        
                        return {
                            "success": True,
                            "rows_imported": len(rows),
                            "message": f"✅ Successfully imported {len(rows)} rows from GSC",
                            "date_range": f"{start_date} to {end_date}",
                            "days": days
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

@app.post("/api/fetch-ga4-data")
async def fetch_ga4_data(request_data: dict):
    """Fetch GA4 data for cross-analysis"""
    site_id = request_data.get('site_id')
    property_id = request_data.get('property_id')  # GA4 Property ID
    days = request_data.get('days', 90)
    
    if not DATABASE_URL:
        return {"error": "Database not configured"}
    
    try:
        import psycopg2
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        
        cur.execute("""
            SELECT credentials_meta 
            FROM connectors 
            WHERE type = 'google' AND status = 'active'
            ORDER BY created_at DESC
            LIMIT 1
        """)
        
        connector = cur.fetchone()
        
        if not connector:
            cur.close()
            conn.close()
            return {"error": "No Google connector found"}
        
        credentials = connector[0]
        access_token = credentials.get('access_token')
        
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days)
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"https://analyticsdata.googleapis.com/v1beta/properties/{property_id}:runReport",
                json={
                    "dateRanges": [{"startDate": start_date.isoformat(), "endDate": end_date.isoformat()}],
                    "dimensions": [
                        {"name": "pagePath"},
                        {"name": "date"},
                        {"name": "country"},
                        {"name": "deviceCategory"}
                    ],
                    "metrics": [
                        {"name": "sessions"},
                        {"name": "totalUsers"},
                        {"name": "screenPageViews"},
                        {"name": "averageSessionDuration"},
                        {"name": "bounceRate"},
                        {"name": "conversions"}
                    ],
                    "limit": 25000
                },
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json"
                },
                timeout=60.0
            )
            
            if response.status_code == 200:
                ga4_data = response.json()
                rows = ga4_data.get('rows', [])
                
                # Clear old GA4 data
                cur.execute("""
                    DELETE FROM ga4_metrics 
                    WHERE site_id = %s AND date >= %s AND date <= %s
                """, (site_id, start_date, end_date))
                
                for row in rows:
                    dimensions = row.get('dimensionValues', [])
                    metrics = row.get('metricValues', [])
                    
                    if len(dimensions) >= 4 and len(metrics) >= 6:
                        cur.execute("""
                            INSERT INTO ga4_metrics 
                            (site_id, page_path, date, country, device, sessions, users, pageviews, 
                             avg_session_duration, bounce_rate, conversions)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            ON CONFLICT DO NOTHING
                        """, (
                            site_id,
                            dimensions[0].get('value'),
                            dimensions[1].get('value'),
                            dimensions[2].get('value'),
                            dimensions[3].get('value'),
                            int(metrics[0].get('value', 0)),
                            int(metrics[1].get('value', 0)),
                            int(metrics[2].get('value', 0)),
                            float(metrics[3].get('value', 0)),
                            float(metrics[4].get('value', 0)),
                            float(metrics[5].get('value', 0))
                        ))
                
                conn.commit()
                cur.close()
                conn.close()
                
                return {
                    "success": True,
                    "rows_imported": len(rows),
                    "message": f"✅ Successfully imported {len(rows)} rows from GA4",
                    "date_range": f"{start_date} to {end_date}"
                }
            else:
                return {"error": f"GA4 API failed: {response.status_code}", "details": response.text}
                
    except Exception as e:
        return {"error": str(e)}

@app.get("/api/gsc-data/{site_id}")
async def get_gsc_data(site_id: int, page: int = 1, per_page: int = 50, 
                       filter_device: str = None, filter_country: str = None,
                       start_date: str = None, end_date: str = None):
    if not DATABASE_URL:
        return {"error": "Database not configured"}
    
    try:
        import psycopg2
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        
        # Build dynamic query
        query = """
            SELECT 
                url,
                query,
                country,
                device,
                SUM(impressions) as total_impressions,
                SUM(clicks) as total_clicks,
                AVG(ctr) as avg_ctr,
                AVG(position) as avg_position,
                date
            FROM gsc_metrics
            WHERE site_id = %s
        """
        params = [site_id]
        
        if filter_device:
            query += " AND device = %s"
            params.append(filter_device)
        
        if filter_country:
            query += " AND country = %s"
            params.append(filter_country)
        
        if start_date:
            query += " AND date >= %s"
            params.append(start_date)
        
        if end_date:
            query += " AND date <= %s"
            params.append(end_date)
        
        query += """
            GROUP BY url, query, country, device, date
            ORDER BY total_impressions DESC
            LIMIT %s OFFSET %s
        """
        params.extend([per_page, (page - 1) * per_page])
        
        cur.execute(query, tuple(params))
        
        pages = []
        for row in cur.fetchall():
            pages.append({
                "url": row[0],
                "query": row[1],
                "country": row[2],
                "device": row[3],
                "impressions": int(row[4] or 0),
                "clicks": int(row[5] or 0),
                "ctr": float(row[6] or 0),
                "position": float(row[7] or 0),
                "date": row[8].isoformat() if row[8] else None
            })
        
        # Get total count
        count_query = "SELECT COUNT(DISTINCT url) FROM gsc_metrics WHERE site_id = %s"
        cur.execute(count_query, (site_id,))
        total = cur.fetchone()[0]
        
        cur.close()
        conn.close()
        
        return {
            "pages": pages,
            "count": len(pages),
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": (total + per_page - 1) // per_page
        }
    except Exception as e:
        return {"error": str(e), "pages": [], "count": 0}

@app.get("/api/ga4-data/{site_id}")
async def get_ga4_data(site_id: int, page: int = 1, per_page: int = 50):
    """Get GA4 data for comparison"""
    if not DATABASE_URL:
        return {"error": "Database not configured"}
    
    try:
        import psycopg2
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        
        cur.execute("""
            SELECT 
                page_path,
                SUM(sessions) as total_sessions,
                SUM(users) as total_users,
                SUM(pageviews) as total_pageviews,
                AVG(avg_session_duration) as avg_duration,
                AVG(bounce_rate) as avg_bounce_rate,
                SUM(conversions) as total_conversions
            FROM ga4_metrics
            WHERE site_id = %s
            GROUP BY page_path
            ORDER BY total_sessions DESC
            LIMIT %s OFFSET %s
        """, (site_id, per_page, (page - 1) * per_page))
        
        pages = []
        for row in cur.fetchall():
            pages.append({
                "page_path": row[0],
                "sessions": int(row[1] or 0),
                "users": int(row[2] or 0),
                "pageviews": int(row[3] or 0),
                "avg_duration": float(row[4] or 0),
                "bounce_rate": float(row[5] or 0),
                "conversions": float(row[6] or 0)
            })
        
        cur.close()
        conn.close()
        
        return {"pages": pages, "count": len(pages)}
    except Exception as e:
        return {"error": str(e), "pages": []}

@app.post("/api/analyze-page-deep")
async def analyze_page_deep(request_data: dict):
    """Deep AI analysis combining GSC, GA4, sitemap content, and competitors"""
    site_id = request_data.get('site_id')
    page_url = request_data.get('page_url')
    
    if not DATABASE_URL:
        return {"error": "Database not configured"}
    
    try:
        import psycopg2
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        
        # 1. Get GSC data for this page
        cur.execute("""
            SELECT 
                query,
                SUM(impressions) as impressions,
                SUM(clicks) as clicks,
                AVG(ctr) as ctr,
                AVG(position) as position
            FROM gsc_metrics
            WHERE site_id = %s AND url = %s
            GROUP BY query
            ORDER BY impressions DESC
            LIMIT 10
        """, (site_id, page_url))
        
        gsc_queries = []
        for row in cur.fetchall():
            gsc_queries.append({
                "query": row[0],
                "impressions": int(row[1]),
                "clicks": int(row[2]),
                "ctr": float(row[3]),
                "position": float(row[4])
            })
        
        if not gsc_queries:
            return {"error": "No GSC data for this page"}
        
        # 2. Get GA4 data for this page
        cur.execute("""
            SELECT 
                SUM(sessions) as sessions,
                SUM(pageviews) as pageviews,
                AVG(avg_session_duration) as avg_duration,
                AVG(bounce_rate) as bounce_rate,
                SUM(conversions) as conversions
            FROM ga4_metrics
            WHERE site_id = %s AND page_path = %s
        """, (site_id, page_url))
        
        ga4_row = cur.fetchone()
        ga4_data = {
            "sessions": int(ga4_row[0] or 0),
            "pageviews": int(ga4_row[1] or 0),
            "avg_duration": float(ga4_row[2] or 0),
            "bounce_rate": float(ga4_row[3] or 0),
            "conversions": float(ga4_row[4] or 0)
        } if ga4_row else None
        
        # 3. Analyze page content
        page_analysis = await analyze_competitor_page(page_url)
        
        # 4. Search competitors for top query
        top_query = gsc_queries[0]['query']
        competitors = await search_google(top_query, 10) if SERPER_API_KEY else []
        
        competitor_analysis = []
        for comp in competitors[:5]:
            analysis = await analyze_competitor_page(comp.get('link'))
            if analysis:
                competitor_analysis.append(analysis)
        
        # 5. Generate AI expert analysis
        ai_suggestions = await generate_expert_seo_analysis(
            gsc_queries, ga4_data, page_analysis, competitor_analysis, top_query
        )
        
        # 6. Store as comprehensive issue
        cur.execute("""
            INSERT INTO issues (site_id, issue_type, severity, description, suggested_action, status)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            site_id,
            'deep_analysis',
            'high',
            f'Complete SEO analysis for "{top_query}" (Position: {gsc_queries[0]["position"]:.1f})',
            ai_suggestions
        ))
        
        issue_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()
        
        return {
            "success": True,
            "issue_id": issue_id,
            "gsc_data": gsc_queries,
            "ga4_data": ga4_data,
            "page_analysis": page_analysis,
            "competitor_count": len(competitor_analysis),
            "ai_suggestions": ai_suggestions
        }
        
    except Exception as e:
        return {"error": str(e)}

async def search_google(query: str, num_results: int = 10):
    """Search Google using Serper API"""
    if not SERPER_API_KEY:
        return []
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://google.serper.dev/search",
                json={"q": query, "num": num_results},
                headers={"X-API-KEY": SERPER_API_KEY, "Content-Type": "application/json"},
                timeout=10.0
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get('organic', [])
            return []
    except:
        return []

async def analyze_competitor_page(url: str):
    """Scrape and analyze competitor page deeply"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=15.0, follow_redirects=True)
            
            if response.status_code == 200:
                html = response.text
                soup = BeautifulSoup(html, 'html.parser')
                
                # SEO Elements
                title = soup.find('title')
                title_text = title.text.strip() if title else ""
                
                meta_desc = soup.find('meta', {'name': 'description'})
                meta_desc_text = meta_desc.get('content', '').strip() if meta_desc else ""
                
                # Headings
                h1s = [h.text.strip() for h in soup.find_all('h1')]
                h2s = [h.text.strip() for h in soup.find_all('h2')]
                h3s = [h.text.strip() for h in soup.find_all('h3')]
                
                # Content Analysis
                text = soup.get_text()
                words = len(text.split())
                
                # Count paragraphs
                paragraphs = len(soup.find_all('p'))
                
                # Images
                images = soup.find_all('img')
                images_with_alt = len([img for img in images if img.get('alt')])
                
                # Links
                links = soup.find_all('a', href=True)
                internal_links = []
                external_links = []
                for link in links:
                    href = link.get('href', '')
                    if href.startswith('http'):
                        if url.split('/')[2] in href:
                            internal_links.append(href)
                        else:
                            external_links.append(href)
                
                # Schema markup
                schemas = soup.find_all('script', {'type': 'application/ld+json'})
                schema_types = []
                for schema in schemas:
                    try:
                        schema_data = json.loads(schema.string)
                        if '@type' in schema_data:
                            schema_types.append(schema_data['@type'])
                        elif isinstance(schema_data, list):
                            for item in schema_data:
                                if '@type' in item:
                                    schema_types.append(item['@type'])
                    except:
                        pass
                
                # FAQ detection
                has_faq = bool(soup.find_all(['div', 'section'], 
                              class_=lambda x: x and 'faq' in x.lower())) or \
                          'FAQPage' in schema_types
                
                # Check for other structured data
                has_breadcrumb = 'BreadcrumbList' in schema_types
                has_article = 'Article' in schema_types or 'BlogPosting' in schema_types
                has_review = 'Review' in schema_types or 'AggregateRating' in schema_types
                
                # Keyword density (top 20 words)
                words_list = text.lower().split()
                word_freq = {}
                stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'is', 'are', 'was', 'were'}
                for word in words_list:
                    if len(word) > 3 and word not in stop_words:
                        word_freq[word] = word_freq.get(word, 0) + 1
                
                top_keywords = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:20]
                
                return {
                    "url": url,
                    "title": title_text,
                    "title_length": len(title_text),
                    "meta_desc": meta_desc_text,
                    "meta_desc_length": len(meta_desc_text),
                    "word_count": words,
                    "paragraph_count": paragraphs,
                    "h1_count": len(h1s),
                    "h2_count": len(h2s),
                    "h3_count": len(h3s),
                    "h1s": h1s,
                    "h2s": h2s[:15],
                    "h3s": h3s[:10],
                    "images_total": len(images),
                    "images_with_alt": images_with_alt,
                    "internal_links": len(internal_links),
                    "external_links": len(external_links),
                    "schemas": schema_types,
                    "has_faq": has_faq,
                    "has_breadcrumb": has_breadcrumb,
                    "has_article_schema": has_article,
                    "has_review_schema": has_review,
                    "top_keywords": top_keywords
                }
    except Exception as e:
        print(f"Error analyzing {url}: {e}")
        return None

async def generate_expert_seo_analysis(gsc_queries, ga4_data, page_analysis, competitors, query):
    """Generate comprehensive SEO expert analysis"""
    
    suggestions = []
    
    # === PART 1: GSC Analysis ===
    suggestions.append("## 🔍 Google Search Console Analysis\n")
    
    top_query_data = gsc_queries[0]
    position = top_query_data['position']
    ctr = top_query_data['ctr']
    impressions = top_query_data['impressions']
    clicks = top_query_data['clicks']
    
    # Position Analysis
    if position > 10:
        suggestions.append(f"❌ **Critical: Page 2+ Ranking** - Your page ranks at position {position:.1f} for '{query}'. You need to reach page 1 (top 10) to get significant traffic.")
        suggestions.append("   → Action: Comprehensive content overhaul + backlink building required.")
    elif position > 5:
        suggestions.append(f"⚠️ **Below Fold Position** - Position {position:.1f} means users must scroll to see your result.")
        suggestions.append("   → Action: Optimize title/meta for higher CTR to improve rankings.")
    elif position > 3:
        suggestions.append(f"✅ **Good Position** - Position {position:.1f} is solid, but top 3 gets 75% of clicks.")
        suggestions.append("   → Action: Add featured snippet content (lists, tables, definitions).")
    else:
        suggestions.append(f"🏆 **Excellent Position** - Position {position:.1f} is in the golden zone!")
    
    # CTR Analysis
    expected_ctr = calculate_expected_ctr(position)
    if ctr < expected_ctr * 0.7:
        suggestions.append(f"\n❌ **Poor CTR Performance** - Your CTR is {ctr*100:.2f}% but should be ~{expected_ctr*100:.1f}% for position {position:.1f}")
        suggestions.append("   → Title Issues: Make it more compelling, add power words like 'Best', 'Guide', '2024'")
        suggestions.append("   → Meta Description: Write benefit-driven copy, include the keyword, add a CTA")
    elif ctr > expected_ctr * 1.2:
        suggestions.append(f"\n✅ **Excellent CTR** - Your {ctr*100:.2f}% CTR beats the {expected_ctr*100:.1f}% average!")
    
    # Impression without clicks
    if impressions > 1000 and clicks < 20:
        suggestions.append(f"\n🚨 **Visibility Crisis** - {impressions} impressions but only {clicks} clicks!")
        suggestions.append("   → Emergency: Rewrite title/meta immediately. Your content is invisible in search.")
    
    # === PART 2: GA4 Cross-Analysis ===
    if ga4_data and ga4_data['sessions'] > 0:
        suggestions.append("\n\n## 📊 GA4 Behavior Analysis\n")
        
        bounce_rate = ga4_data['bounce_rate']
        avg_duration = ga4_data['avg_duration']
        conversions = ga4_data['conversions']
        
        # Bounce Rate
        if bounce_rate > 70:
            suggestions.append(f"❌ **High Bounce Rate: {bounce_rate:.1f}%** - Users leave immediately!")
            suggestions.append("   → User Intent Mismatch: Your content doesn't match what the title/meta promises")
            suggestions.append("   → Page Speed: Check if page loads slowly (use PageSpeed Insights)")
            suggestions.append("   → UX Issues: Add clear headings, better formatting, images")
        elif bounce_rate > 50:
            suggestions.append(f"⚠️ **Moderate Bounce Rate: {bounce_rate:.1f}%**")
            suggestions.append("   → Add internal links to related content")
            suggestions.append("   → Improve first paragraph to hook readers")
        else:
            suggestions.append(f"✅ **Good Engagement: {bounce_rate:.1f}% bounce rate**")
        
        # Session Duration
        if avg_duration < 30:
            suggestions.append(f"\n❌ **Very Short Sessions: {avg_duration:.0f}s** - Users don't read your content")
            suggestions.append("   → Content Quality: Add more depth, examples, visuals")
            suggestions.append("   → Formatting: Use short paragraphs, bullet points, subheadings")
        elif avg_duration < 60:
            suggestions.append(f"\n⚠️ **Short Sessions: {avg_duration:.0f}s** - Could be better")
            suggestions.append("   → Add video content to increase time on page")
        else:
            suggestions.append(f"\n✅ **Good Engagement: {avg_duration:.0f}s average session**")
        
        # Conversion
        if conversions == 0 and ga4_data['sessions'] > 100:
            suggestions.append(f"\n❌ **Zero Conversions** from {ga4_data['sessions']} sessions!")
            suggestions.append("   → Missing CTA: Add clear call-to-action buttons")
            suggestions.append("   → Trust Issues: Add testimonials, reviews, trust badges")
    else:
        suggestions.append("\n\n## 📊 GA4 Data Not Available\n")
        suggestions.append("⚠️ Connect GA4 to get behavioral insights (bounce rate, conversions, etc.)")
    
    # === PART 3: Competitor Analysis ===
    if competitors:
        suggestions.append("\n\n## 🏆 Competitor Gap Analysis\n")
        
        avg_words = sum(c['word_count'] for c in competitors) / len(competitors)
        avg_h2 = sum(c['h2_count'] for c in competitors) / len(competitors)
        avg_images = sum(c['images_total'] for c in competitors) / len(competitors)
        avg_internal_links = sum(c['internal_links'] for c in competitors) / len(competitors)
        
        competitor_schemas = [s for c in competitors for s in c['schemas']]
        competitor_faq_count = sum(1 for c in competitors if c['has_faq'])
        
        if page_analysis:
            your_words = page_analysis['word_count']
            your_h2s = page_analysis['h2_count']
            your_images = page_analysis['images_total']
            
            # Content Length
            if your_words < avg_words * 0.7:
                word_gap = int(avg_words - your_words)
                suggestions.append(f"❌ **Content Length Gap: -{word_gap} words**")
                suggestions.append(f"   → Your page: {your_words} words")
                suggestions.append(f"   → Top competitors: {int(avg_words)} words average")
                suggestions.append(f"   → Action: Add {word_gap} words of high-quality, relevant content")
                suggestions.append("   → Ideas: Add 'How it works', 'Benefits', 'Case studies', 'FAQs'")
            elif your_words > avg_words * 1.3:
                suggestions.append(f"✅ **Content Length Advantage: +{int(your_words - avg_words)} words**")
            else:
                suggestions.append(f"✅ **Competitive Content Length: {your_words} words**")
            
            # Heading Structure
            if your_h2s < avg_h2:
                suggestions.append(f"\n❌ **Poor Content Structure: Only {your_h2s} H2 headings**")
                suggestions.append(f"   → Top competitors use {int(avg_h2)} H2s on average")
                suggestions.append(f"   → Action: Add {int(avg_h2 - your_h2s)} more H2 sections")
                suggestions.append("   → Competitor H2 examples:")
                for comp in competitors[:1]:
                    for h2 in comp['h2s'][:5]:
                        suggestions.append(f"      • {h2}")
            
            # Images
            if your_images < avg_images * 0.6:
                suggestions.append(f"\n❌ **Visual Content Gap: Only {your_images} images**")
                suggestions.append(f"   → Competitors use {int(avg_images)} images on average")
                suggestions.append("   → Add: Screenshots, infographics, charts, product images")
            
            # Alt Text
            if your_images > 0:
                alt_percentage = (page_analysis['images_with_alt'] / your_images) * 100
                if alt_percentage < 80:
                    suggestions.append(f"\n⚠️ **Missing Alt Text: Only {alt_percentage:.0f}% of images have alt text**")
                    suggestions.append("   → SEO Impact: Search engines can't understand your images")
                    suggestions.append("   → Action: Add descriptive alt text to all images")
            
            # Internal Linking
            if page_analysis['internal_links'] < avg_internal_links * 0.5:
                suggestions.append(f"\n❌ **Weak Internal Linking: Only {page_analysis['internal_links']} internal links**")
                suggestions.append(f"   → Competitors average {int(avg_internal_links)} internal links")
                suggestions.append("   → Action: Link to 5-10 related pages on your site")
                suggestions.append("   → Benefits: Helps users + spreads PageRank + signals topic authority")
            
            # Schema Markup
            your_schemas = page_analysis.get('schemas', [])
            if not your_schemas and competitor_schemas:
                unique_schemas = list(set(competitor_schemas))
                suggestions.append(f"\n❌ **Missing Structured Data** - Competitors use:")
                for schema in unique_schemas[:5]:
                    suggestions.append(f"   → {schema} schema")
                suggestions.append("   → Impact: Competitors get rich snippets (star ratings, FAQs, etc.) in search")
                suggestions.append("   → Action: Add schema markup using Google's Structured Data Tool")
            
            # FAQ
            if competitor_faq_count >= 3 and not page_analysis['has_faq']:
                suggestions.append(f"\n❌ **Missing FAQ Section** - {competitor_faq_count} out of {len(competitors)} competitors have FAQs")
                suggestions.append("   → FAQs help you rank for question-based queries")
                suggestions.append("   → Can appear as rich snippet in Google")
                suggestions.append("   → Action: Add 5-10 common questions about your topic")
    
    # === PART 4: Technical SEO ===
    suggestions.append("\n\n## ⚙️ Technical SEO Checklist\n")
    
    if page_analysis:
        # Title Tag
        title_len = page_analysis['title_length']
        if title_len < 30:
            suggestions.append(f"⚠️ **Title Too Short: {title_len} chars** (optimal: 50-60)")
            suggestions.append("   → Expand with descriptive modifiers")
        elif title_len > 60:
            suggestions.append(f"⚠️ **Title Too Long: {title_len} chars** (optimal: 50-60)")
            suggestions.append("   → Google will truncate it in search results")
        else:
            suggestions.append(f"✅ **Title Length Good: {title_len} chars**")
        
        # Meta Description
        meta_len = page_analysis['meta_desc_length']
        if meta_len < 120:
            suggestions.append(f"\n⚠️ **Meta Description Too Short: {meta_len} chars** (optimal: 150-160)")
        elif meta_len > 160:
            suggestions.append(f"\n⚠️ **Meta Description Too Long: {meta_len} chars** (optimal: 150-160)")
        else:
            suggestions.append(f"\n✅ **Meta Description Length Good: {meta_len} chars**")
        
        # H1
        h1_count = page_analysis['h1_count']
        if h1_count == 0:
            suggestions.append("\n❌ **CRITICAL: No H1 tag found!**")
            suggestions.append("   → Every page MUST have exactly one H1")
        elif h1_count > 1:
            suggestions.append(f"\n⚠️ **Multiple H1 tags: {h1_count} found** (should be 1)")
        else:
            suggestions.append(f"\n✅ **Proper H1 structure**")
    
    # === PART 5: Action Plan ===
    suggestions.append("\n\n## 🎯 Priority Action Plan\n")
    suggestions.append("### Week 1 - Quick Wins:")
    suggestions.append("1. ✏️ Rewrite title tag with power words + keyword")
    suggestions.append("2. ✏️ Rewrite meta description with benefit + CTA")
    suggestions.append("3. 🖼️ Add alt text to all images")
    suggestions.append("4. 🔗 Add 5 internal links to related pages")
    
    suggestions.append("\n### Week 2 - Content:")
    suggestions.append("5. 📝 Add missing sections (compare with competitor H2s)")
    suggestions.append("6. ❓ Create FAQ section with 8-10 questions")
    suggestions.append("7. 📊 Add charts/infographics if applicable")
    
    suggestions.append("\n### Week 3 - Technical:")
    suggestions.append("8. 🏷️ Implement schema markup (Article + FAQ)")
    suggestions.append("9. ⚡ Check page speed (should be <3s)")
    suggestions.append("10. 📱 Verify mobile responsiveness")
    
    suggestions.append("\n### Week 4 - Off-Page:")
    suggestions.append("11. 🔗 Get 3-5 quality backlinks")
    suggestions.append("12. 📢 Promote on social media")
    suggestions.append("13. 📧 Email subscribers about updated content")
    
    return "\n".join(suggestions)

def calculate_expected_ctr(position):
    """Calculate expected CTR based on position"""
    ctr_map = {
        1: 0.316, 2: 0.158, 3: 0.106, 4: 0.077, 5: 0.062,
        6: 0.051, 7: 0.043, 8: 0.037, 9: 0.032, 10: 0.028
    }
    pos = int(position)
    if pos <= 10:
        return ctr_map.get(pos, 0.028)
    elif pos <= 20:
        return 0.015
    else:
        return 0.005

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
        return {"error": str(e)}

@app.get("/api/export-gsc-data/{site_id}")
async def export_gsc_data(site_id: int):
    if not DATABASE_URL:
        return {"error": "Database not configured"}
    
    try:
        import psycopg2
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        
        cur.execute("""
            SELECT url, query, country, device, impressions, clicks, ctr, position, date
            FROM gsc_metrics
            WHERE site_id = %s
            ORDER BY impressions DESC
        """, (site_id,))
        
        rows = cur.fetchall()
        cur.close()
        conn.close()
        
        csv_data = "URL,Query,Country,Device,Impressions,Clicks,CTR,Position,Date\n"
        for row in rows:
            csv_data += f'"{row[0]}","{row[1]}","{row[2]}","{row[3]}",{row[4]},{row[5]},{row[6]},{row[7]},"{row[8]}"\n'
        
        return {"success": True, "csv_data": csv_data, "rows_count": len(rows)}
    except Exception as e:
        return {"error": str(e)}
