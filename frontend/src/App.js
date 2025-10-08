import React, { useState, useEffect } from 'react';
import './App.css';

function App() {
  const [backendStatus, setBackendStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [sites, setSites] = useState([]);
  const [showAddSite, setShowAddSite] = useState(false);
  const [newSite, setNewSite] = useState({ domain: '', sitemap_url: '' });
  const [gscData, setGscData] = useState(null);
  const [selectedSiteId, setSelectedSiteId] = useState(null);

  const API_URL = 'https://seo-engine.onrender.com';

  // Handle OAuth redirect
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    if (params.get("oauth_success")) {
      alert("✅ Successfully connected to Google! Now add your website to fetch data.");
      window.history.replaceState({}, document.title, "/");
      loadSites();  // Reload sites after OAuth
    }
  }, []);

  // Load backend status
  useEffect(() => {
    fetch(`${API_URL}/health`)
      .then(res => res.json())
      .then(data => {
        setBackendStatus(data);
        setLoading(false);
        loadSites();  // Load sites after backend is ready
      })
      .catch(err => {
        setError(err.message);
        setLoading(false);
      });
  }, []);

  const loadSites = () => {
    fetch(`${API_URL}/api/sites`)
      .then(res => res.json())
      .then(data => {
        if (data.sites) {
          setSites(data.sites);
        }
      })
      .catch(err => console.error('Error loading sites:', err));
  };

  const handleConnectGoogle = () => {
    fetch(`${API_URL}/api/connect`)
      .then(res => res.json())
      .then(data => {
        if (data.oauth_url) {
          window.location.href = data.oauth_url;
        }
      })
      .catch(err => alert('Error: ' + err.message));
  };

  const handleAddSite = (e) => {
    e.preventDefault();
    
    fetch(`${API_URL}/api/sites`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(newSite)
    })
      .then(res => res.json())
      .then(data => {
        if (data.success) {
          alert('✅ Site added successfully!');
          setShowAddSite(false);
          setNewSite({ domain: '', sitemap_url: '' });
          loadSites();
        } else {
          alert('Error: ' + (data.error || 'Unknown error'));
        }
      })
      .catch(err => alert('Error: ' + err.message));
  };

  const handleFetchGSCData = (siteId) => {
    setLoading(true);
    
    fetch(`${API_URL}/api/fetch-gsc-data`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ site_id: siteId })
    })
      .then(res => res.json())
      .then(data => {
        setLoading(false);
        if (data.success) {
          alert(`✅ ${data.message}`);
          loadGSCData(siteId);
        } else {
          alert('Error: ' + (data.error || 'Unknown error'));
        }
      })
      .catch(err => {
        setLoading(false);
        alert('Error: ' + err.message);
      });
  };

  const loadGSCData = (siteId) => {
    setSelectedSiteId(siteId);
    
    fetch(`${API_URL}/api/gsc-data/${siteId}`)
      .then(res => res.json())
      .then(data => {
        if (data.pages) {
          setGscData(data);
        }
      })
      .catch(err => console.error('Error loading GSC data:', err));
  };

  if (loading && !backendStatus) {
    return (
      <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: '#f5f5f5' }}>
        <div style={{ textAlign: 'center' }}>
          <h2>🔄 Loading...</h2>
          <p>Connecting to backend...</p>
        </div>
      </div>
    );
  }

  return (
    <div style={{ minHeight: '100vh', background: '#f5f5f5' }}>
      <header style={{ background: '#1a73e8', color: 'white', padding: '20px', boxShadow: '0 2px 4px rgba(0,0,0,0.1)' }}>
        <div style={{ maxWidth: '1200px', margin: '0 auto' }}>
          <h1 style={{ margin: 0 }}>🚀 SEO Engine</h1>
          <p style={{ margin: '5px 0 0 0', opacity: 0.9 }}>AI-Powered SEO Diagnostic & Action Tool</p>
        </div>
      </header>

      <main style={{ padding: '40px 20px', maxWidth: '1200px', margin: '0 auto' }}>
        {/* Backend Status */}
        <div style={{ background: backendStatus ? '#d4edda' : '#f8d7da', border: `1px solid ${backendStatus ? '#c3e6cb' : '#f5c6cb'}`, padding: '20px', borderRadius: '8px', marginBottom: '30px' }}>
          <h2 style={{ marginTop: 0 }}>Backend Status</h2>
          {backendStatus ? (
            <>
              <p><strong>✅ Status:</strong> {backendStatus.status}</p>
              <p><strong>Database:</strong> {backendStatus.services?.database}</p>
              <p><strong>OAuth:</strong> {backendStatus.services?.oauth}</p>
            </>
          ) : (
            <p>❌ Cannot connect to backend</p>
          )}
        </div>

        {/* Step 1: Connect Google */}
        <div style={{ background: 'white', border: '1px solid #ddd', padding: '30px', borderRadius: '8px', marginBottom: '30px' }}>
          <h2>Step 1: Connect Google Account</h2>
          <button onClick={handleConnectGoogle} style={{ background: '#1a73e8', color: 'white', padding: '15px 30px', fontSize: '16px', border: 'none', borderRadius: '5px', cursor: 'pointer' }}>
            🔗 Connect Google Account
          </button>
        </div>

        {/* Step 2: Manage Sites */}
        <div style={{ background: 'white', border: '1px solid #ddd', padding: '30px', borderRadius: '8px', marginBottom: '30px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
            <h2 style={{ margin: 0 }}>Step 2: Your Websites</h2>
            <button onClick={() => setShowAddSite(!showAddSite)} style={{ background: '#28a745', color: 'white', padding: '10px 20px', border: 'none', borderRadius: '5px', cursor: 'pointer' }}>
              + Add Website
            </button>
          </div>

          {showAddSite && (
            <form onSubmit={handleAddSite} style={{ background: '#f8f9fa', padding: '20px', borderRadius: '8px', marginBottom: '20px' }}>
              <div style={{ marginBottom: '15px' }}>
                <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>Domain:</label>
                <input
                  type="text"
                  placeholder="example.com"
                  value={newSite.domain}
                  onChange={(e) => setNewSite({...newSite, domain: e.target.value})}
                  style={{ width: '100%', padding: '10px', border: '1px solid #ddd', borderRadius: '5px' }}
                  required
                />
              </div>
              <div style={{ marginBottom: '15px' }}>
                <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>Sitemap URL:</label>
                <input
                  type="url"
                  placeholder="https://example.com/sitemap.xml"
                  value={newSite.sitemap_url}
                  onChange={(e) => setNewSite({...newSite, sitemap_url: e.target.value})}
                  style={{ width: '100%', padding: '10px', border: '1px solid #ddd', borderRadius: '5px' }}
                  required
                />
              </div>
              <button type="submit" style={{ background: '#1a73e8', color: 'white', padding: '10px 20px', border: 'none', borderRadius: '5px', cursor: 'pointer', marginRight: '10px' }}>
                Add Site
              </button>
              <button type="button" onClick={() => setShowAddSite(false)} style={{ background: '#6c757d', color: 'white', padding: '10px 20px', border: 'none', borderRadius: '5px', cursor: 'pointer' }}>
                Cancel
              </button>
            </form>
          )}

          {sites.length === 0 ? (
            <p style={{ color: '#666' }}>No websites added yet. Click "+ Add Website" to get started.</p>
          ) : (
            <div>
              {sites.map(site => (
                <div key={site.id} style={{ background: '#f8f9fa', padding: '15px', borderRadius: '8px', marginBottom: '10px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div>
                      <h3 style={{ margin: '0 0 5px 0' }}>{site.domain}</h3>
                      <p style={{ margin: '0', fontSize: '14px', color: '#666' }}>{site.sitemap_url}</p>
                      {site.last_scan_at && (
                        <p style={{ margin: '5px 0 0 0', fontSize: '12px', color: '#999' }}>
                          Last scanned: {new Date(site.last_scan_at).toLocaleString()}
                        </p>
                      )}
                    </div>
                    <div>
                      <button onClick={() => handleFetchGSCData(site.id)} disabled={loading} style={{ background: loading ? '#ccc' : '#17a2b8', color: 'white', padding: '10px 20px', border: 'none', borderRadius: '5px', cursor: loading ? 'not-allowed' : 'pointer', marginRight: '10px' }}>
                        {loading ? '⏳ Fetching...' : '📊 Fetch GSC Data'}
                      </button>
                      <button onClick={() => loadGSCData(site.id)} style={{ background: '#ffc107', color: '#000', padding: '10px 20px', border: 'none', borderRadius: '5px', cursor: 'pointer' }}>
                        📈 View Data
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Step 3: View GSC Data */}
        {gscData && (
          <div style={{ background: 'white', border: '1px solid #ddd', padding: '30px', borderRadius: '8px' }}>
            <h2>GSC Data ({gscData.count} pages)</h2>
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead>
                  <tr style={{ background: '#f8f9fa', borderBottom: '2px solid #ddd' }}>
                    <th style={{ padding: '12px', textAlign: 'left' }}>URL</th>
                    <th style={{ padding: '12px', textAlign: 'right' }}>Impressions</th>
                    <th style={{ padding: '12px', textAlign: 'right' }}>Clicks</th>
                    <th style={{ padding: '12px', textAlign: 'right' }}>CTR</th>
                    <th style={{ padding: '12px', textAlign: 'right' }}>Position</th>
                  </tr>
                </thead>
                <tbody>
                  {gscData.pages.map((page, idx) => (
                    <tr key={idx} style={{ borderBottom: '1px solid #eee' }}>
                      <td style={{ padding: '12px' }}>{page.url}</td>
                      <td style={{ padding: '12px', textAlign: 'right' }}>{page.impressions.toLocaleString()}</td>
                      <td style={{ padding: '12px', textAlign: 'right' }}>{page.clicks}</td>
                      <td style={{ padding: '12px', textAlign: 'right' }}>{(page.ctr * 100).toFixed(2)}%</td>
                      <td style={{ padding: '12px', textAlign: 'right' }}>{page.position.toFixed(1)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

export default App;
