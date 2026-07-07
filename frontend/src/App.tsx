import { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import { 
  fetchAssets, 
  fetchAgents, 
  triggerScan, 
  fetchScanHistory 
} from './services/api';
import type { Asset, Scan } from './services/api';

type SortKey = 'name' | 'resource_type' | 'region' | 'confidence_score' | 'risk_score';
type SortDir = 'asc' | 'desc';

const PAGE_SIZE = 25;

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
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [sortKey, setSortKey] = useState<SortKey>('risk_score');
  const [sortDir, setSortDir] = useState<SortDir>('desc');
  const [focusedRowIndex, setFocusedRowIndex] = useState<number>(-1);
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [theme, setTheme] = useState<'dark' | 'light'>(() => (localStorage.getItem('theme') as 'dark' | 'light') || 'dark');

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('theme', theme);
  }, [theme]);

  const tbodyRef = useRef<HTMLTableSectionElement>(null);
  const searchRef = useRef<HTMLInputElement>(null);

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
      
      // Auto-select first agent if none is selected
      if (allAgents.length > 0 && !selectedAsset) {
        setSelectedAsset(allAgents[0]);
      } else if (selectedAsset) {
        const updated = [...allAssets, ...allAgents].find(a => a.id === selectedAsset.id);
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
          setScanError(null);
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

  // Global keyboard handler
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && selectedAsset) {
        setSelectedAsset(null);
      }
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        searchRef.current?.focus();
      }
    };
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [selectedAsset]);

  // Stats
  const totalAssets = assets.length;
  const totalAgents = agents.length;
  const avgRisk = totalAgents > 0 
    ? Math.round(agents.reduce((acc, curr) => acc + curr.risk_score, 0) / totalAgents) 
    : 0;

  // Sort helper
  const handleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortDir(d => d === 'asc' ? 'desc' : 'asc');
    } else {
      setSortKey(key);
      setSortDir(key === 'risk_score' || key === 'confidence_score' ? 'desc' : 'asc');
    }
    setCurrentPage(1);
  };

  const getSortIndicator = (key: SortKey) => {
    if (sortKey !== key) return '↕';
    return sortDir === 'asc' ? '↑' : '↓';
  };

  // Filter + sort
  const displayedAssets = useMemo(() => {
    let list = [...assets];

    if (filterType !== 'ALL') {
      list = list.filter(a => a.resource_type === filterType);
    }

    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      list = list.filter(a =>
        a.name.toLowerCase().includes(q) ||
        a.resource_type.toLowerCase().includes(q) ||
        a.region.toLowerCase().includes(q)
      );
    }

    list.sort((a, b) => {
      let aVal: string | number = (a as any)[sortKey] ?? '';
      let bVal: string | number = (b as any)[sortKey] ?? '';
      if (typeof aVal === 'string') aVal = aVal.toLowerCase();
      if (typeof bVal === 'string') bVal = bVal.toLowerCase();
      if (aVal < bVal) return sortDir === 'asc' ? -1 : 1;
      if (aVal > bVal) return sortDir === 'asc' ? 1 : -1;
      return 0;
    });

    return list;
  }, [assets, filterType, searchQuery, sortKey, sortDir]);

  const displayedAgents = useMemo(() => {
    let list = [...agents];

    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      list = list.filter(a =>
        a.name.toLowerCase().includes(q) ||
        (a.runtime || '').toLowerCase().includes(q)
      );
    }

    list.sort((a, b) => {
      let aVal: string | number = (a as any)[sortKey] ?? '';
      let bVal: string | number = (b as any)[sortKey] ?? '';
      if (typeof aVal === 'string') aVal = aVal.toLowerCase();
      if (typeof bVal === 'string') bVal = bVal.toLowerCase();
      if (aVal < bVal) return sortDir === 'asc' ? -1 : 1;
      if (aVal > bVal) return sortDir === 'asc' ? 1 : -1;
      return 0;
    });

    return list;
  }, [agents, searchQuery, sortKey, sortDir]);

  // Pagination
  const currentList = activeTab === 'assets' ? displayedAssets : displayedAgents;
  const totalPages = Math.max(1, Math.ceil(currentList.length / PAGE_SIZE));
  const pagedList = currentList.slice((currentPage - 1) * PAGE_SIZE, currentPage * PAGE_SIZE);

  // Keyboard navigation on table
  const handleTableKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setFocusedRowIndex(i => Math.min(i + 1, pagedList.length - 1));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setFocusedRowIndex(i => Math.max(i - 1, 0));
    } else if (e.key === 'Enter' && focusedRowIndex >= 0 && focusedRowIndex < pagedList.length) {
      setSelectedAsset(pagedList[focusedRowIndex]);
    }
  };

  useEffect(() => {
    if (focusedRowIndex >= 0 && tbodyRef.current) {
      const rows = tbodyRef.current.querySelectorAll('tr');
      rows[focusedRowIndex]?.scrollIntoView({ block: 'nearest' });
      (rows[focusedRowIndex] as HTMLElement)?.focus();
    }
  }, [focusedRowIndex]);

  useEffect(() => {
    setFocusedRowIndex(-1);
    setCurrentPage(1);
  }, [activeTab, filterType, searchQuery]);

  const getRiskLabel = (score: number) => {
    if (score >= 70) return { text: 'Critical', class: 'badge-danger', severity: 'high' };
    if (score >= 40) return { text: 'Medium', class: 'badge-warning', severity: 'medium' };
    return { text: 'Low', class: 'badge-success', severity: 'low' };
  };

  const getConfidenceLabel = (score: number) => {
    if (score >= 80) return 'High Confidence';
    if (score >= 50) return 'Medium Confidence';
    return 'Low Confidence';
  };

  const renderSortableHeader = (key: SortKey, label: string) => (
    <th 
      className={`sortable ${sortKey === key ? 'sort-active' : ''}`}
      onClick={() => handleSort(key)}
      aria-sort={sortKey === key ? (sortDir === 'asc' ? 'ascending' : 'descending') : 'none'}
    >
      {label}<span className="sort-indicator">{getSortIndicator(key)}</span>
    </th>
  );

  const renderPagination = () => {
    if (currentList.length <= PAGE_SIZE) return null;
    const startItem = (currentPage - 1) * PAGE_SIZE + 1;
    const endItem = Math.min(currentPage * PAGE_SIZE, currentList.length);

    return (
      <div className="pagination-bar">
        <span>{startItem}–{endItem} of {currentList.length}</span>
        <div className="pagination-controls">
          <button 
            className="page-btn" 
            disabled={currentPage <= 1} 
            onClick={() => setCurrentPage(p => p - 1)}
            aria-label="Previous page"
          >
            ‹
          </button>
          {Array.from({ length: totalPages }, (_, i) => i + 1)
            .filter(p => p === 1 || p === totalPages || Math.abs(p - currentPage) <= 1)
            .map((p, idx, arr) => (
              <span key={p}>
                {idx > 0 && arr[idx - 1] !== p - 1 && <span style={{ color: 'var(--text-muted)', padding: '0 0.25rem' }}>…</span>}
                <button 
                  className={`page-btn ${p === currentPage ? 'active' : ''}`}
                  onClick={() => setCurrentPage(p)}
                >
                  {p}
                </button>
              </span>
            ))}
          <button 
            className="page-btn" 
            disabled={currentPage >= totalPages} 
            onClick={() => setCurrentPage(p => p + 1)}
            aria-label="Next page"
          >
            ›
          </button>
        </div>
      </div>
    );
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

        <div className="header-actions" style={{ display: 'flex', gap: '0.75rem' }}>
          <button 
            className="btn btn-secondary theme-toggle-btn"
            onClick={() => setTheme(t => t === 'dark' ? 'light' : 'dark')}
            title="Toggle color theme"
            aria-label="Toggle color theme"
          >
            {theme === 'dark' ? (
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                <circle cx="12" cy="12" r="4" />
                <path d="M12 2v2" />
                <path d="M12 20v2" />
                <path d="m4.93 4.93 1.41 1.41" />
                <path d="m17.66 17.66 1.41 1.41" />
                <path d="M2 12h2" />
                <path d="M20 12h2" />
                <path d="m6.34 17.66-1.41 1.41" />
                <path d="m19.07 4.93-1.41 1.41" />
              </svg>
            ) : (
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                <path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z" />
              </svg>
            )}
          </button>
          <button 
            className="btn btn-primary" 
            onClick={handleScanTrigger} 
            disabled={scanning}
          >
            {scanning ? (
              <>
                <div className="spinner" aria-label="Scanning in progress"></div>
                Scanning Project...
              </>
            ) : (
              <>
                <svg width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24" aria-hidden="true">
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
        
        {/* Left Area */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          
          {/* Summary Strip — replaces hero-metric cards */}
          <div className="summary-strip">
            <div className="summary-stat metric-card">
              <span className="summary-stat-value metric-value">{totalAssets}</span>
              <span className="summary-stat-label">Total Assets Scanned</span>
            </div>
            <div className="summary-divider" />
            <div className="summary-stat metric-card">
              <span className="summary-stat-value metric-value">{totalAgents}</span>
              <span className="summary-stat-label">Likely AI Workloads</span>
            </div>
            <div className="summary-divider" />
            <div className="summary-stat metric-card">
              <span className="summary-stat-value metric-value">{avgRisk}%</span>
              <span className="summary-stat-label">Average Risk</span>
            </div>
          </div>

          {/* Running Scan status alert */}
          {scanning && (
            <div className="scanning-bar-container" role="status" aria-live="polite">
              <div className="spinner" aria-hidden="true"></div>
              <span>Active scan in progress — analyzing workloads, environments, and Service Accounts.</span>
            </div>
          )}

          {scanError && (
            <div className="scanning-bar-container failed" role="alert">
              <svg className="alert-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
                <line x1="12" y1="9" x2="12" y2="13" />
                <line x1="12" y1="17" x2="12.01" y2="17" />
              </svg>
              <span>Scan error: {scanError}</span>
            </div>
          )}

          {/* Main Table Card */}
          <div className="content-card">
            <div className="view-selector-bar">
              <div className="tabs">
                <button 
                  className={`tab-btn ${activeTab === 'agents' ? 'active' : ''}`}
                  onClick={() => setActiveTab('agents')}
                >
                  Likely AI Agents ({totalAgents})
                </button>
                <button 
                  className={`tab-btn ${activeTab === 'assets' ? 'active' : ''}`}
                  onClick={() => { setActiveTab('assets'); setFilterType('ALL'); }}
                >
                  All Cloud Assets ({totalAssets})
                </button>
              </div>

              <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
                <div className="search-input-wrap">
                  <svg className="search-icon" width="14" height="14" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24" aria-hidden="true">
                    <circle cx="11" cy="11" r="8" />
                    <path d="M21 21l-4.35-4.35" />
                  </svg>
                  <input
                    ref={searchRef}
                    type="text"
                    className="search-input"
                    placeholder={`Search ${activeTab === 'assets' ? 'resources' : 'agents'}…`}
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    aria-label={`Search ${activeTab === 'assets' ? 'resources' : 'agents'}`}
                  />
                </div>

                {activeTab === 'assets' && (
                  <>
                    <label htmlFor="filter-type" style={{ position: 'absolute', width: '1px', height: '1px', overflow: 'hidden', clip: 'rect(0,0,0,0)' }}>
                      Filter by resource type
                    </label>
                    <div className="select-wrap">
                      <select 
                        id="filter-type"
                        value={filterType} 
                        onChange={(e) => setFilterType(e.target.value)}
                      >
                        <option value="ALL">All Resources</option>
                        <option value="Cloud Run">Cloud Run</option>
                        <option value="Cloud Function">Cloud Function</option>
                        <option value="GKE">GKE</option>
                        <option value="Vertex AI">Vertex AI</option>
                        <option value="Unknown">Unknown</option>
                      </select>
                      <svg className="select-arrow" width="10" height="6" viewBox="0 0 10 6" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                        <path d="M1 1l4 4 4-4" />
                      </svg>
                    </div>
                  </>
                )}
              </div>
            </div>

            {loading && assets.length === 0 ? (
              <div className="empty-state">
                <div className="spinner" style={{ width: '2rem', height: '2rem' }} aria-label="Loading"></div>
                <p style={{ marginTop: '1rem' }}>Loading workspace inventory…</p>
              </div>
            ) : activeTab === 'assets' ? (
              displayedAssets.length === 0 ? (
                <div className="empty-state">
                  <div className="empty-icon">🔍</div>
                  <p>{searchQuery ? `No resources matching "${searchQuery}"` : 'No matching resources found.'}</p>
                  {searchQuery && (
                    <button 
                      className="btn btn-secondary" 
                      style={{ marginTop: '1rem', padding: '0.4rem 0.8rem', fontSize: '0.8rem' }} 
                      onClick={() => setSearchQuery('')}
                    >
                      Clear Search
                    </button>
                  )}
                </div>
              ) : (
                <>
                  <div className="table-wrapper" onKeyDown={handleTableKeyDown}>
                    <table>
                      <thead>
                        <tr>
                          {renderSortableHeader('name', 'Resource Name')}
                          {renderSortableHeader('resource_type', 'Type')}
                          {renderSortableHeader('region', 'Region')}
                          <th>Classification</th>
                          {renderSortableHeader('confidence_score', 'Confidence')}
                        </tr>
                      </thead>
                      <tbody ref={tbodyRef}>
                        {pagedList.map((asset, idx) => (
                          <tr 
                            key={asset.id} 
                            className={`table-row-interactive ${selectedAsset?.id === asset.id ? 'selected' : ''}`}
                            onClick={() => setSelectedAsset(asset)}
                            tabIndex={0}
                            role="button"
                            aria-label={`View details for ${asset.name}`}
                            onFocus={() => setFocusedRowIndex(idx)}
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
                                  <div className="score-indicator-bar" role="meter" aria-valuenow={asset.confidence_score} aria-valuemin={0} aria-valuemax={100} aria-label="Confidence score">
                                    <div className="score-fill agent" style={{ transform: `scaleX(${asset.confidence_score / 100})` }}></div>
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
                    {renderPagination()}
                  </div>
                </>
              )
            ) : (
              displayedAgents.length === 0 ? (
                <div className="empty-state">
                  <div className="empty-icon">🛡️</div>
                  <p>{searchQuery ? `No agents matching "${searchQuery}"` : 'No Shadow AI workloads discovered in this project.'}</p>
                  {searchQuery && (
                    <button 
                      className="btn btn-secondary" 
                      style={{ marginTop: '1rem', padding: '0.4rem 0.8rem', fontSize: '0.8rem' }} 
                      onClick={() => setSearchQuery('')}
                    >
                      Clear Search
                    </button>
                  )}
                </div>
              ) : (
                <>
                  <div className="table-wrapper" onKeyDown={handleTableKeyDown}>
                    <table>
                      <thead>
                        <tr>
                          {renderSortableHeader('name', 'Agent Name')}
                          <th>Runtime</th>
                          {renderSortableHeader('confidence_score', 'Confidence')}
                          {renderSortableHeader('risk_score', 'Risk Score')}
                          <th>Status</th>
                        </tr>
                      </thead>
                      <tbody ref={tbodyRef}>
                        {pagedList.map((agent, idx) => {
                          const risk = getRiskLabel(agent.risk_score);
                          return (
                            <tr 
                              key={agent.id} 
                              className={`table-row-interactive ${selectedAsset?.id === agent.id ? 'selected' : ''}`}
                              onClick={() => setSelectedAsset(agent)}
                              tabIndex={0}
                              role="button"
                              aria-label={`View details for ${agent.name}`}
                              onFocus={() => setFocusedRowIndex(idx)}
                            >
                              <td style={{ fontWeight: '600' }}>{agent.name}</td>
                              <td><span className="badge badge-runtime">{agent.runtime || 'Unknown'}</span></td>
                              <td>
                                <span style={{ fontWeight: '600' }}>{agent.confidence_score}%</span>
                                <div className="score-indicator-bar" role="meter" aria-valuenow={agent.confidence_score} aria-valuemin={0} aria-valuemax={100} aria-label="Confidence score">
                                  <div className="score-fill agent" style={{ transform: `scaleX(${agent.confidence_score / 100})` }}></div>
                                </div>
                              </td>
                              <td>
                                <div style={{ display: 'flex', alignItems: 'baseline', gap: '0.375rem' }}>
                                  <span style={{ fontWeight: '600', color: agent.risk_score >= 70 ? 'var(--accent-rose)' : agent.risk_score >= 40 ? 'var(--accent-amber)' : 'var(--accent-emerald)' }}>
                                    {agent.risk_score}%
                                  </span>
                                  <span className={`severity-label ${risk.severity}`}>{risk.text}</span>
                                </div>
                                <div className="score-indicator-bar" role="meter" aria-valuenow={agent.risk_score} aria-valuemin={0} aria-valuemax={100} aria-label={`Risk score: ${risk.text}`}>
                                  <div className={`score-fill ${risk.severity}`} style={{ transform: `scaleX(${agent.risk_score / 100})` }}></div>
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
                    {renderPagination()}
                  </div>
                </>
              )
            )}
          </div>
        </div>

        {/* Right Area — Detail Sidebar */}
        {selectedAsset && (
          <div className="details-sidebar" role="complementary" aria-label="Asset details">
            <div className="details-card">
              <div className="details-hero">
                <div className="details-hero-header variant-2">
                  <div>
                    <div className="details-title">{selectedAsset.name}</div>
                    <div className="details-subtitle">
                      <span className="badge badge-type">{selectedAsset.resource_type}</span>
                      <span style={{ color: "var(--text-muted)", fontSize: "0.8rem" }}>• {selectedAsset.region}</span>
                    </div>
                  </div>
                  <div className="v2-btn-group">
                    <button 
                      className="v2-close-btn" 
                      onClick={() => setSelectedAsset(null)}
                      aria-label="Close details panel"
                      title="Close (Esc)"
                    >
                      <span className="v2-esc-badge">ESC</span>
                      <svg width="12" height="12" viewBox="0 0 12 12" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round">
                        <path d="M2 2l8 8M10 2l-8 8" />
                      </svg>
                    </button>
                  </div>
                </div>
              </div>

              {/* Risk Level Section — leads sidebar for security-first users */}
              {selectedAsset.is_ai_agent && (
                <div className="details-section">
                  <div className="section-title" style={{ display: 'flex', alignItems: 'center', gap: '0.375rem' }}>
                    <span>Risk Scoring Breakdown ({selectedAsset.risk_score}%)</span>
                    <span className="info-trigger" title="Risk score evaluates public endpoints, privileged service accounts, external API communication, and logging status.">ℹ️</span>
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', marginBottom: '1rem' }}>
                    <div style={{ fontSize: '0.85rem', color: selectedAsset.risk_score >= 70 ? 'var(--accent-rose)' : selectedAsset.risk_score >= 40 ? 'var(--accent-amber)' : 'var(--accent-emerald)', fontWeight: '600' }}>
                      {getRiskLabel(selectedAsset.risk_score).text} Risk Level
                    </div>
                    <div className="score-indicator-bar" style={{ height: '8px' }} role="meter" aria-valuenow={selectedAsset.risk_score} aria-valuemin={0} aria-valuemax={100} aria-label="Risk score">
                      <div className={`score-fill ${selectedAsset.risk_score >= 70 ? 'high' : selectedAsset.risk_score >= 40 ? 'medium' : 'low'}`} style={{ transform: `scaleX(${selectedAsset.risk_score / 100})` }}></div>
                    </div>
                  </div>
                  <div className="indicator-pill-list">
                    {selectedAsset.risk_reasons.length > 0 ? (
                      selectedAsset.risk_reasons.map((reason, idx) => (
                        <div key={idx} className={`indicator-pill ${selectedAsset.risk_score >= 70 ? 'danger' : 'warning'}`}>
                          <svg className="indicator-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                            <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
                            <line x1="12" y1="9" x2="12" y2="13" />
                            <line x1="12" y1="17" x2="12.01" y2="17" />
                          </svg>
                          <span>{reason}</span>
                        </div>
                      ))
                    ) : (
                      <div className="indicator-pill success">
                        <svg className="indicator-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                          <polyline points="20 6 9 17 4 12" />
                        </svg>
                        <span>No significant risks flagged</span>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Confidence Score Section */}
              {selectedAsset.is_ai_agent && (
                <div className="details-section">
                  <div className="section-title" style={{ display: 'flex', alignItems: 'center', gap: '0.375rem' }}>
                    <span>AI Confidence Breakdown ({selectedAsset.confidence_score}%)</span>
                    <span className="info-trigger" title="Confidence score evaluates environment variable patterns, framework fingerprints (e.g. LangChain, CrewAI), and Vertex AI infrastructure.">ℹ️</span>
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', marginBottom: '1rem' }}>
                    <div style={{ fontSize: '0.85rem', color: 'var(--accent-purple)', fontWeight: '600' }}>
                      {getConfidenceLabel(selectedAsset.confidence_score)}
                    </div>
                    <div className="score-indicator-bar" style={{ height: '8px' }} role="meter" aria-valuenow={selectedAsset.confidence_score} aria-valuemin={0} aria-valuemax={100} aria-label="AI confidence">
                      <div className="score-fill agent" style={{ transform: `scaleX(${selectedAsset.confidence_score / 100})` }}></div>
                    </div>
                  </div>
                  <div className="indicator-pill-list">
                    {selectedAsset.confidence_reasons.map((reason, idx) => (
                      <div key={idx} className="indicator-pill success">
                        <svg className="indicator-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                          <polyline points="20 6 9 17 4 12" />
                        </svg>
                        <span>{reason}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Resource Architecture Flow — improved connector styling */}
              <div className="details-section">
                <div className="section-title">Resource Architecture Flow</div>
                <div className="relationship-graph">
                  <div className="graph-node resource">
                    <span>☁️ {selectedAsset.name}</span>
                  </div>
                  <div className="graph-connector">
                    <div className="graph-connector-line" />
                    <div className="graph-connector-label">runs under</div>
                    <div className="graph-connector-line" />
                  </div>
                  <div className="graph-node sa">
                    <span style={{ fontSize: '0.75rem', wordBreak: 'break-all' }}>
                      👤 {selectedAsset.service_account ? selectedAsset.service_account.split('@')[0] : 'default-compute'}
                    </span>
                  </div>
                  {selectedAsset.is_ai_agent && (
                    <>
                      <div className="graph-connector">
                        <div className="graph-connector-line" />
                        <div className="graph-connector-label">invokes</div>
                        <div className="graph-connector-line" />
                      </div>
                      <div className="graph-node dest">
                        <span>🤖 LLM Endpoint / Vertex API</span>
                      </div>
                    </>
                  )}
                </div>
              </div>

              {/* Identity & Metadata */}
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

              {/* Environment Variables */}
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
                        borderRadius: 'var(--radius-xs)',
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
