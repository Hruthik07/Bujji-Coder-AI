import React, { useState, useEffect } from 'react';
import './ModelSelector.css';

function ModelSelector({ onModelChange, currentModel }) {
  const [availableModels, setAvailableModels] = useState([]);
  const [selectedModel, setSelectedModel] = useState(currentModel || 'auto');
  const [modelStats, setModelStats] = useState(null);
  const [showInfo, setShowInfo] = useState(false);

  useEffect(() => {
    loadAvailableModels();
    loadModelStats();
    // Load saved preference from localStorage
    const saved = localStorage.getItem('selectedModel');
    if (saved) {
      setSelectedModel(saved);
      if (onModelChange) {
        onModelChange(saved);
      }
    }
  }, []);

  useEffect(() => {
    if (currentModel) {
      setSelectedModel(currentModel);
    }
  }, [currentModel]);

  const loadAvailableModels = async () => {
    try {
      const response = await fetch('/api/status');
      const data = await response.json();
      
      const models = [];
      if (data.available_providers?.openai) {
        models.push({
          id: 'openai',
          name: 'GPT-3.5 Turbo',
          provider: 'OpenAI',
          model: data.model_info?.includes('gpt-3.5-turbo') ? 'gpt-3.5-turbo' : 'gpt-3.5-turbo',
          contextWindow: '16K',
          cost: 'Low',
          description: 'Fast and cost-effective for general tasks'
        });
      }
      if (data.available_providers?.deepseek) {
        models.push({
          id: 'deepseek',
          name: 'DeepSeek Coder',
          provider: 'DeepSeek',
          model: 'deepseek-coder',
          contextWindow: '16K',
          cost: 'Very Low',
          description: 'Specialized for code generation, fast and cheap'
        });
      }
      if (data.available_providers?.anthropic) {
        models.push({
          id: 'anthropic',
          name: 'Claude Sonnet 3.5',
          provider: 'Anthropic',
          model: 'claude-3-5-sonnet-20241022',
          contextWindow: '200K',
          cost: 'Medium',
          description: 'Best for complex reasoning and large context'
        });
      }
      
      // Add auto option
      models.unshift({
        id: 'auto',
        name: 'Auto (Recommended)',
        provider: 'Automatic',
        model: 'auto',
        contextWindow: 'Variable',
        cost: 'Optimized',
        description: 'Automatically selects best model based on task'
      });
      
      setAvailableModels(models);
    } catch (error) {
      console.error('Error loading models:', error);
    }
  };

  const loadModelStats = async () => {
    try {
      const response = await fetch('/api/models/stats');
      if (response.ok) {
        const data = await response.json();
        setModelStats(data);
      }
    } catch (error) {
      // Endpoint might not exist yet, ignore
      console.debug('Model stats endpoint not available');
    }
  };

  const handleModelChange = (modelId) => {
    setSelectedModel(modelId);
    localStorage.setItem('selectedModel', modelId);
    if (onModelChange) {
      onModelChange(modelId);
    }
  };

  const selectedModelInfo = availableModels.find(m => m.id === selectedModel);

  return (
    <div className="model-selector">
      <div className="model-selector-header">
        <label htmlFor="model-select">Model:</label>
        <select
          id="model-select"
          value={selectedModel}
          onChange={(e) => handleModelChange(e.target.value)}
          className="model-select"
        >
          {availableModels.map(model => (
            <option key={model.id} value={model.id}>
              {model.name}
            </option>
          ))}
        </select>
        <button
          className="model-info-btn"
          onClick={() => setShowInfo(!showInfo)}
          title="Show model information"
        >
          ℹ️
        </button>
      </div>
      
      {showInfo && selectedModelInfo && (
        <div className="model-info-card">
          <div className="model-info-header">
            <h4>{selectedModelInfo.name}</h4>
            <button
              className="close-info-btn"
              onClick={() => setShowInfo(false)}
            >
              ×
            </button>
          </div>
          <div className="model-info-details">
            <div className="info-row">
              <span className="info-label">Provider:</span>
              <span className="info-value">{selectedModelInfo.provider}</span>
            </div>
            <div className="info-row">
              <span className="info-label">Context Window:</span>
              <span className="info-value">{selectedModelInfo.contextWindow}</span>
            </div>
            <div className="info-row">
              <span className="info-label">Cost:</span>
              <span className="info-value">{selectedModelInfo.cost}</span>
            </div>
            <div className="info-description">
              {selectedModelInfo.description}
            </div>
            {modelStats && modelStats[selectedModelInfo.id] && (
              <div className="model-stats">
                <h5>Performance</h5>
                <div className="stats-grid">
                  <div className="stat-item">
                    <span className="stat-label">Avg Response Time:</span>
                    <span className="stat-value">
                      {modelStats[selectedModelInfo.id].avgResponseTime?.toFixed(2)}s
                    </span>
                  </div>
                  <div className="stat-item">
                    <span className="stat-label">Total Requests:</span>
                    <span className="stat-value">
                      {modelStats[selectedModelInfo.id].totalRequests}
                    </span>
                  </div>
                  <div className="stat-item">
                    <span className="stat-label">Total Cost:</span>
                    <span className="stat-value">
                      ${modelStats[selectedModelInfo.id].totalCost?.toFixed(4)}
                    </span>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

export default ModelSelector;
