import React, { useState, useEffect } from 'react';
import './App.css';

function App() {
  const [backendStatus, setBackendStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [oauthUrl, setOauthUrl] = useState(null);

  const API_URL = process.env.REACT_APP_API_URL || 'https://seo-engine.onrender.com';

  useEffect(() => {
    // Check backend health
    fetch(`${API_URL}/health`)
      .then(res => res.json())
      .then(data => {
        setBackendStatus(data);
        setLoading(false);
      })
      .catch(err => {
        console.error('Backend not reachable:', err);
        setLoading(false);
      });
  }, []);

  const handleConnectGoogle = () => {
    fetch(`${API_URL}/api/connect`)
      .then(res => res.json())
      .then(data => {
        if (data.oauth_url) {
          // Redirect to Google OAuth
          window.location.href = data.oauth_url;
        }
      })
      .catch(err => console.error('Error:', err));
  };

  if (loading) {
    return (
      <div className="App">
        <div style={{ padding: '50px', textAlign: 'center' }}>
          <h2>Loading...</h2>
        </div>
      </div>
    );
  }

  return (
    <div className="App">
      <header style={{ background: '#1a73e8', color: 'white', padding: '20px' }}>
        <h1>🚀 SEO Engine</h1>
        <p>AI-Powered SEO Diagnostic & Action Tool</p>
      </header>

      <main style={{ padding: '40px', maxWidth: '1200px', margin: '0 auto' }}>
        {/* Backend Status */}
        <div style={{ 
          background: backendStatus?.status === 'healthy' ? '#d4edda' : '#f8d7da',
          border: `1px solid ${backendStatus?.status === 'healthy' ? '#c3e6cb' : '#f5c6cb'}`,
          padding: '20px',
          borderRadius: '8px',
          marginBottom: '30px'
        }}>
          <h2>Backend Status</h2>
          {backendStatus ? (
            <>
              <p><strong>Status:</strong> {backendStatus.status}</p>
              <p><strong>Database:</strong> {backendStatus.services?.database || 'N/A'}</p>
              <p><strong>Redis:</strong> {backendStatus.services?.redis || 'N/A'}</p>
              <p><strong>OAuth:</strong> {backendStatus.services?.oauth || 'N/A'}</p>
            </>
          ) : (
            <p>❌ Cannot connect to backend</p>
          )}
        </div>

        {/* Connect Google Button */}
        <div style={{ 
          background: 'white',
          border: '1px solid #ddd',
          padding: '30px',
          borderRadius: '8px',
          textAlign: 'center'
        }}>
          <h2>Step 1: Connect Google Search Console</h2>
          <p>Authorize access to your Google Search Console data</p>
          <button
            onClick={handleConnectGoogle}
            style={{
              background: '#1a73e8',
              color: 'white',
              padding: '15px 30px',
              fontSize: '16px',
              border: 'none',
              borderRadius: '5px',
              cursor: 'pointer',
              marginTop: '20px'
            }}
          >
            🔗 Connect Google Account
          </button>
        </div>

        {/* Feature Cards */}
        <div style={{ 
          display: 'grid', 
          gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))',
          gap: '20px',
          marginTop: '30px'
        }}>
          <div style={{ background: 'white', border: '1px solid #ddd', padding: '20px', borderRadius: '8px' }}>
            <h3>📊 GSC Integration</h3>
            <p>Import impressions, clicks, CTR, and position data automatically</p>
          </div>
          <div style={{ background: 'white', border: '1px solid #ddd', padding: '20px', borderRadius: '8px' }}>
            <h3>🤖 AI-Powered Analysis</h3>
            <p>Detect low CTR, ranking gaps, and conversion issues</p>
          </div>
          <div style={{ background: 'white', border: '1px solid #ddd', padding: '20px', borderRadius: '8px' }}>
            <h3>✨ Auto-Generated Fixes</h3>
            <p>Get meta tags, FAQ schemas, and content suggestions</p>
          </div>
          <div style={{ background: 'white', border: '1px solid #ddd', padding: '20px', borderRadius: '8px' }}>
            <h3>📈 Track Results</h3>
            <p>Monitor improvements with automated weekly reports</p>
          </div>
        </div>

        {/* API Endpoints */}
        <div style={{ 
          marginTop: '40px',
          background: '#f8f9fa',
          padding: '20px',
          borderRadius: '8px'
        }}>
          <h3>🔌 Available API Endpoints:</h3>
          <ul style={{ textAlign: 'left', lineHeight: '2' }}>
            <li><code>GET {API_URL}/</code> - Root endpoint</li>
            <li><code>GET {API_URL}/health</code> - Health check</li>
            <li><code>GET {API_URL}/api/connect</code> - Start OAuth</li>
            <li><code>GET {API_URL}/api/test-db</code> - Test database</li>
            <li><code>GET {API_URL}/api/test-redis</code> - Test Redis</li>
            <li><code>GET {API_URL}/docs</code> - API documentation</li>
          </ul>
        </div>
      </main>
    </div>
  );
}

export default App;
