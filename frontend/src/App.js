import React, { useState, useEffect } from 'react';
import './App.css';

function App() {
  const [backendStatus, setBackendStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [sites, setSites] = useState([]);
  const [showAddSite, setShowAddSite] = useState(false);
  const [newSite, setNewSite] = useState({ domain: '', sitemap_url: '' });
  const [gscData, setGscData] = useState(null);
  const [ga4Data, setGa4Data] = useState(null);
  const [selectedSiteId, setSelectedSiteId] = useState(null);
  const [fetchingStates, setFetchingStates] = useState({});
  const [analyzingPages, setAnalyzingPages] = useState({});
  const [issues, setIssues] = useState([]);
  const [showIssues, setShowIssues] = useState(false);
  const [dateRange, setDateRange] = useState(90);
  const [ga4PropertyId, setGa4PropertyId] = useState('');
  const [viewMode, setViewMode] = useState('gsc');
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);

  const API_URL = 'https://seo-engine.onrender.com';

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    if (params.get("oauth_success")) {
      alert("Success! Connected to Google");
      window.history.replaceState({}, document.title, "/");
      loadSites();
    }
  }, []);

  useEffect(() => {
    fetch(`${API_URL}/health`)
      .then(res => res.json())
      .then(data => {
        setBackendStatus(data);
        setLoading(false);
        loadSites();
      })
      .catch(err => setLoading(false));
  }, []);

  const loadSites = () => {
    fetch(`${API_URL}/api/sites`)
      .then(res => res.json())
      .then(data => setSites(data.sites || []))
      .catch(err => console.error('Error:', err));
  };

  const handleConnectGoogle = () => {
    fetch(`${API_URL}/api/connect`)
      .then(res => res.json())
      .then(data => {
        if (data.oauth_url) window.location.href = data.oauth_url;
      })
      .catch(err => alert('Error: ' + err.message));
  };

  const handleAddSite = (e) => {
    e.preventDefault();
    let domain = newSite.domain.trim().replace(/^https?:\/\//, '').replace(/\/$/, '');
    
    fetch(`${API_URL}/api/sites`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ domain, sitemap_url: newSite.sitemap_url })
    })
      .then(res => res.json())
      .then(data => {
        if (data.success) {
          alert('Site added!');
          setShowAddSite(false);
          setNewSite({ domain: '', sitemap_url: '' });
          loadSites();
        }
      });
  };

  const handleFetchGSCData = (siteId) => {
    setFetchingStates(prev => ({ ...prev, [siteId]: true }));
    
    fetch(`${API_URL}/api/fetch-gsc-data`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ site_id: siteId, days: dateRange })
    })
      .then(res => res.json())
      .then(data => {
        setFetchingStates(prev => ({ ...prev, [siteId]: false }));
        if (data.success) {
          alert(data.message);
          loadGSCData(siteId);
        } else {
          alert('Error: ' + data.error);
        }
      });
  };

  const handleFetchGA4Data = (siteId) => {
    if (!ga4PropertyId) {
      alert('Enter GA4 Property ID first');
      return;
    }
    
    setFetchingStates(prev => ({ ...prev, [`ga4_${siteId}`]: true }));
    
    fetch(`${API_URL}/api/fetch-ga4-data`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ site_id: siteId, property_id: ga4PropertyId, days: dateRange })
    })
      .then(res => res.json())
      .then(data => {
        setFetchingStates(prev => ({ ...prev, [`ga4_${siteId}`]: false }));
        if (data.success) {
          alert(data.message);
          loadGA4Data(siteId);
        }
      });
  };

  const loadGSCData = (siteId) => {
    setSelectedSiteId(siteId);
    fetch(`${API_URL}/api/gsc-data/${siteId}?page=1&per_page=50`)
      .then(res => res.json())
      .then(data => {
        setGscData(data);
        setTotalPages(data.total_pages || 1);
        setCurrentPage(1);
      });
  };

  const loadGA4Data = (siteId) => {
    setSelectedSiteId(siteId);
    fetch(`${API_URL}/api/ga4-data/${siteId}?page=1&per_page=50`)
      .then(res => res.json())
      .then(data => setGa4Data(data));
  };

  const loadIssues = (siteId) => {
    fetch(`${API_URL}/api/issues/${siteId}`)
      .then(res => res.json())
      .then(data => {
        setIssues(data.issues || []);
        setShowIssues(true);
      });
  };

  const handleDeepAIAnalysis = (siteId, pageUrl) => {
    setAnalyzingPages(prev => ({ ...prev, [pageUrl]: true }));
    
    fetch(`${API_URL}/api/analyze-page-deep`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ site_id: siteId, page_url: pageUrl })
    })
      .then(res => res.json())
      .then(data => {
        setAnalyzingPages(prev => ({ ...prev, [pageUrl]: false }));
        if (data.success) {
          alert('Analysis complete!');
          loadIssues(siteId);
        } else {
          alert('Error: ' + (data.error || 'Unknown'));
        }
      })
      .catch(err => {
        setAnalyzingPages(prev => ({ ...prev, [pageUrl]: false }));
        alert('Error: ' + err.message);
      });
  };

  const getSeverityColor = (severity) => {
    const colors = {
      critical: '#dc3545',
      high: '#fd7e14',
      medium: '#ffc107',
      low: '#17a2b8'
    };
    return colors[severity] || '#6c757d';
  };

  if (loading && !backendStatus) {
    return <div style={{ textAlign: 'center', padding: '50px' }}>Loading...</div>;
  }

  return (
    <div style={{ minHeight: '100vh', background: '#f5f5f5' }}>
      <header style={{ background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)', color: 'white', padding: '20px' }}>
        <div style={{ maxWidth: '1200px', margin: '0 auto' }}>
          <h1 style={{ margin: 0 }}>SEO Engine Pro</h1>
          <p style={{ margin: '5px 0 0 0', opacity: 0.9 }}>AI-Powered SEO Analysis | GSC + GA4</p>
        </div>
      </header>

      <main style={{ padding: '30px 20px', maxWidth: '1200px', margin: '0 auto' }}>
        <div style={{ background: backendStatus ? '#d4edda' : '#f8d7da', border: '2px solid ' + (backendStatus ? '#28a745' : '#dc3545'), padding: '20px', borderRadius: '8px', marginBottom: '30px' }}>
          <h2 style={{ marginTop: 0 }}>System Status</h2>
          {backendStatus && (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '15px' }}>
              <div><strong>Database:</strong> {backendStatus.services?.database}</div>
              <div><strong>OAuth:</strong> {backendStatus.services?.oauth}</div>
            </div>
          )}
        </div>

        <div style={{ background: 'white', border: '2px solid #ddd', padding: '25px', borderRadius: '8px', marginBottom: '30px' }}>
          <h2 style={{ marginTop: 0 }}>Step 1: Connect Google</h2>
          <button onClick={handleConnectGoogle} style={{ background: '#007bff', color: 'white', padding: '12px 24px', border: 'none', borderRadius: '6px', cursor: 'pointer', fontWeight: 'bold' }}>
            Connect Google Account
          </button>
        </div>

        <div style={{ background: 'white', border: '2px solid #ddd', padding: '25px', borderRadius: '8px', marginBottom: '30px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
            <h2 style={{ margin: 0 }}>Step 2: Your Websites ({sites.length})</h2>
            <button onClick={() => setShowAddSite(!showAddSite)} style={{ background: '#28a745', color: 'white', padding: '10px 20px', border: 'none', borderRadius: '6px', cursor: 'pointer', fontWeight: 'bold' }}>
              {showAddSite ? 'Cancel' : '+ Add Website'}
            </button>
          </div>

          {showAddSite && (
            <form onSubmit={handleAddSite} style={{ background: '#f9f9f9', padding: '20px', borderRadius: '6px', marginBottom: '20px', border: '1px dashed #ddd' }}>
              <div style={{ marginBottom: '15px' }}>
                <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>Domain:</label>
                <input type="text" placeholder="example.com" value={newSite.domain} onChange={(e) => setNewSite({...newSite, domain: e.target.value})} style={{ width: '100%', padding: '10px', border: '1px solid #ddd', borderRadius: '4px' }} required />
              </div>
              <div style={{ marginBottom: '15px' }}>
                <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>Sitemap URL:</label>
                <input type="url" placeholder="https://example.com/sitemap.xml" value={newSite.sitemap_url} onChange={(e) => setNewSite({...newSite, sitemap_url: e.target.value})} style={{ width: '100%', padding: '10px', border: '1px solid #ddd', borderRadius: '4px' }} required />
              </div>
              <button type="submit" style={{ background: '#007bff', color: 'white', padding: '10px 20px', border: 'none', borderRadius: '4px', cursor: 'pointer', fontWeight: 'bold', width: '100%' }}>Add Site</button>
            </form>
          )}

          {sites.length === 0 ? (
            <p style={{ textAlign: 'center', color: '#666' }}>No websites added</p>
          ) : (
            <div>
              {sites.map(site => (
                <div key={site.id} style={{ background: '#f9f9f9', padding: '15px', borderRadius: '6px', marginBottom: '15px', border: '1px solid #ddd' }}>
                  <h3 style={{ margin: '0 0 15px 0' }}>{site.domain}</h3>

                  <div style={{ background: 'white', padding: '12px', borderRadius: '4px', marginBottom: '12px', border: '1px solid #ddd' }}>
                    <label style={{ fontWeight: 'bold', marginBottom: '8px', display: 'block' }}>Date Range:</label>
                    <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                      {[7, 30, 90, 180].map(days => (
                        <button key={days} onClick={() => setDateRange(days)} style={{ padding: '6px 12px', border: dateRange === days ? '2px solid #007bff' : '1px solid #ddd', borderRadius: '4px', background: dateRange === days ? '#007bff' : 'white', color: dateRange === days ? 'white' : '#333', cursor: 'pointer', fontWeight: dateRange === days ? 'bold' : 'normal', fontSize: '12px' }}>
                          {days}d
                        </button>
                      ))}
                    </div>
                  </div>

                  <div style={{ background: 'white', padding: '12px', borderRadius: '4px', marginBottom: '12px', border: '1px solid #ddd' }}>
                    <label style={{ fontWeight: 'bold', marginBottom: '5px', display: 'block' }}>GA4 Property ID:</label>
                    <input type="text" placeholder="Enter Property ID" value={ga4PropertyId} onChange={(e) => setGa4PropertyId(e.target.value)} style={{ width: '100%', padding: '8px', border: '1px solid #ddd', borderRadius: '4px', fontSize: '12px' }} />
                  </div>

                  <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                    <button onClick={() => handleFetchGSCData(site.id)} disabled={fetchingStates[site.id]} style={{ background: fetchingStates[site.id] ? '#ccc' : '#17a2b8', color: 'white', padding: '8px 16px', border: 'none', borderRadius: '4px', cursor: fetchingStates[site.id] ? 'not-allowed' : 'pointer', fontWeight: 'bold', fontSize: '12px' }}>
                      {fetchingStates[site.id] ? 'Fetching...' : 'Fetch GSC'}
                    </button>
                    <button onClick={() => handleFetchGA4Data(site.id)} disabled={fetchingStates[`ga4_${site.id}`]} style={{ background: fetchingStates[`ga4_${site.id}`] ? '#ccc' : '#9c27b0', color: 'white', padding: '8px 16px', border: 'none', borderRadius: '4px', cursor: fetchingStates[`ga4_${site.id}`] ? 'not-allowed' : 'pointer', fontWeight: 'bold', fontSize: '12px' }}>
                      {fetchingStates[`ga4_${site.id}`] ? 'Fetching...' : 'Fetch GA4'}
                    </button>
                    <button onClick={() => { loadGSCData(site.id); loadGA4Data(site.id); }} style={{ background: '#ffc107', color: '#000', padding: '8px 16px', border: 'none', borderRadius: '4px', cursor: 'pointer', fontWeight: 'bold', fontSize: '12px' }}>View Data</button>
                    <button onClick={() => loadIssues(site.id)} style={{ background: '#fd7e14', color: 'white', padding: '8px 16px', border: 'none', borderRadius: '4px', cursor: 'pointer', fontWeight: 'bold', fontSize: '12px' }}>AI Insights</button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {issues.length > 0 && showIssues && (
          <div style={{ background: 'white', border: '2px solid #ddd', padding: '25px', borderRadius: '8px', marginBottom: '30px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
              <h2 style={{ margin: 0 }}>AI Analysis ({issues.length})</h2>
              <button onClick={() => setShowIssues(false)} style={{ background: '#6c757d', color: 'white', padding: '6px 12px', border: 'none', borderRadius: '4px', cursor: 'pointer' }}>Hide</button>
            </div>
            {issues.map((issue, idx) => (
              <div key={idx} style={{ borderLeft: '4px solid ' + getSeverityColor(issue.severity), padding: '15px', marginBottom: '15px', background: '#f9f9f9', borderRadius: '4px' }}>
                <h3 style={{ margin: '0 0 8px 0', textTransform: 'capitalize' }}>{issue.type.replace(/_/g, ' ')}</h3>
                <p style={{ margin: '8px 0', fontSize: '13px' }}>{issue.description}</p>
                <div style={{ background: '#e3f2fd', padding: '10px', borderRadius: '4px', fontSize: '12px', whiteSpace: 'pre-wrap', fontFamily: 'monospace', maxHeight: '200px', overflow: 'auto' }}>
                  {issue.suggestion}
                </div>
              </div>
            ))}
          </div>
        )}

        {(gscData || ga4Data) && selectedSiteId && (
          <div style={{ background: 'white', border: '2px solid #ddd', padding: '25px', borderRadius: '8px' }}>
            <div style={{ display: 'flex', gap: '10px', marginBottom: '20px', borderBottom: '2px solid #ddd', paddingBottom: '10px' }}>
              <button onClick={() => setViewMode('gsc')} style={{ padding: '8px 16px', border: 'none', borderBottom: viewMode === 'gsc' ? '3px solid #007bff' : 'none', background: viewMode === 'gsc' ? '#e7f3ff' : 'transparent', color: viewMode === 'gsc' ? '#007bff' : '#666', cursor: 'pointer', fontWeight: 'bold' }}>
                GSC Data
              </button>
              <button onClick={() => setViewMode('ga4')} style={{ padding: '8px 16px', border: 'none', borderBottom: viewMode === 'ga4' ? '3px solid #9c27b0' : 'none', background: viewMode === 'ga4' ? '#f3e5f5' : 'transparent', color: viewMode === 'ga4' ? '#9c27b0' : '#666', cursor: 'pointer', fontWeight: 'bold' }}>
                GA4 Data
              </button>
            </div>

            {viewMode === 'gsc' && gscData && (
              <div>
                <h3>Search Performance ({gscData.total || 0} pages)</h3>
                <div style={{ overflowX: 'auto', border: '1px solid #ddd', borderRadius: '4px' }}>
                  <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '12px' }}>
                    <thead>
                      <tr style={{ background: '#667eea', color: 'white' }}>
                        <th style={{ padding: '8px', textAlign: 'left' }}>URL</th>
                        <th style={{ padding: '8px', textAlign: 'left' }}>Query</th>
                        <th style={{ padding: '8px', textAlign: 'center' }}>Impressions</th>
                        <th style={{ padding: '8px', textAlign: 'center' }}>Clicks</th>
                        <th style={{ padding: '8px', textAlign: 'center' }}>CTR</th>
                        <th style={{ padding: '8px', textAlign: 'center' }}>Position</th>
                        <th style={{ padding: '8px', textAlign: 'center' }}>AI</th>
                      </tr>
                    </thead>
                    <tbody>
                      {gscData.pages && gscData.pages.map((page, idx) => (
                        <tr key={idx} style={{ borderBottom: '1px solid #ddd', background: idx % 2 === 0 ? '#fff' : '#f9f9f9' }}>
                          <td style={{ padding: '8px', maxWidth: '200px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                            {page.url}
                          </td>
                          <td style={{ padding: '8px', maxWidth: '150px', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                            {page.query}
                          </td>
                          <td style={{ padding: '8px', textAlign: 'center', fontWeight: 'bold', color: '#007bff' }}>
                            {page.impressions || 0}
                          </td>
                          <td style={{ padding: '8px', textAlign: 'center', fontWeight: 'bold', color: '#28a745' }}>
                            {page.clicks || 0}
                          </td>
                          <td style={{ padding: '8px', textAlign: 'center', fontWeight: 'bold' }}>
                            {((page.ctr || 0) * 100).toFixed(2)}%
                          </td>
                          <td style={{ padding: '8px', textAlign: 'center', fontWeight: 'bold' }}>
                            {(page.position || 0).toFixed(1)}
                          </td>
                          <td style={{ padding: '8px', textAlign: 'center' }}>
                            <button onClick={() => handleDeepAIAnalysis(selectedSiteId, page.url)} disabled={analyzingPages[page.url]} style={{ background: analyzingPages[page.url] ? '#ccc' : '#9c27b0', color: 'white', padding: '4px 8px', border: 'none', borderRadius: '3px', cursor: analyzingPages[page.url] ? 'not-allowed' : 'pointer', fontSize: '11px', fontWeight: 'bold' }}>
                              {analyzingPages[page.url] ? 'AI...' : 'AI'}
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {viewMode === 'ga4' && ga4Data && (
              <div>
                <h3>GA4 Data ({ga4Data.count || 0} pages)</h3>
                <div style={{ overflowX: 'auto', border: '1px solid #ddd', borderRadius: '4px' }}>
                  <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '12px' }}>
                    <thead>
                      <tr style={{ background: '#9c27b0', color: 'white' }}>
                        <th style={{ padding: '8px', textAlign: 'left' }}>Page Path</th>
                        <th style={{ padding: '8px', textAlign: 'center' }}>Sessions</th>
                        <th style={{ padding: '8px', textAlign: 'center' }}>Bounce Rate</th>
                        <th style={{ padding: '8px', textAlign: 'center' }}>Avg Duration</th>
                        <th style={{ padding: '8px', textAlign: 'center' }}>Conversions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {ga4Data.pages && ga4Data.pages.map((page, idx) => (
                        <tr key={idx} style={{ borderBottom: '1px solid #ddd', background: idx % 2 === 0 ? '#fff' : '#f9f9f9' }}>
                          <td style={{ padding: '8px', maxWidth: '300px', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                            {page.page_path}
                          </td>
                          <td style={{ padding: '8px', textAlign: 'center', fontWeight: 'bold' }}>
                            {page.sessions || 0}
                          </td>
                          <td style={{ padding: '8px', textAlign: 'center', fontWeight: 'bold' }}>
                            {((page.bounce_rate || 0).toFixed(1))}%
                          </td>
                          <td style={{ padding: '8px', textAlign: 'center', fontWeight: 'bold' }}>
                            {((page.avg_duration || 0).toFixed(0))}s
                          </td>
                          <td style={{ padding: '8px', textAlign: 'center', fontWeight: 'bold' }}>
                            {(page.conversions || 0).toFixed(0)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        )}
      </main>

      <footer style={{ textAlign: 'center', padding: '20px', marginTop: '40px', borderTop: '1px solid #ddd', background: 'white', fontSize: '12px', color: '#666' }}>
        <p>SEO Engine Pro v2.0 | React + FastAPI + AI</p>
      </footer>
    </div>
  );
}

export default App;
