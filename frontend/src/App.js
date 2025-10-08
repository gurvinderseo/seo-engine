import React, { useState, useEffect } from 'react';
import './App.css';

function App() {
  const [backendStatus, setBackendStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
 // Handle redirect after OAuth
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    if (params.get("oauth_success")) {
      alert("✅ Successfully connected to Google!");
      // Clean URL so query param is removed
      window.history.replaceState({}, document.title, "/");
      // Optional: call backend to fetch/store tokens or update UI
    }
  }, []);
  // Backend URL - NO trailing slash
  const API_URL = 'https://seo-engine.onrender.com';

  useEffect(() => {
    console.log('Attempting to connect to:', API_URL);
    
    fetch(`${API_URL}/health`, {
      method: 'GET',
      headers: {
        'Accept': 'application/json',
        'Content-Type': 'application/json'
      }
    })
      .then(res => {
        console.log('Response status:', res.status);
        if (!res.ok) {
          throw new Error(`HTTP error! status: ${res.status}`);
        }
        return res.json();
      })
      .then(data => {
        console.log('Backend data:', data);
        setBackendStatus(data);
        setLoading(false);
      })
      .catch(err => {
        console.error('Backend connection error:', err);
        setError(err.message);
        setLoading(false);
      });
  }, [API_URL]);

  const handleConnectGoogle = () => {
    setLoading(true);
    fetch(`${API_URL}/api/connect`)
      .then(res => res.json())
      .then(data => {
        if (data.oauth_url) {
          window.location.href = data.oauth_url;
        } else {
          alert('Error: No OAuth URL received');
          setLoading(false);
        }
      })
      .catch(err => {
        console.error('OAuth error:', err);
        alert('Error connecting to Google: ' + err.message);
        setLoading(false);
      });
  };

  if (loading) {
    return (
      <div style={{ 
        minHeight: '100vh', 
        display: 'flex', 
        alignItems: 'center', 
        justifyContent: 'center',
        background: '#f5f5f5'
      }}>
        <div style={{ textAlign: 'center' }}>
          <h2>🔄 Loading...</h2>
          <p>Connecting to backend at {API_URL}</p>
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
        <div style={{ 
          background: backendStatus && !error ? '#d4edda' : '#f8d7da',
          border: `1px solid ${backendStatus && !error ? '#c3e6cb' : '#f5c6cb'}`,
          padding: '20px',
          borderRadius: '8px',
          marginBottom: '30px'
        }}>
          <h2 style={{ marginTop: 0 }}>Backend Status</h2>
          {error ? (
            <>
              <p><strong>❌ Error:</strong> {error}</p>
              <p><strong>Backend URL:</strong> {API_URL}</p>
              <p><strong>Troubleshooting:</strong></p>
              <ul>
                <li>Check if backend is running at <a href={`${API_URL}/health`} target="_blank" rel="noopener noreferrer">{API_URL}/health</a></li>
                <li>Check browser console (F12) for CORS errors</li>
                <li>Verify CORS settings in backend allow {window.location.origin}</li>
              </ul>
            </>
          ) : backendStatus ? (
            <>
              <p><strong>✅ Status:</strong> {backendStatus.status}</p>
              <p><strong>Database:</strong> {backendStatus.services?.database || 'N/A'}</p>
              <p><strong>Redis:</strong> {backendStatus.services?.redis || 'N/A'}</p>
              <p><strong>OAuth:</strong> {backendStatus.services?.oauth || 'N/A'}</p>
              <p style={{ fontSize: '14px', color: '#666', marginTop: '10px' }}>
                Connected to: {API_URL}
              </p>
            </>
          ) : (
            <p>⏳ Loading backend status...</p>
          )}
        </div>

        {/* Connect Google Button */}
        {backendStatus && !error && (
          <div style={{ 
            background: 'white',
            border: '1px solid #ddd',
            padding: '30px',
            borderRadius: '8px',
            textAlign: 'center',
            marginBottom: '30px'
          }}>
            <h2>Step 1: Connect Google Search Console</h2>
            <p>Authorize access to your Google Search Console and Analytics data</p>
            <button
              onClick={handleConnectGoogle}
              disabled={loading}
              style={{
                background: loading ? '#ccc' : '#1a73e8',
                color: 'white',
                padding: '15px 30px',
                fontSize: '16px',
                border: 'none',
                borderRadius: '5px',
                cursor: loading ? 'not-allowed' : 'pointer',
                marginTop: '20px',
                transition: 'all 0.2s'
              }}
            >
              {loading ? '⏳ Connecting...' : '🔗 Connect Google Account'}
            </button>
          </div>
        )}

        {/* Feature Cards */}
        <div style={{ 
          display: 'grid', 
          gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))',
          gap: '20px',
          marginTop: '30px'
        }}>
          <div style={{ background: 'white', border: '1px solid #ddd', padding: '20px', borderRadius: '8px' }}>
            <h3>📊 GSC Integration</h3>
            <p>Import impressions, clicks, CTR, and position data automatically from Google Search Console</p>
          </div>
          <div style={{ background: 'white', border: '1px solid #ddd', padding: '20px', borderRadius: '8px' }}>
            <h3>🤖 AI-Powered Analysis</h3>
            <p>Automatically detect low CTR pages, ranking gaps, and conversion issues</p>
          </div>
          <div style={{ background: 'white', border: '1px solid #ddd', padding: '20px', borderRadius: '8px' }}>
            <h3>✨ Auto-Generated Fixes</h3>
            <p>Get AI-generated meta tags, FAQ schemas, and content suggestions</p>
          </div>
          <div style={{ background: 'white', border: '1px solid #ddd', padding: '20px', borderRadius: '8px' }}>
            <h3>📈 Track Results</h3>
            <p>Monitor SEO improvements with automated weekly performance reports</p>
          </div>
        </div>

        {/* Debug Info */}
        <div style={{ 
          marginTop: '40px',
          background: '#f8f9fa',
          padding: '20px',
          borderRadius: '8px',
          fontSize: '14px'
        }}>
          <h3>🔌 System Information</h3>
          <ul style={{ textAlign: 'left', lineHeight: '2' }}>
            <li><strong>Backend URL:</strong> {API_URL}</li>
            <li><strong>Frontend URL:</strong> {window.location.origin}</li>
            <li><strong>API Endpoints:</strong>
              <ul>
                <li><code>GET {API_URL}/health</code> - Health check</li>
                <li><code>GET {API_URL}/api/connect</code> - Start OAuth</li>
                <li><code>GET {API_URL}/api/test-db</code> - Test database</li>
                <li><code>GET {API_URL}/docs</code> - API documentation</li>
              </ul>
            </li>
          </ul>
        </div>
      </main>

      <footer style={{ textAlign: 'center', padding: '20px', marginTop: '40px', borderTop: '1px solid #ddd' }}>
        <p style={{ color: '#666', margin: 0 }}>SEO Engine v1.0 | Built with React + FastAPI</p>
      </footer>
    </div>
  );
}

export default App;
