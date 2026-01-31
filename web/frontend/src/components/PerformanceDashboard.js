import React, { useState, useEffect } from 'react';
import './PerformanceDashboard.css';

const PerformanceDashboard = ({ onClose }) => {
  const [stats, setStats] = useState(null);
  const [history, setHistory] = useState([]);
  const [indexingHistory, setIndexingHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [refreshInterval, setRefreshInterval] = useState(null);

  useEffect(() => {
    fetchPerformanceData();
    
    // Set up auto-refresh every 5 seconds
    const interval = setInterval(fetchPerformanceData, 5000);
    setRefreshInterval(interval);

    return () => {
      if (interval) clearInterval(interval);
    };
  }, []);

  const fetchPerformanceData = async () => {
    try {
      setLoading(true);
      
      // Fetch current stats
      const statsResponse = await fetch('http://localhost:8001/api/performance');
      if (!statsResponse.ok) throw new Error('Failed to fetch performance stats');
      const statsData = await statsResponse.json();
      setStats(statsData);

      // Fetch response time history
      const historyResponse = await fetch('http://localhost:8001/api/performance/history?metric_type=response&hours=1');
      if (historyResponse.ok) {
        const historyData = await historyResponse.json();
        setHistory(historyData);
      }

      // Fetch indexing history
      const indexingResponse = await fetch('http://localhost:8001/api/performance/indexing');
      if (indexingResponse.ok) {
        const indexingData = await indexingResponse.json();
        setIndexingHistory(indexingData);
      }

      setError(null);
    } catch (err) {
      setError(err.message);
      console.error('Error fetching performance data:', err);
    } finally {
      setLoading(false);
    }
  };

  const formatBytes = (bytes) => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
  };

  const formatTime = (seconds) => {
    if (seconds < 1) return `${(seconds * 1000).toFixed(0)}ms`;
    return `${seconds.toFixed(2)}s`;
  };

  const formatCurrency = (usd) => {
    return `$${usd.toFixed(4)}`;
  };

  if (loading && !stats) {
    return (
      <div className="performance-dashboard">
        <div className="performance-dashboard-header">
          <h2>Performance Dashboard</h2>
          <button onClick={onClose} className="close-btn">×</button>
        </div>
        <div className="performance-loading">Loading performance data...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="performance-dashboard">
        <div className="performance-dashboard-header">
          <h2>Performance Dashboard</h2>
          <button onClick={onClose} className="close-btn">×</button>
        </div>
        <div className="performance-error">Error: {error}</div>
      </div>
    );
  }

  const current = stats?.current || {};
  const totals = stats?.totals || {};
  const memory = current.memory || {};
  const responseTimes = current.response_times || {};
  const system = current.system || {};

  return (
    <div className="performance-dashboard">
      <div className="performance-dashboard-header">
        <h2>Performance Dashboard</h2>
        <div className="header-actions">
          <button onClick={fetchPerformanceData} className="refresh-btn">🔄 Refresh</button>
          <button onClick={onClose} className="close-btn">×</button>
        </div>
      </div>

      <div className="performance-content">
        {/* Memory Stats */}
        <div className="performance-section">
          <h3>Memory Usage</h3>
          <div className="stats-grid">
            <div className="stat-card">
              <div className="stat-label">Current Memory</div>
              <div className="stat-value">{formatBytes((memory.current_mb || 0) * 1024 * 1024)}</div>
            </div>
            <div className="stat-card">
              <div className="stat-label">Peak Memory</div>
              <div className="stat-value">{formatBytes((memory.peak_mb || 0) * 1024 * 1024)}</div>
            </div>
            <div className="stat-card">
              <div className="stat-label">CPU Usage</div>
              <div className="stat-value">{system.cpu_percent?.toFixed(1) || 0}%</div>
            </div>
            <div className="stat-card">
              <div className="stat-label">Threads</div>
              <div className="stat-value">{system.threads || 0}</div>
            </div>
          </div>
        </div>

        {/* Response Time Stats */}
        {responseTimes && (
          <div className="performance-section">
            <h3>Response Times</h3>
            <div className="stats-grid">
              <div className="stat-card">
                <div className="stat-label">Average</div>
                <div className="stat-value">{formatTime((responseTimes.avg_ms || 0) / 1000)}</div>
              </div>
              <div className="stat-card">
                <div className="stat-label">Min</div>
                <div className="stat-value">{formatTime((responseTimes.min_ms || 0) / 1000)}</div>
              </div>
              <div className="stat-card">
                <div className="stat-label">Max</div>
                <div className="stat-value">{formatTime((responseTimes.max_ms || 0) / 1000)}</div>
              </div>
              <div className="stat-card">
                <div className="stat-label">P95</div>
                <div className="stat-value">{formatTime((responseTimes.p95_ms || 0) / 1000)}</div>
              </div>
              <div className="stat-card">
                <div className="stat-label">P99</div>
                <div className="stat-value">{formatTime((responseTimes.p99_ms || 0) / 1000)}</div>
              </div>
              <div className="stat-card">
                <div className="stat-label">Total Requests</div>
                <div className="stat-value">{responseTimes.total_requests || 0}</div>
              </div>
            </div>
          </div>
        )}

        {/* API Usage Stats */}
        <div className="performance-section">
          <h3>API Usage</h3>
          <div className="stats-grid">
            <div className="stat-card">
              <div className="stat-label">Total API Calls</div>
              <div className="stat-value">{totals.api_calls || 0}</div>
            </div>
            <div className="stat-card">
              <div className="stat-label">Total Cost</div>
              <div className="stat-value">{formatCurrency(totals.total_cost_usd || 0)}</div>
            </div>
          </div>
        </div>

        {/* Indexing Stats */}
        {stats?.latest_indexing && (
          <div className="performance-section">
            <h3>Latest Indexing</h3>
            <div className="stats-grid">
              <div className="stat-card">
                <div className="stat-label">Files Indexed</div>
                <div className="stat-value">{stats.latest_indexing.files_indexed || 0}</div>
              </div>
              <div className="stat-card">
                <div className="stat-label">Chunks Created</div>
                <div className="stat-value">{stats.latest_indexing.chunks_created || 0}</div>
              </div>
              <div className="stat-card">
                <div className="stat-label">Duration</div>
                <div className="stat-value">{formatTime(stats.latest_indexing.duration_seconds || 0)}</div>
              </div>
              <div className="stat-card">
                <div className="stat-label">Files/sec</div>
                <div className="stat-value">{stats.latest_indexing.files_per_second?.toFixed(2) || 0}</div>
              </div>
              <div className="stat-card">
                <div className="stat-label">Chunks/sec</div>
                <div className="stat-value">{stats.latest_indexing.chunks_per_second?.toFixed(2) || 0}</div>
              </div>
            </div>
          </div>
        )}

        {/* Indexing History */}
        {indexingHistory.length > 0 && (
          <div className="performance-section">
            <h3>Indexing History</h3>
            <div className="history-table">
              <table>
                <thead>
                  <tr>
                    <th>Files</th>
                    <th>Chunks</th>
                    <th>Duration</th>
                    <th>Files/sec</th>
                    <th>Chunks/sec</th>
                  </tr>
                </thead>
                <tbody>
                  {indexingHistory.slice(-10).reverse().map((entry, idx) => (
                    <tr key={idx}>
                      <td>{entry.files_indexed}</td>
                      <td>{entry.chunks_created}</td>
                      <td>{formatTime(entry.duration_seconds)}</td>
                      <td>{entry.files_per_second?.toFixed(2)}</td>
                      <td>{entry.chunks_per_second?.toFixed(2)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default PerformanceDashboard;

