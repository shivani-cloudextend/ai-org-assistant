import React, { useState } from 'react';
import './QueryForm.css';

function QueryForm() {
  const [question, setQuestion] = useState('');
  const [userRole, setUserRole] = useState('developer');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const handleQuery = async () => {
    if (!question.trim()) {
      setError('Please enter a question');
      return;
    }

    setLoading(true);
    setError(null);
    setResult(null);

    const requestBody = {
      question: question,
      user_role: userRole
    };

    try {
      const response = await fetch('http://localhost:8000/query', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestBody),
      });

      const data = await response.json();
      
      if (response.ok) {
        setResult(data);
      } else {
        setError(data.detail || 'Query failed');
      }
    } catch (err) {
      setError('Failed to connect to server: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && e.ctrlKey) {
      handleQuery();
    }
  };

  return (
    <div className="query-form">
      <h2>Ask a Question</h2>

      <div className="form-section">
        <label className="section-label">👤 User Role</label>
        <select 
          value={userRole} 
          onChange={(e) => setUserRole(e.target.value)}
          className="select-input"
        >
          <option value="developer">Developer</option>
          <option value="support">Support</option>
          <option value="manager">Manager</option>
          <option value="general">General</option>
        </select>
      </div>

      <div className="form-section">
        <label className="section-label">💭 Your Question</label>
        <textarea
          placeholder="e.g., How does the NetSuite to Outlook sync work?&#10;&#10;Tip: Press Ctrl+Enter to submit"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          onKeyPress={handleKeyPress}
          className="textarea-input question-textarea"
          rows="6"
        />
      </div>

      <button 
        className="query-button"
        onClick={handleQuery}
        disabled={loading}
      >
        {loading ? '🤔 Thinking...' : '🚀 Ask Question'}
      </button>

      {error && (
        <div className="error-message">
          ❌ {error}
        </div>
      )}

      {result && (
        <div className="result-box">
          <div className="answer-section">
            <h3>🤖 Answer</h3>
            <div className="answer-content">
              {result.answer}
            </div>
          </div>

          <div className="metadata-section">
            <div className="metadata-item">
              <span className="metadata-label">⚡ Processing Time:</span>
              <span className="metadata-value">{result.processing_time_seconds?.toFixed(2)}s</span>
            </div>
            <div className="metadata-item">
              <span className="metadata-label">📊 Confidence:</span>
              <span className="metadata-value">{Math.abs(result.confidence_score)?.toFixed(2)}</span>
            </div>
          </div>

          {result.sources && result.sources.length > 0 && (
            <div className="sources-section">
              <h3>📚 Sources ({result.sources.length})</h3>
              <div className="sources-list">
                {result.sources.map((source, index) => (
                  <div key={index} className="source-item">
                    <div className="source-header">
                      <span className="source-type">
                        {source.type === 'github' && '💻'}
                        {source.type === 'confluence' && '📄'}
                        {source.type === 'jira' && '🎫'}
                        {' ' + source.type}
                      </span>
                      <span className="source-similarity">
                        Similarity: {Math.abs(source.similarity_score)?.toFixed(2)}
                      </span>
                    </div>
                    <div className="source-title">
                      {source.title}
                    </div>
                    {source.url && (
                      <a 
                        href={source.url} 
                        target="_blank" 
                        rel="noopener noreferrer"
                        className="source-link"
                      >
                        🔗 View Source
                      </a>
                    )}
                    {source.repository && (
                      <div className="source-meta">
                        Repository: {source.repository}
                      </div>
                    )}
                    {source.file_path && (
                      <div className="source-meta">
                        Path: {source.file_path}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {result.suggested_actions && result.suggested_actions.length > 0 && (
            <div className="suggestions-section">
              <h3>💡 Suggested Actions</h3>
              <ul className="suggestions-list">
                {result.suggested_actions.map((action, index) => (
                  <li key={index}>{action}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default QueryForm;

