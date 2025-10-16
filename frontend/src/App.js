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
  const [customStartDate, setCustomStartDate] = useState('');
  const [customEndDate, setCustomEndDate] = useState('');
  const [deviceFilter, setDeviceFilter] = useState('');
  const [countryFilter, setCountryFilter] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [perPage] = useState(50);
  const [viewMode, setViewMode] = useState('gsc');
  const [ga4PropertyId, setGa4PropertyId] = useState('');

  const API_URL = 'https://seo-engine.onrender.com';

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    if (params.get("oauth_success")) {
      alert("Success connected to Google! Now add your website to fetch data.");
      window.history.replaceState({}, document.title, "/");
      loadSites();
    }
    if (params.get("oauth_error")) {
      alert("OAuth failed: " + params.get("oauth_error") + ". Please try again.");
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
          alert('Site added successfully!');
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
    if (!window.confirm(`Are you sure you want to delete "${domain}"?`)) {
      return;
    }
    
    fetch(`${API_URL}/api/sites/${siteId}`, {
      method: 'DELETE'
    })
      .then(res => res.json())
      .then(data => {
        if (data.success) {
          alert('Site deleted successfully!');
          loadSites();
          if (selectedSiteId === siteId) {
            setSelectedSiteId(null);
            setGscData(null);
            setGa4Data(null);
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
      body: JSON.stringify({ site_id: siteId, days: dateRange })
    })
      .then(res => res.json())
      .then(data => {
        setFetchingStates(prev => ({ ...prev, [siteId]: false }));
        
        if (data.success) {
          alert(`${data.message}\n\nDate Range: ${data.date_range}`);
          loadSites();
          loadGSCData(siteId);
        } else if (data.error) {
          let errorMsg = `Error: ${data.error}`;
          if (data.solution) {
            errorMsg += `\n\nSolution:\n${data.solution}`;
          }
          alert(errorMsg);
        }
      })
      .catch(err => {
        setFetchingStates(prev => ({ ...prev, [siteId]: false }));
        alert(`Error: ${err.message}`);
      });
  };

  const handleFetchGA4Data = (siteId) => {
    if (!ga4PropertyId) {
      alert('Please enter your GA4 Property ID first');
      return;
    }
    
    setFetchingStates(prev => ({ ...prev, [`ga4_${siteId}`]: true }));
    
    fetch(`${API_URL}/api/fetch-ga4-data`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ 
        site_id: siteId, 
        property_id: ga4PropertyId,
        days: dateRange 
      })
    })
      .then(res => res.json())
      .then(data => {
        setFetchingStates(prev => ({ ...prev, [`ga4_${siteId}`]: false }));
        
        if (data.success) {
          alert(`${data.message}\n\nDate Range: ${data.date_range}`);
          loadGA4Data(siteId);
        } else {
          alert('Error: ' + (data.error || 'Unknown error'));
        }
      })
      .catch(err => {
        setFetchingStates(prev => ({ ...prev, [`ga4_${siteId}`]: false }));
        alert('Error: ' + err.message);
      });
  };

  const loadGSCData = (siteId, page = 1) => {
    setSelectedSiteId(siteId);
    setCurrentPage(page);
    
    let url = `${API_URL}/api/gsc-data/${siteId}?page=${page}&per_page=${perPage}`;
    
    if (deviceFilter) url += `&filter_device=${deviceFilter}`;
    if (countryFilter) url += `&filter_country=${countryFilter}`;
    if (customStartDate) url += `&start_date=${customStartDate}`;
    if (customEndDate) url += `&end_date=${customEndDate}`;
    
    fetch(url)
      .then(res => res.json())
      .then(data => {
        if (data.pages) {
          setGscData(data);
          setTotalPages(data.total_pages || 1);
        }
      })
      .catch(err => console.error('Error loading GSC data:', err));
  };

  const loadGA4Data = (siteId, page = 1) => {
    setSelectedSiteId(siteId);
    
    fetch(`${API_URL}/api/ga4-data/${siteId}?page=${page}&per_page=${perPage}`)
      .then(res => res.json())
      .then(data => {
        if (data.pages) {
          setGa4Data(data);
        }
      })
      .catch(err => console.error('Error loading GA4 data:', err));
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

  const handleDeepAIAnalysis = (siteId, pageUrl) => {
    setAnalyzingPages(prev => ({ ...prev, [pageUrl]: true }));
    
    fetch(`${API_URL}/api/analyze-page-deep`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ 
        site_id: siteId, 
        page_url: pageUrl 
      })
    })
      .then(res => res.json())
      .then(data => {
        setAnalyzingPages(prev => ({ ...prev, [pageUrl]: false }));
        
        if (data.success) {
          alert('Deep AI Analysis Complete! Check View AI Insights for report.');
          loadIssues(siteId);
        } else {
          alert('Error: ' + (data.error || 'Unknown error'));
        }
      })
      .catch(err => {
        setAnalyzingPages(prev => ({ ...prev, [pageUrl]: false }));
        alert('Error: ' + err.message);
      });
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
          
          alert(`Exported ${data.rows_count} rows to CSV!`);
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

  const renderPagination = () => {
    if (totalPages <= 1) return null;
    
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', gap: '10px', marginTop: '20px', flexWrap: 'wrap' }}>
        <button
          onClick={() => loadGSCData(selectedSiteId, 1)}
          disabled={currentPage === 1}
          style={{ padding: '8px 16px', border: '1px solid #dee2e6', borderRadius: '6px', cursor: currentPage === 1 ? 'not-allowed' : 'pointer', background: currentPage === 1 ? '#e9ecef' : 'white' }}
        >
          First
        </button>
        <button
          onClick={() => loadGSCData(selectedSiteId, currentPage - 1)}
          disabled={currentPage === 1}
          style={{ padding: '8px 16px', border: '1px solid #dee2e6', borderRadius: '6px', cursor: currentPage === 1 ? 'not-allowed' : 'pointer', background: currentPage === 1 ? '#e9ecef' : 'white' }}
        >
          Previous
        </button>
        
        <span style={{ padding: '8px 16px', fontWeight: 'bold' }}>
          Page {currentPage} of {totalPages}
        </span>
        
        <button
          onClick={() => loadGSCData(selectedSiteId, currentPage + 1)}
          disabled={currentPage === totalPages}
          style={{ padding: '8px 16px', border: '1px solid #dee2e6', borderRadius: '6px', cursor: currentPage === totalPages ? 'not-allowed' : 'pointer', background: currentPage === totalPages ? '#e9ecef' : 'white' }}
        >
          Next
        </button>
        <button
          onClick={() => loadGSCData(selectedSiteId, totalPages)}
          disabled={currentPage === totalPages}
          style={{ padding: '8px 16px', border: '1px solid #dee2e6', borderRadius: '6px', cursor: currentPage === totalPages ? 'not-allowed' : 'pointer', background: currentPage === totalPages ? '#e9ecef' : 'white' }}
        >
          Last
        </button>
      </div>
    );
  };

  if (loading && !backendStatus) {
    return (
      <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: '#f5f5f5' }}>
        <div style={{ textAlign: 'center' }}>
          <h2>Loading...</h2>
          <p>Connecting to SEO Engine...</p>
        </div>
      </div>
    );
  }

  return (
    <div style={{ minHeight: '100vh', background: '#f5f5f5' }}>
      <header style={{ background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)', color: 'white', padding: '20px', boxShadow: '0 2px 10px rgba(0,0,0,0.1)' }}>
        <div style={{ maxWidth: '1400px', margin: '0 auto' }}>
          <h1 style={{ margin: 0, fontSize: '32px' }}>SEO Engine Pro</h1>
          <p style={{ margin: '5px 0 0 0', opacity: 0.9 }}>AI-Powered SEO Analysis | GSC + GA4 Integration | Competitor Intelligence</p>
        </div>
      </header>

      <main style={{ padding: '40px 20px', maxWidth: '1400px', margin: '0 auto' }}>
        <div style={{ 
          background: backendStatus ? 'linear-gradient(135deg, #d4edda 0%, #c3e6cb 100%)' : '#f8d7da', 
          border: `2px solid ${backendStatus ? '#28a745' : '#dc3545'}`, 
          padding: '20px', 
          borderRadius: '12px', 
          marginBottom: '30px',
          boxShadow: '0 4px 6px rgba(0,0,0,0.1)'
        }}>
          <h2 style={{ marginTop: 0 }}>System Status</h2>
          {backendStatus && (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '15px' }}>
              <div><strong>Database:</strong> {backendStatus.services?.database}</div>
              <div><strong>OAuth:</strong> {backendStatus.services?.oauth}</div>
              <div><strong>AI Engine:</strong> {backendStatus.services?.ai}</div>
              <div><strong>Serper API:</strong> {backendStatus.services?.serper}</div>
            </div>
          )}
        </div>

        <div style={{ background: 'white', border: '2px solid #e0e0e0', padding: '30px', borderRadius: '12px', marginBottom: '30px', boxShadow: '0 4px 6px rgba(0,0,0,0.1)' }}>
          <h2 style={{ marginTop: 0 }}>Step 1: Connect Google Account</h2>
          <p style={{ color: '#666', marginBottom: '20px' }}>Connect Google Search Console and Google Analytics 4</p>
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
            Connect Google Account
          </button>
        </div>

        <div style={{ background: 'white', border: '2px solid #e0e0e0', padding: '30px', borderRadius: '12px', marginBottom: '30px', boxShadow: '0 4px 6px rgba(0,0,0,0.1)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px', flexWrap: 'wrap', gap: '10px' }}>
            <h2 style={{ margin: 0 }}>Step 2: Your Websites ({sites.length})</h2>
            <button 
              onClick={() => setShowAddSite(!showAddSite)} 
              style={{ 
                background: '#28a745', 
                color: 'white', 
                padding: '12px 24px', 
                fontWeight: 'bold',
                border: 'none', 
                borderRadius: '8px', 
                cursor: 'pointer'
              }}
            >
              {showAddSite ? 'Cancel' : '+ Add Website'}
            </button>
          </div>

          {showAddSite && (
            <form onSubmit={handleAddSite} style={{ background: '#f8f9fa', padding: '25px', borderRadius: '12px', marginBottom: '20px', border: '2px dashed #dee2e6' }}>
              <div style={{ marginBottom: '15px' }}>
                <label style={{ display: 'block', marginBottom: '8px', fontWeight: 'bold' }}>Domain:</label>
                <input
                  type="text"
                  placeholder="example.com"
                  value={newSite.domain}
                  onChange={(e) => setNewSite({...newSite, domain: e.target.value})}
                  style={{ width: '100%', padding: '12px', border: '2px solid #ced4da', borderRadius: '8px' }}
                  required
                />
              </div>
              <div style={{ marginBottom: '20px' }}>
                <label style={{ display: 'block', marginBottom: '8px', fontWeight: 'bold' }}>Sitemap URL:</label>
                <input
                  type="url"
                  placeholder="https://example.com/sitemap.xml"
                  value={newSite.sitemap_url}
                  onChange={(e) => setNewSite({...newSite, sitemap_url: e.target.value})}
                  style={{ width: '100%', padding: '12px', border: '2px solid #ced4da', borderRadius: '8px' }}
                  required
                />
              </div>
              <button 
                type="submit" 
                style={{ background: '#007bff', color: 'white', padding: '12px 24px', border: 'none', borderRadius: '8px', cursor: 'pointer', fontWeight: 'bold', width: '100%' }}
              >
                Add Site
              </button>
            </form>
          )}

          {sites.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '40px', color: '#666' }}>
              <p>No websites added yet</p>
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
                  <h3 style={{ margin: '0 0 15px 0', fontSize: '18px' }}>{site.domain}</h3>

                  <div style={{ background: 'white', padding: '15px', borderRadius: '8px', marginBottom: '15px' }}>
                    <label style={{ fontWeight: 'bold', marginBottom: '10px', display: 'block' }}>Date Range:</label>
                    <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
                      {[7, 30, 90, 180].map(days => (
                        <button
                          key={days}
                          onClick={() => setDateRange(days)}
                          style={{
                            padding: '8px 16px',
                            border: dateRange === days ? '2px solid #007bff' : '1px solid #dee2e6',
                            borderRadius: '6px',
                            background: dateRange === days ? '#007bff' : 'white',
                            color: dateRange === days ? 'white' : '#333',
                            cursor: 'pointer',
                            fontWeight: dateRange === days ? 'bold' : 'normal'
                          }}
                        >
                          {days} days
                        </button>
                      ))}
                    </div>
                  </div>

                  <div style={{ background: 'white', padding: '15px', borderRadius: '8px', marginBottom: '15px' }}>
                    <label style={{ fontWeight: 'bold', display: 'block', marginBottom: '8px' }}>GA4 Property ID:</label>
                    <input
                      type="text"
                      placeholder="Enter GA4 Property ID"
                      value={ga4PropertyId}
                      onChange={(e) => setGa4PropertyId(e.target.value)}
                      style={{ width: '100%', padding: '10px', border: '1px solid #ced4da', borderRadius: '6px' }}
                    />
                    <p style={{ fontSize: '11px', color: '#666', margin: '5px 0 0 0' }}>
                      Find in GA4: Admin Property Property Details
                    </p>
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
                        fontWeight: 'bold'
                      }}
                    >
                      {fetchingStates[site.id] ? 'Fetching GSC...' : 'Fetch GSC Data'}
                    </button>
                    
                    <button 
                      onClick={() => handleFetchGA4Data(site.id)} 
                      disabled={fetchingStates[`ga4_${site.id}`]} 
                      style={{ 
                        background: fetchingStates[`ga4_${site.id}`] ? '#ccc' : '#9c27b0', 
                        color: 'white', 
                        padding: '10px 20px', 
                        border: 'none', 
                        borderRadius: '8px', 
                        cursor: fetchingStates[`ga4_${site.id}`] ? 'not-allowed' : 'pointer',
                        fontWeight: 'bold'
                      }}
                    >
                      {fetchingStates[`ga4_${site.id}`] ? 'Fetching GA4...' : 'Fetch GA4 Data'}
                    </button>
                    
                    <button 
                      onClick={() => {
                        loadGSCData(site.id);
                        loadGA4Data(site.id);
                      }} 
                      style={{ background: '#ffc107', color: '#000', padding: '10px 20px', border: 'none', borderRadius: '8px', cursor: 'pointer', fontWeight: 'bold' }}
                    >
                      View Data
                    </button>
                    
                    <button 
                      onClick={() => loadIssues(site.id)}
                      style={{ background: '#fd7e14', color: 'white', padding: '10px 20px', border: 'none', borderRadius: '8px', cursor: 'pointer', fontWeight: 'bold' }}
                    >
                      View AI Insights
                    </button>
                    
                    <button 
                      onClick={() => handleExportData(site.id)} 
                      style={{ background: '#6f42c1', color: 'white', padding: '10px 20px', border: 'none', borderRadius: '8px', cursor: 'pointer', fontWeight: 'bold' }}
                    >
                      Export CSV
                    </button>
                    
                    <button 
                      onClick={() => handleDeleteSite(site.id, site.domain)} 
                      style={{ background: '#dc3545', color: 'white', padding: '10px 20px', border: 'none', borderRadius: '8px', cursor: 'pointer', fontWeight: 'bold' }}
                    >
                      Delete
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {issues.length > 0 && showIssues && (
          <div style={{ background: 'white', border: '2px solid #e0e0e0', padding: '30px', borderRadius: '12px', marginBottom: '30px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
              <h2 style={{ margin: 0 }}>AI SEO Expert Analysis ({issues.length} insights)</h2>
              <button 
                onClick={() => setShowIssues(false)}
                style={{ background: '#6c757d', color: 'white', padding: '8px 16px', border: 'none', borderRadius: '6px', cursor: 'pointer' }}
              >
                Hide
              </button>
            </div>
            
            <div style={{ display: 'grid', gap: '20px' }}>
              {issues.map((issue, idx) => (
                <div 
                  key={issue.id || idx} 
                  style={{ 
                    border: `2px solid ${getSeverityColor(issue.severity)}`, 
                    borderLeft: `8px solid ${getSeverityColor(issue.severity)}`,
                    padding: '20px', 
                    borderRadius: '10px',
                    background: '#f8f9fa'
                  }}
                >
                  <div style={{ marginBottom: '10px' }}>
                    <h3 style={{ margin: '0 0 10px 0', textTransform: 'capitalize' }}>
                      {issue.type.replace(/_/g, ' ')}
                    </h3>
                    {getSeverityBadge(issue.severity)}
                  </div>
                  
                  <p style={{ margin: '10px 0', fontWeight: 'bold' }}>
                    {issue.description}
                  </p>
                  
                  <div style={{ background: '#e3f2fd', border: '1px solid #2196f3', borderRadius: '6px', padding: '15px', marginTop: '10px' }}>
                    <pre style={{ margin: 0, whiteSpace: 'pre-wrap', fontFamily: 'inherit', fontSize: '13px' }}>
                      {issue.suggestion}
                    </pre>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {(gscData || ga4Data) && selectedSiteId && (
          <div style={{ background: 'white', border: '2px solid #e0e0e0', padding: '30px', borderRadius: '12px' }}>
            <div style={{ display: 'flex', gap: '10px', marginBottom: '20px', borderBottom: '2px solid #dee2e6' }
