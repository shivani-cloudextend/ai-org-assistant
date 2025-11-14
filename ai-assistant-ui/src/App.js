import React, { useState } from 'react';
import './App.css';
import SyncForm from './components/SyncForm';
import QueryForm from './components/QueryForm';

function App() {
  const [activeTab, setActiveTab] = useState('query');

  return (
    <div className="App">
      <header className="App-header">
        <h1>🤖 AI Organization Assistant</h1>
        <p>Sync your data and query with AI</p>
      </header>

      <div className="tabs">
        <button 
          className={activeTab === 'query' ? 'tab active' : 'tab'}
          onClick={() => setActiveTab('query')}
        >
          💬 Query Assistant
        </button>
        <button 
          className={activeTab === 'sync' ? 'tab active' : 'tab'}
          onClick={() => setActiveTab('sync')}
        >
          🔄 Sync Data
        </button>
      </div>

      <div className="content">
        {activeTab === 'query' && <QueryForm />}
        {activeTab === 'sync' && <SyncForm />}
      </div>

      <footer className="App-footer">
        <p>Powered by AWS Bedrock Titan + ChromaDB</p>
      </footer>
    </div>
  );
}

export default App;
