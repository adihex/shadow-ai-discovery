import { useState, useEffect, useCallback } from 'react';
import { 
  fetchAssets, 
  fetchAgents, 
  triggerScan, 
  fetchScanHistory 
} from './services/api';
import type { Asset, Scan } from './services/api';

function App() {
  const [activeTab, setActiveTab] = useState<'assets' | 'agents'>('assets');
  const [assets, setAssets] = useState<Asset[]>([]);
  const [agents, setAgents] = useState<Asset[]>([]);
  const [scanHistory, setScanHistory] = useState<Scan[]>([]);
  const [selectedAsset, setSelectedAsset] = useState<Asset | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [scanning, setScanning] = useState<boolean>(false);
  const [scanError, setScanError] = useState<string | null>(null);
  const [filterType, setFilterType] = useState<string>('ALL');

  // Load dashboard data
  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      const [allAssets, allAgents, history] = await Promise.all([
        fetchAssets(),
        fetchAgents(),
        fetchScanHistory()
      ]);
      setAssets(allAssets);
      setAgents(allAgents);
      setScanHistory(history);
      
      // Auto-select first asset if none is selected
      if (allAssets.length > 0 && !selectedAsset) {
        setSelectedAsset(allAssets[0]);
      } else if (selectedAsset) {
        // Refresh selected asset if it exists
        const updated = allAssets.find(a => a.id === selectedAsset.id);
        if (updated) setSelectedAsset(updated);
      }
    } catch (err) {
      console.error("Failed to load dashboard data:", err);
    } finally {
      setLoading(false);
    }
  }, [selectedAsset]);

  useEffect(() => {
    loadData();
  }, []);

  // Poll running scans
  useEffect(() => {
    let interval: any;
    const runningScan = scanHistory.find(s => s.status === 'running');
    if (runningScan) {
      setScanning(true);
      interval = setInterval(async () => {
        const history = await fetchScanHistory();
        setScanHistory(history);
        const stillRunning = history.find(s => s.status === 'running');
        if (!stillRunning) {
          setScanning(false);
          loadData();
          clearInterval(interval);
        }
      }, 2000);
    } else {
      setScanning(false);
    }
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [scanHistory, loadData]);

  // Handle manual scan trigger
  const handleScanTrigger = async () => {
    try {
      setScanning(true);
      setScanError(null);
      const newScan = await triggerScan();
      setScanHistory(prev => [newScan, ...prev]);
    } catch (err: any) {
      setScanning(false);
      setScanError(err.message || "Failed to start scan");
    }
  };

  // Calculate high-level stats
  const totalAssets = assets.length;
  const totalAgents = agents.length;
  const avgRisk = totalAgents > 0 
    ? Math.round(agents.reduce((acc, curr) => acc + curr.risk_score, 0) / totalAgents) 
    : 0;

  // Filter resources
  const filteredAssets = assets.filter(asset => {
    if (filterType === 'ALL') return true;
    return asset.resource_type === filterType;
  });

  const getRiskLabel = (score: number) => {
    if (score >= 70) return { text: 'Critical', class: 'badge-danger' };
    if (score >= 40) return { text: 'Medium', class: 'badge-warning' };
    return { text: 'Low', class: 'badge-success' };
  };

  const getConfidenceLabel = (score: number) => {
    if (score >= 80) return 'High Confidence';
    if (score >= 50) return 'Medium Confidence';
    return 'Low Confidence';
  };

  return (
    <div className="app-container">
      {/* Header */}
      <header className="app-header">
        <div className="brand">
          <div className="brand-icon">Ω</div>
          <div className="brand-title">
            <h1>Shadow AI Discovery</h1>
            <span>GCP Inventory & Governance</span>
          </div>
        </div>

        <div className="header-actions">
          <button 
            className="btn btn-primary" 
            onClick={handleScanTrigger} 
            disabled={scanning}
          >
            {scanning ? (
              <>
                <div className="spinner"></div>
                Scanning Project...
              </>
            ) : (
              <>
                <svg width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                  <path d="M21.5 2v6h-6M21.34 15.57a10 10 0 1 1-.57-8.38l.73-.73" />
                </svg>
                Trigger Scan
              </>
            )}
          </button>
        </div>
      </header>

      {/* Main Grid */}
      <main className={`dashboard-main ${selectedAsset ? 'with-sidebar' : ''}`}>
        
        {/* Left Area (Metrics + Tables) */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
          
          {/* Quick Metrics */}
          <div className="metrics-row">
            <div className="metric-card cyan">
              <div>
                <div className="metric-label">Total Assets Scanned</div>
                <div className="metric-value">{totalAssets}</div>
              </div>
              <div className="metric-subtext">Across Cloud Run, GKE & Functions</div>
            </div>

            <div className="metric-card purple">
              <div>
                <div className="metric-label">Likely AI Workloads</div>
                <div className="metric-value">{totalAgents}</div>
              </div>
              <div className="metric-subtext">Detected by heuristics engine</div>
            </div>

            <div className="metric-card rose">
              <div>
                <div className="metric-label">Avg Agent Risk Score</div>
                <div className="metric-value">{avgRisk}%</div>
              </div>
              <div className="metric-subtext">Based on expose & access profiles</div>
            </div>
          </div>

          {/* Running Scan status alert */}
          {scanning && (
            <div className="scanning-bar-container">
              <div className="spinner"></div>
              <span>Active scan in progress... analyzing cloud workloads, environments, and Service Accounts.</span>
            </div>
          )}

          {scanError && (
            <div className="scanning-bar-container failed">
              <span>⚠️ Error during scan execution: {scanError}</span>
            </div>
          )}

          {/* Main Table Card */}
          <div className="content-card">
            <div className="view-selector-bar">
              <div className="tabs">
                <button 
                  className={`tab-btn ${activeTab === 'assets' ? 'active' : ''}`}
                  onClick={() => { setActiveTab('assets'); setFilterType('ALL'); }}
                >
                  All Cloud Assets ({totalAssets})
                </button>
                <button 
                  className={`tab-btn ${activeTab === 'agents' ? 'active' : ''}`}
                  onClick={() => setActiveTab('agents')}
                >
                  Likely AI Agents ({totalAgents})
                </button>
              </div>

              {activeTab === 'assets' && (
                <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                  <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Filter type:</span>
                  <select 
                    value={filterType} 
                    onChange={(e) => setFilterType(e.target.value)}
                    style={{
                      backgroundColor: 'var(--bg-card)',
                      color: 'var(--text-primary)',
                      border: '1px solid var(--border-color)',
                      padding: '0.4rem 0.8rem',
                      borderRadius: '6px',
                      fontSize: '0.8rem',
                      outline: 'none',
                      cursor: 'pointer'
                    }}
                  >
                    <option value="ALL">All Resources</option>
                    <option value="Cloud Run">Cloud Run</option>
                    <option value="Cloud Function">Cloud Function</option>
                    <option value="GKE">GKE</option>
                    <option value="Vertex AI">Vertex AI</option>
                  </select>
                </div>
              )}
            </div>

            {loading && assets.length === 0 ? (
              <div className="empty-state">
                <div className="spinner" style={{ width: '2rem', height: '2rem' }}></div>
                <p style={{ marginTop: '1rem' }}>Loading workspace inventory...</p>
              </div>
            ) : activeTab === 'assets' ? (
              filteredAssets.length === 0 ? (
                <div className="empty-state">
                  <div className="empty-icon">🔍</div>
                  <p>No matching resources found.</p>
                </div>
              ) : (
                <div className="table-wrapper">
                  <table>
                    <thead>
                      <tr>
                        <th>Resource Name</th>
                        <th>Type</th>
                        <th>Region</th>
                        <th>Classification</th>
                        <th>Confidence</th>
                      </tr>
                    </thead>
                    <tbody>
                      {filteredAssets.map(asset => (
                        <tr 
                          key={asset.id} 
                          className={`table-row-interactive ${selectedAsset?.id === asset.id ? 'selected' : ''}`}
                          onClick={() => setSelectedAsset(asset)}
                        >
                          <td style={{ fontWeight: '600' }}>{asset.name}</td>
                          <td><span className="badge badge-type">{asset.resource_type}</span></td>
                          <td>{asset.region}</td>
                          <td>
                            {asset.is_ai_agent ? (
                              <span className="badge badge-agent">AI Agent</span>
                            ) : (
                              <span style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>Generic Workload</span>
                            )}
                          </td>
                          <td>
                            {asset.is_ai_agent ? (
                              <div>
                                <span style={{ fontSize: '0.85rem', fontWeight: '600' }}>{asset.confidence_score}%</span>
                                <div className="score-indicator-bar">
                                  <div className="score-fill agent" style={{ width: `${asset.confidence_score}%` }}></div>
                                </div>
                              </div>
                            ) : (
                              <span style={{ color: 'var(--text-muted)' }}>—</span>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )
            ) : (
              agents.length === 0 ? (
                <div className="empty-state">
                  <div className="empty-icon">🛡️</div>
                  <p>No Shadow AI workloads discovered in this project.</p>
                </div>
              ) : (
                <div className="table-wrapper">
                  <table>
                    <thead>
                      <tr>
                        <th>Agent Name</th>
                        <th>Runtime</th>
                        <th>Confidence</th>
                        <th>Risk Score</th>
                        <th>Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      {agents.map(agent => {
                        const risk = getRiskLabel(agent.risk_score);
                        return (
                          <tr 
                            key={agent.id} 
                            className={`table-row-interactive ${selectedAsset?.id === agent.id ? 'selected' : ''}`}
                            onClick={() => setSelectedAsset(agent)}
                          >
                            <td style={{ fontWeight: '600' }}>{agent.name}</td>
                            <td><span className="badge badge-runtime">{agent.runtime || 'Unknown'}</span></td>
                            <td>
                              <span style={{ fontWeight: '600' }}>{agent.confidence_score}%</span>
                              <div className="score-indicator-bar">
                                <div className="score-fill agent" style={{ width: `${agent.confidence_score}%` }}></div>
                              </div>
                            </td>
                            <td>
                              <span style={{ fontWeight: '600', color: agent.risk_score >= 70 ? 'var(--accent-rose)' : agent.risk_score >= 40 ? 'var(--accent-amber)' : 'var(--accent-emerald)' }}>
                                {agent.risk_score}%
                              </span>
                              <div className="score-indicator-bar">
                                <div className={`score-fill ${agent.risk_score >= 70 ? 'high' : agent.risk_score >= 40 ? 'medium' : 'low'}`} style={{ width: `${agent.risk_score}%` }}></div>
                              </div>
                            </td>
                            <td>
                              <span className={`badge ${risk.class}`}>{risk.text}</span>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              )
            )}
          </div>
        </div>

        {/* Right Area (Agent detail drawer) */}
        {selectedAsset && (
          <div className="details-sidebar">
            <div className="details-card">
              <div className="details-hero">
                <div className="details-title">{selectedAsset.name}</div>
                <div className="details-subtitle">
                  <span className="badge badge-type">{selectedAsset.resource_type}</span>
                  <span style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>• {selectedAsset.region}</span>
                </div>
              </div>

              {/* Confidence Score Section */}
              {selectedAsset.is_ai_agent && (
                <div className="details-section">
                  <div className="section-title">AI Confidence Breakdown ({selectedAsset.confidence_score}%)</div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', marginBottom: '1rem' }}>
                    <div style={{ fontSize: '0.85rem', color: 'var(--accent-purple)', fontWeight: '600' }}>
                      {getConfidenceLabel(selectedAsset.confidence_score)}
                    </div>
                    <div className="score-indicator-bar" style={{ height: '8px' }}>
                      <div className="score-fill agent" style={{ width: `${selectedAsset.confidence_score}%` }}></div>
                    </div>
                  </div>
                  <div className="indicator-pill-list">
                    {selectedAsset.confidence_reasons.map((reason, idx) => (
                      <div key={idx} className="indicator-pill success">
                        <span className="indicator-bullet">✓</span>
                        <span>{reason}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Risk Level Section */}
              {selectedAsset.is_ai_agent && (
                <div className="details-section">
                  <div className="section-title">Risk Scoring Breakdown ({selectedAsset.risk_score}%)</div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', marginBottom: '1rem' }}>
                    <div style={{ fontSize: '0.85rem', color: selectedAsset.risk_score >= 70 ? 'var(--accent-rose)' : selectedAsset.risk_score >= 40 ? 'var(--accent-amber)' : 'var(--accent-emerald)', fontWeight: '600' }}>
                      {getRiskLabel(selectedAsset.risk_score).text} Risk Level
                    </div>
                    <div className="score-indicator-bar" style={{ height: '8px' }}>
                      <div className={`score-fill ${selectedAsset.risk_score >= 70 ? 'high' : selectedAsset.risk_score >= 40 ? 'medium' : 'low'}`} style={{ width: `${selectedAsset.risk_score}%` }}></div>
                    </div>
                  </div>
                  <div className="indicator-pill-list">
                    {selectedAsset.risk_reasons.length > 0 ? (
                      selectedAsset.risk_reasons.map((reason, idx) => (
                        <div key={idx} className={`indicator-pill ${selectedAsset.risk_score >= 70 ? 'danger' : 'warning'}`}>
                          <span className="indicator-bullet">⚠</span>
                          <span>{reason}</span>
                        </div>
                      ))
                    ) : (
                      <div className="indicator-pill success">
                        <span className="indicator-bullet">✓</span>
                        <span>No significant risks flagged</span>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Relationship Flow Diagram (Bonus 2) */}
              <div className="details-section">
                <div className="section-title">Resource Architecture Flow</div>
                <div className="relationship-graph">
                  <div className="node resource">
                    <span>☁️ {selectedAsset.name}</span>
                  </div>
                  <div className="node-arrow">↓ runs under</div>
                  <div className="node sa">
                    <span style={{ fontSize: '0.75rem', wordBreak: 'break-all' }}>
                      👤 {selectedAsset.service_account ? selectedAsset.service_account.split('@')[0] : 'default-compute'}
                    </span>
                  </div>
                  {selectedAsset.is_ai_agent && (
                    <>
                      <div className="node-arrow">↓ invokes</div>
                      <div className="node dest">
                        <span>🤖 LLM Endpoint / Vertex API</span>
                      </div>
                    </>
                  )}
                </div>
              </div>

              {/* Safe Metadata Grid */}
              <div className="details-section">
                <div className="section-title">Identity & Metadata</div>
                <div className="details-grid">
                  <div className="details-grid-item">
                    <div className="grid-label">IAM Identity (Service Account)</div>
                    <div className="grid-value" style={{ fontSize: '0.75rem' }}>{selectedAsset.service_account || 'Default Compute SA'}</div>
                  </div>
                  <div className="details-grid-item">
                    <div className="grid-label">Runtime / Environment</div>
                    <div className="grid-value">{selectedAsset.runtime || 'Container'}</div>
                  </div>
                  <div className="details-grid-item">
                    <div className="grid-label">Last Discovered Scan</div>
                    <div className="grid-value">{new Date(selectedAsset.last_seen).toLocaleString()}</div>
                  </div>
                </div>
              </div>

              {/* Safe Environment Variables */}
              <div className="details-section">
                <div className="section-title">Environment Variables</div>
                {Object.keys(selectedAsset.env_vars).length > 0 ? (
                  <div className="meta-collapsible">
                    {Object.entries(selectedAsset.env_vars).map(([key, val]) => (
                      <div key={key} className="meta-item">
                        <span className="meta-key">{key}</span>
                        <span className="meta-val">{val}</span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>No variables configured</span>
                )}
              </div>

              {/* Labels */}
              <div className="details-section" style={{ marginBottom: 0 }}>
                <div className="section-title">Labels</div>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.4rem' }}>
                  {Object.keys(selectedAsset.labels).length > 0 ? (
                    Object.entries(selectedAsset.labels).map(([k, v]) => (
                      <span key={k} style={{
                        fontSize: '0.7rem',
                        backgroundColor: 'rgba(255, 255, 255, 0.05)',
                        border: '1px solid var(--border-color)',
                        padding: '0.2rem 0.5rem',
                        borderRadius: '4px',
                        color: 'var(--text-secondary)',
                        fontFamily: 'var(--font-mono)'
                      }}>
                        {k}: {v}
                      </span>
                    ))
                  ) : (
                    <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>No labels applied</span>
                  )}
                </div>
              </div>

            </div>
          </div>
        )}

      </main>
    </div>
  );
}

export default App;
