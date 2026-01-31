import React, { useState, useEffect } from 'react';
import './StatusBar.css';

function StatusBar({ status }) {
  const [stats, setStats] = useState(null);

  useEffect(() => {
    loadStats();
    const interval = setInterval(loadStats, 30000); // Update every 30s
    return () => clearInterval(interval);
  }, []);

  const loadStats = async () => {
    try {
      const response = await fetch('/api/stats');
      const data = await response.json();
      setStats(data);
    } catch (error) {
      console.error('Error loading stats:', error);
    }
  };

  return (
    <div className="status-bar">
      <div className="status-item">
        <span className="status-label">RAG:</span>
        <span className={`status-value ${status.rag_indexed ? 'active' : 'inactive'}`}>
          {status.rag_indexed ? '✓ Indexed' : '○ Not Indexed'}
        </span>
      </div>
      {status.rag_indexed && (
        <div className="status-item">
          <span className="status-label">Chunks:</span>
          <span className="status-value">{status.rag_chunks || 0}</span>
        </div>
      )}
      {stats && stats.cost && (
        <>
          <div className="status-item">
            <span className="status-label">Requests:</span>
            <span className="status-value">{stats.cost.total_requests || 0}</span>
          </div>
          <div className="status-item">
            <span className="status-label">Cost:</span>
            <span className="status-value">${(stats.cost.estimated_cost || 0).toFixed(4)}</span>
          </div>
        </>
      )}
      <div className="status-item">
        <span className="status-label">Model:</span>
        <span className="status-value">{status.model || status.model_info || 'gpt-3.5-turbo'}</span>
      </div>
    </div>
  );
}

export default StatusBar;
