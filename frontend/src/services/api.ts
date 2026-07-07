export interface Asset {
  id: string;
  name: string;
  resource_type: string;
  region: string;
  runtime?: string;
  service_account?: string;
  env_vars: Record<string, string>;
  labels: Record<string, string>;
  is_ai_agent: boolean;
  confidence_score: number;
  confidence_reasons: string[];
  risk_score: number;
  risk_reasons: string[];
  last_seen: string;
}

export interface Scan {
  id: string;
  timestamp: string;
  status: string;
  assets_found: number;
  agents_found: number;
  error_message?: string;
}

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api";

export async function fetchAssets(): Promise<Asset[]> {
  const res = await fetch(`${API_BASE}/assets?limit=10000`);
  if (!res.ok) throw new Error("Failed to fetch assets");
  return res.json();
}

export async function fetchAgents(): Promise<Asset[]> {
  const res = await fetch(`${API_BASE}/agents?limit=10000`);
  if (!res.ok) throw new Error("Failed to fetch agents");
  return res.json();
}

export async function fetchAgentDetails(id: string): Promise<Asset> {
  const res = await fetch(`${API_BASE}/agents/${id}`);
  if (!res.ok) throw new Error("Failed to fetch agent details");
  return res.json();
}

export async function triggerScan(): Promise<Scan> {
  const res = await fetch(`${API_BASE}/scan`, { method: "POST" });
  if (!res.ok) throw new Error("Failed to trigger scan");
  return res.json();
}

export async function fetchScanHistory(): Promise<Scan[]> {
  const res = await fetch(`${API_BASE}/scan/history`);
  if (!res.ok) throw new Error("Failed to fetch scan history");
  return res.json();
}
