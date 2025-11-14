import React, { useState } from 'react';
import './SyncForm.css';

function SyncForm() {
  const [sources, setSources] = useState({
    github: false,
    confluence: false,
    jira: false
  });
  const [repositories, setRepositories] = useState('');
  const [spaces, setSpaces] = useState('');
  const [includePaths, setIncludePaths] = useState('');
  const [excludePaths, setExcludePaths] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const handleSourceChange = (source) => {
    setSources(prev => ({ ...prev, [source]: !prev[source] }));
  };

  const handleSync = async () => {
    setLoading(true);
    setError(null);
    setResult(null);

    // Build selected sources array
    const selectedSources = Object.keys(sources).filter(key => sources[key]);

    if (selectedSources.length === 0) {
      setError('Please select at least one source');
      setLoading(false);
      return;
    }

    // Build request body
    const requestBody = {
      sources: selectedSources
    };

    // Add optional fields
    if (repositories.trim()) {
      requestBody.repositories = repositories.split(',').map(r => r.trim());
    }
    if (spaces.trim()) {
      requestBody.spaces = spaces.split(',').map(s => s.trim());
    }
    if (includePaths.trim()) {
      requestBody.include_paths = includePaths.split('\n').map(p => p.trim()).filter(p => p);
    }
    if (excludePaths.trim()) {
      requestBody.exclude_paths = excludePaths.split('\n').map(p => p.trim()).filter(p => p);
    }

    try {
      const response = await fetch('http://localhost:8000/sync', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestBody),
      });

      const data = await response.json();
      
      if (response.ok) {
        setResult(data);
        // Poll for status
        pollSyncStatus();
      } else {
        setError(data.detail || 'Sync failed');
      }
    } catch (err) {
      setError('Failed to connect to server: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  const pollSyncStatus = async () => {
    const interval = setInterval(async () => {
      try {
        const response = await fetch('http://localhost:8000/sync/status');
        const data = await response.json();
        
        setResult(data);
        
        if (data.status === 'completed' || data.status === 'failed') {
          clearInterval(interval);
        }
      } catch (err) {
        console.error('Error polling status:', err);
      }
    }, 3000); // Poll every 3 seconds
  };

  return (
    <div className="sync-form">
      <h2>Sync Data Sources</h2>

      <div className="form-section">
        <label className="section-label">📂 Data Sources</label>
        <div className="checkbox-group">
          <label className="checkbox-label">
            <input
              type="checkbox"
              checked={sources.github}
              onChange={() => handleSourceChange('github')}
            />
            <span>GitHub</span>
          </label>
          <label className="checkbox-label">
            <input
              type="checkbox"
              checked={sources.confluence}
              onChange={() => handleSourceChange('confluence')}
            />
            <span>Confluence</span>
          </label>
          <label className="checkbox-label">
            <input
              type="checkbox"
              checked={sources.jira}
              onChange={() => handleSourceChange('jira')}
            />
            <span>Jira</span>
          </label>
        </div>
      </div>

      {sources.github && (
        <div className="form-section">
          <label className="section-label">🔗 Repositories</label>
          <input
            type="text"
            placeholder="e.g., backend-services, frontend-app (comma-separated)"
            value={repositories}
            onChange={(e) => setRepositories(e.target.value)}
            className="text-input"
          />
        </div>
      )}

      {sources.confluence && (
        <div className="form-section">
          <label className="section-label">📚 Confluence Spaces</label>
          <input
            type="text"
            placeholder="e.g., PRP, DOCS (comma-separated)"
            value={spaces}
            onChange={(e) => setSpaces(e.target.value)}
            className="text-input"
          />
        </div>
      )}

      <div className="form-section">
        <label className="section-label">✅ Include Paths (one per line)</label>
        <textarea
          placeholder="e.g.,&#10;src/&#10;docs/&#10;README.md"
          value={includePaths}
          onChange={(e) => setIncludePaths(e.target.value)}
          className="textarea-input"
          rows="4"
        />
      </div>

      <div className="form-section">
        <label className="section-label">❌ Exclude Paths (one per line)</label>
        <textarea
          placeholder="e.g.,&#10;node_modules/&#10;tests/&#10;*.test.js"
          value={excludePaths}
          onChange={(e) => setExcludePaths(e.target.value)}
          className="textarea-input"
          rows="4"
        />
      </div>

      <button 
        className="sync-button"
        onClick={handleSync}
        disabled={loading}
      >
        {loading ? '🔄 Syncing...' : '🚀 Start Sync'}
      </button>

      {error && (
        <div className="error-message">
          ❌ {error}
        </div>
      )}

      {result && (
        <div className="result-box">
          <h3>Sync Status</h3>
          <div className="status-grid">
            <div className="status-item">
              <span className="status-label">Status:</span>
              <span className={`status-value ${result.status}`}>
                {result.status === 'running' && '⏳ Running'}
                {result.status === 'completed' && '✅ Completed'}
                {result.status === 'failed' && '❌ Failed'}
              </span>
            </div>
            <div className="status-item">
              <span className="status-label">Documents:</span>
              <span className="status-value">{result.processed_documents || 0}</span>
            </div>
            <div className="status-item">
              <span className="status-label">Chunks:</span>
              <span className="status-value">{result.total_chunks || 0}</span>
            </div>
            <div className="status-item">
              <span className="status-label">Errors:</span>
              <span className="status-value">{result.errors || 0}</span>
            </div>
          </div>
          {result.message && (
            <div className="status-message">
              💬 {result.message}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default SyncForm;

