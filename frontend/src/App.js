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
  const [fetchingStates, setFetchingStates] = useState({});
  const [issues, setIssues] = useState([]);
  const [showIssues, setShowIssues] = useState(false);

  const API_URL = 'https://seo-engine.onrender.com';

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    if (params.get("oauth_success")) {
      alert("✅ Successfully connected to Google! Now add your website to fetch data.");
      window.history.replaceState({}, document.title, "/");
      loadSites();
    }
    if (params.get("oauth_error")) {
      alert("❌ OAuth failed: " + params.get("oauth_error") + ". Please try again.");
      window.history.replaceState({}, document.title, "/");
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
        } else {
          alert('Error: ' + (data.error || 'No OAuth URL received'));
        }
      })
      .catch(err => alert('Error: ' + err.message));
  };

  const handleAddSite = (e) => {
    e.preventDefault();
    let domain = newSite.domain.trim();
    domain = domain.replace(/^https?:\/\//, '');
    domain = domain.replace(/\/$/, '');
    
    if (!domain) {
      alert('Please enter a valid domain');
      return;
    }
    
    fetch(`${API_URL}/api/sites`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        domain: domain,
        sitemap_url: newSite.sitemap_url
      })
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

  const handleDeleteSite = (siteId, domain) => {
    if (!window.confirm(`Are you sure you want to delete "${domain}"? All data will be permanently removed.`)) {
      return;
    }
    
    fetch(`${API_URL}/api/sites/${siteId}`, {
      method: 'DELETE'
    })
      .then(res => res.json())
      .then(data => {
        if (data.success) {
          alert('✅ Site deleted successfully!');
          loadSites();
          if (selectedSiteId === siteId) {
            setSelectedSiteId(null);
            setGscData(null);
            setIssues([]);
          }
        } else {
          alert('Error: ' + (data.error || 'Unknown error'));
        }
      })
      .catch(err => alert('Error: ' + err.message));
  };

  const handleFetchGSCData = (siteId) => {
    setFetchingStates(prev => ({ ...prev, [siteId]: true }));
    
    fetch(`${API_URL}/api/fetch-gsc-data`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ site_id: siteId })
    })
      .then(res => res.json())
      .then(data => {
        setFetchingStates(prev => ({ ...prev, [siteId]: false }));
        
        if (data.success) {
          alert(`${data.message}\n\n💡 Tip: Click "View Data" to see results and AI suggestions.`);
          loadSites();
          loadGSCData(siteId);
          loadIssues(siteId);
        } else if (data.error) {
          let errorMsg = `❌ ${data.error}`;
          if (data.solution) {
            errorMsg += `\n\n💡 Solution:\n${data.solution}`;
          }
          if (data.tried_url) {
            errorMsg += `\n\n🔍 Tried to fetch: ${data.tried_url}`;
          }
          alert(errorMsg);
        }
      })
      .catch(err => {
        setFetchingStates(prev => ({ ...prev, [siteId]: false }));
        alert(`Error: ${err.message}\n\n💡 Try:\n1. Check your internet connection\n2. Reconnect Google account\n3. Verify domain is in GSC`);
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

  const loadIssues = (siteId) => {
    fetch(`${API_URL}/api/issues/${siteId}`)
      .then(res => res.json())
      .then(data => {
        if (data.issues) {
          setIssues(data.issues);
          setShowIssues(true);
        }
      })
      .catch(err => console.error('Error loading issues:', err));
  };

  const handleExportData = (siteId) => {
    fetch(`${API_URL}/api/export-gsc-data/${siteId}`)
      .then(res => res.json())
      .then(data => {
        if (data.success && data.csv_data) {
          const blob = new Blob([data.csv_data], { type: 'text/csv' });
          const url = window.URL.createObjectURL(blob);
          const a = document.createElement('a');
          a.href = url;
          a.download = `gsc-data-${siteId}-${new Date().toISOString().split('T')[0]}.csv`;
          document.body.appendChild(a);
          a.click();
          document.body.removeChild(a);
          window.URL.revokeObjectURL(url);
          
          alert(`✅ Exported ${data.rows_count} rows to CSV!`);
        } else {
          alert('Error exporting data: ' + (data.error || 'No data available'));
        }
      })
      .catch(err => alert('Error: ' + err.message));
  };

  const getSeverityColor = (severity) => {
    switch(severity) {
      case 'critical': return '#dc3545';
      case 'high': return '#fd7e14';
      case 'medium': return '#ffc107';
      case 'low': return '#17a2b8';
      default: return '#6c757d';
    }
  };

  const getSeverityBadge = (severity) => {
    const color = getSeverityColor(severity);
    return (
      <span style={{ 
        background: color, 
        color: 'white', 
        padding: '4px 12px', 
        borderRadius: '12px', 
        fontSize: '12px',
        fontWeight: 'bold',
        textTransform: 'uppercase'
      }}>
        {severity}
      </span>
    );
  };

  if (loading && !backendStatus) {
    return (
      <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: '#f5f5f5' }}>
        <div style={{ textAlign: 'center' }}>
          <h2>🔄 Loading...</h2>
          <p>Connecting to SEO Engine...</p>
        </div>
      </div>
    );
  }

  return (
    <div style={{ minHeight: '100vh', background: '#f5f5f5' }}>
      <header style={{ background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)', color: 'white', padding: '20px', boxShadow: '0 2px 10px rgba(0,0,0,0.1)' }}>
        <div style={{ maxWidth: '1200px', margin: '0 auto' }}>
          <h1 style={{ margin: 0, fontSize: '32px' }}>🚀 SEO Engine</h1>
          <p style={{ margin: '5px 0 0 0', opacity: 0.9 }}>AI-Powered SEO Diagnostic & Auto-Fix Tool</p>
        </div>
      </header>

      <main style={{ padding: '40px 20px', maxWidth: '1200px', margin: '0 auto' }}>
        <div style={{ 
          background: backendStatus ? 'linear-gradient(135deg, #d4edda 0%, #c3e6cb 100%)' : '#f8d7da', 
          border: `2px solid ${backendStatus ? '#28a745' : '#dc3545'}`, 
          padding: '20px', 
          borderRadius: '12px', 
          marginBottom: '30px',
          boxShadow: '0 4px 6px rgba(0,0,0,0.1)'
        }}>
          <h2 style={{ marginTop: 0, display: 'flex', alignItems: 'center' }}>
            {backendStatus ? '✅' : '❌'} System Status
          </h2>
          {backendStatus ? (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '15px' }}>
              <div><strong>Database:</strong> {backendStatus.services?.database}</div>
              <div><strong>OAuth:</strong> {backendStatus.services?.oauth}</div>
              <div><strong>Status:</strong> All systems operational</div>
            </div>
          ) : (
            <p>❌ Cannot connect to backend. Please check your internet connection.</p>
          )}
        </div>

        <div style={{ background: 'white', border: '2px solid #e0e0e0', padding: '30px', borderRadius: '12px', marginBottom: '30px', boxShadow: '0 4px 6px rgba(0,0,0,0.1)' }}>
          <h2 style={{ marginTop: 0 }}>📊 Step 1: Connect Google Search Console</h2>
          <p style={{ color: '#666', marginBottom: '20px' }}>
            Connect your Google account to access Search Console data. <strong>Any Google account can connect!</strong>
          </p>
          <button 
            onClick={handleConnectGoogle} 
            style={{ 
              background: 'linear-gradient(135deg, #4285f4 0%, #34a853 100%)', 
              color: 'white', 
              padding: '15px 30px', 
              fontSize: '16px', 
              fontWeight: 'bold',
              border: 'none', 
              borderRadius: '8px', 
              cursor: 'pointer',
              boxShadow: '0 4px 8px rgba(66, 133, 244, 0.3)'
            }}
          >
            🔗 Connect Google Account
          </button>
        </div>

        <div style={{ background: 'white', border: '2px solid #e0e0e0', padding: '30px', borderRadius: '12px', marginBottom: '30px', boxShadow: '0 4px 6px rgba(0,0,0,0.1)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px', flexWrap: 'wrap', gap: '10px' }}>
            <h2 style={{ margin: 0 }}>🌐 Step 2: Your Websites ({sites.length})</h2>
            <button 
              onClick={() => setShowAddSite(!showAddSite)} 
              style={{ 
                background: '#28a745', 
                color: 'white', 
                padding: '12px 24px', 
                fontWeight: 'bold',
                border: 'none', 
                borderRadius: '8px', 
                cursor: 'pointer',
                boxShadow: '0 4px 8px rgba(40, 167, 69, 0.3)'
              }}
            >
              {showAddSite ? '✖ Cancel' : '+ Add Website'}
            </button>
          </div>

          {showAddSite && (
            <form onSubmit={handleAddSite} style={{ background: '#f8f9fa', padding: '25px', borderRadius: '12px', marginBottom: '20px', border: '2px dashed #dee2e6' }}>
              <div style={{ marginBottom: '15px' }}>
                <label style={{ display: 'block', marginBottom: '8px', fontWeight: 'bold', color: '#333' }}>
                  Domain: <span style={{ color: '#dc3545' }}>*</span>
                </label>
                <input
                  type="text"
                  placeholder="example.com (without http://)"
                  value={newSite.domain}
                  onChange={(e) => setNewSite({...newSite, domain: e.target.value})}
                  style={{ width: '100%', padding: '12px', border: '2px solid #ced4da', borderRadius: '8px', fontSize: '15px' }}
                  required
                />
                <p style={{ fontSize: '12px', color: '#666', marginTop: '5px' }}>
                  💡 Enter just the domain, e.g., "example.com"
                </p>
              </div>
              <div style={{ marginBottom: '20px' }}>
                <label style={{ display: 'block', marginBottom: '8px', fontWeight: 'bold', color: '#333' }}>
                  Sitemap URL: <span style={{ color: '#dc3545' }}>*</span>
                </label>
                <input
                  type="url"
                  placeholder="https://example.com/sitemap.xml"
                  value={newSite.sitemap_url}
                  onChange={(e) => setNewSite({...newSite, sitemap_url: e.target.value})}
                  style={{ width: '100%', padding: '12px', border: '2px solid #ced4da', borderRadius: '8px', fontSize: '15px' }}
                  required
                />
                <p style={{ fontSize: '12px', color: '#666', marginTop: '5px' }}>
                  💡 Usually at /sitemap.xml
                </p>
              </div>
              <div style={{ display: 'flex', gap: '10px' }}>
                <button 
                  type="submit" 
                  style={{ background: '#007bff', color: 'white', padding: '12px 24px', border: 'none', borderRadius: '8px', cursor: 'pointer', fontWeight: 'bold', flex: 1 }}
                >
                  ✅ Add Site
                </button>
                <button 
                  type="button" 
                  onClick={() => setShowAddSite(false)} 
                  style={{ background: '#6c757d', color: 'white', padding: '12px 24px', border: 'none', borderRadius: '8px', cursor: 'pointer', fontWeight: 'bold', flex: 1 }}
                >
                  Cancel
                </button>
              </div>
            </form>
          )}

          {sites.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '40px', color: '#666' }}>
              <p style={{ fontSize: '18px', marginBottom: '10px' }}>📝 No websites added yet</p>
              <p>Click "+ Add Website" to get started!</p>
            </div>
          ) : (
            <div style={{ display: 'grid', gap: '15px' }}>
              {sites.map(site => (
                <div 
                  key={site.id} 
                  style={{ 
                    background: 'linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%)', 
                    padding: '20px', 
                    borderRadius: '12px', 
                    border: '2px solid #dee2e6'
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '15px' }}>
                    <div style={{ flex: 1, minWidth: '200px' }}>
                      <h3 style={{ margin: '0 0 8px 0', color: '#333', fontSize: '20px' }}>
                        🌐 {site.domain}
                      </h3>
                      <p style={{ margin: '0 0 5px 0', fontSize: '13px', color: '#666' }}>
                        📄 {site.sitemap_url}
                      </p>
                      {site.last_scan_at && (
                        <p style={{ margin: '5px 0 0 0', fontSize: '12px', color: '#28a745', fontWeight: 'bold' }}>
                          ✅ Last scanned: {new Date(site.last_scan_at).toLocaleString()}
                        </p>
                      )}
                    </div>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '10px' }}>
                      <button 
                        onClick={() => handleFetchGSCData(site.id)} 
                        disabled={fetchingStates[site.id]} 
                        style={{ 
                          background: fetchingStates[site.id] ? '#ccc' : '#17a2b8', 
                          color: 'white', 
                          padding: '10px 20px', 
                          border: 'none', 
                          borderRadius: '8px', 
                          cursor: fetchingStates[site.id] ? 'not-allowed' : 'pointer',
                          fontWeight: 'bold',
                          fontSize: '14px'
                        }}
                      >
                        {fetchingStates[site.id] ? '⏳ Fetching...' : '📊 Fetch Data'}
                      </button>
                      <button 
                        onClick={() => loadGSCData(site.id)} 
                        style={{ background: '#ffc107', color: '#000', padding: '10px 20px', border: 'none', borderRadius: '8px', cursor: 'pointer', fontWeight: 'bold', fontSize: '14px' }}
                      >
                        📈 View Data
                      </button>
                      <button 
                        onClick={() => handleExportData(site.id)} 
                        style={{ background: '#6f42c1', color: 'white', padding: '10px 20px', border: 'none', borderRadius: '8px', cursor: 'pointer', fontWeight: 'bold', fontSize: '14px' }}
                      >
                        💾 Export CSV
                      </button>
                      <button 
                        onClick={() => handleDeleteSite(site.id, site.domain)} 
                        style={{ background: '#dc3545', color: 'white', padding: '10px 20px', border: 'none', borderRadius: '8px', cursor: 'pointer', fontWeight: 'bold', fontSize: '14px' }}
                      >
                        🗑️ Delete
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {issues.length > 0 && showIssues && (
          <div style={{ background: 'white', border: '2px solid #e0e0e0', padding: '30px', borderRadius: '12px', marginBottom: '30px', boxShadow: '0 4px 6px rgba(0,0,0,0.1)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
              <h2 style={{ margin: 0 }}>🤖 AI Diagnostics ({issues.length} issues found)</h2>
              <button 
                onClick={() => setShowIssues(false)}
                style={{ background: '#6c757d', color: 'white', padding: '8px 16px', border: 'none', borderRadius: '6px', cursor: 'pointer' }}
              >
                Hide
              </button>
            </div>
            
            <div style={{ display: 'grid', gap: '15px' }}>
              {issues.map((issue, idx) => (
                <div 
                  key={issue.id || idx} 
                  style={{ 
                    border: `2px solid ${getSeverityColor(issue.severity)}`, 
                    borderLeft: `8px solid ${getSeverityColor(issue.severity)}`,
                    padding: '20px', 
                    borderRadius: '10px',
                    background: 'linear-gradient(135deg, #ffffff 0%, #f8f9fa 100%)'
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '10px', flexWrap: 'wrap', gap: '10px' }}>
                    <div>
                      <h3 style={{ margin: '0 0 8px 0', color: '#333', textTransform: 'capitalize' }}>
                        {issue.type.replace(/_/g, ' ')}
                      </h3>
                      {getSeverityBadge(issue.severity)}
                    </div>
                  </div>
                  
                  <p style={{ margin: '10px 0', color: '#555', lineHeight: '1.6' }}>
                    <strong>Issue:</strong> {issue.description}
                  </p>
                  
                  <div style={{ 
                    background: '#e7f3ff', 
                    border: '2px solid #2196f3', 
                    borderRadius: '8px', 
                    padding: '15px', 
                    marginTop: '15px'
                  }}>
                    <p style={{ margin: 0, color: '#0d47a1', lineHeight: '1.8', whiteSpace: 'pre-wrap' }}>
                      {issue.suggestion}
                    </p>
                  </div>
                  
                  <div style={{ marginTop: '15px', display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
                    <button style={{ background: '#28a745', color: 'white', padding: '10px 20px', border: 'none', borderRadius: '6px', cursor: 'pointer', fontWeight: 'bold' }}>
                      ✅ Apply AI Fix
                    </button>
                    <button style={{ background: '#007bff', color: 'white', padding: '10px 20px', border: 'none', borderRadius: '6px', cursor: 'pointer' }}>
                      📝 Generate Meta Tags
                    </button>
                    <button style={{ background: '#6c757d', color: 'white', padding: '10px 20px', border: 'none', borderRadius: '6px', cursor: 'pointer' }}>
                      ⏭️ Skip
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {gscData && gscData.count > 0 && (
          <div style={{ background: 'white', border: '2px solid #e0e0e0', padding: '30px', borderRadius: '12px', boxShadow: '0 4px 6px rgba(0,0,0,0.1)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px', flexWrap: 'wrap', gap: '10px' }}>
              <h2 style={{ margin: 0 }}>📊 Search Console Data ({gscData.count} pages)</h2>
              <div style={{ display: 'flex', gap: '10px' }}>
                <button 
                  onClick={() => loadIssues(selectedSiteId)}
                  style={{ background: '#17a2b8', color: 'white', padding: '10px 20px', border: 'none', borderRadius: '8px', cursor: 'pointer', fontWeight: 'bold' }}
                >
                  🤖 View AI Suggestions
                </button>
                <button 
                  onClick={() => setGscData(null)}
                  style={{ background: '#6c757d', color: 'white', padding: '10px 20px', border: 'none', borderRadius: '8px', cursor: 'pointer' }}
                >
                  Close
                </button>
              </div>
            </div>
            
            <div style={{ overflowX: 'auto', borderRadius: '8px', border: '1px solid #dee2e6' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', background: 'white' }}>
                <thead>
                  <tr style={{ background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)', color: 'white' }}>
                    <th style={{ padding: '15px', textAlign: 'left', fontWeight: 'bold' }}>URL</th>
                    <th style={{ padding: '15px', textAlign: 'right', fontWeight: 'bold' }}>Impressions</th>
                    <th style={{ padding: '15px', textAlign: 'right', fontWeight: 'bold' }}>Clicks</th>
                    <th style={{ padding: '15px', textAlign: 'right', fontWeight: 'bold' }}>CTR</th>
                    <th style={{ padding: '15px', textAlign: 'right', fontWeight: 'bold' }}>Position</th>
                  </tr>
                </thead>
                <tbody>
                  {gscData.pages.map((page, idx) => (
                    <tr key={idx} style={{ borderBottom: '1px solid #dee2e6', background: idx % 2 === 0 ? '#fff' : '#f8f9fa' }}>
                      <td style={{ padding: '12px', maxWidth: '400px', overflow: 'hidden', textOverflow: 'ellipsis' }} title={page.url}>
                        {page.url}
                      </td>
                      <td style={{ padding: '12px', textAlign: 'right', fontWeight: 'bold', color: '#007bff' }}>
                        {page.impressions.toLocaleString()}
                      </td>
                      <td style={{ padding: '12px', textAlign: 'right', fontWeight: 'bold', color: '#28a745' }}>
                        {page.clicks}
                      </td>
                      <td style={{ padding: '12px', textAlign: 'right', fontWeight: 'bold', color: (page.ctr * 100) < 2 ? '#dc3545' : '#17a2b8' }}>
                        {(page.ctr * 100).toFixed(2)}%
                      </td>
                      <td style={{ padding: '12px', textAlign: 'right', fontWeight: 'bold', color: page.position > 10 ? '#dc3545' : '#28a745' }}>
                        {page.position.toFixed(1)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            
            <div style={{ marginTop: '20px', padding: '15px', background: '#e7f3ff', borderRadius: '8px', border: '1px solid #2196f3' }}>
              <p style={{ margin: 0, color: '#0d47a1' }}>
                💡 <strong>Quick Stats:</strong> Showing top {gscData.count} pages by impressions.
              </p>
            </div>
          </div>
        )}
      </main>

      <footer style={{ textAlign: 'center', padding: '30px 20px', marginTop: '40px', borderTop: '2px solid #dee2e6', background: 'white' }}>
        <p style={{ color: '#666', margin: '0 0 10px 0', fontSize: '14px' }}>
          <strong>SEO Engine v1.0</strong> | Built with React + FastAPI + AI
        </p>
        <p style={{ color: '#999', margin: 0, fontSize: '12px' }}>
          🚀 Free forever | 🔒 Secure | 🤖 AI-powered
        </p>
      </footer>
    </div>
  );
}

export default App;
