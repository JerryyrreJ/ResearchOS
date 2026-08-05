import { DATA_CONNECTORS, connectorById, type DataConnectorDefinition } from "../lib/connector-catalog";

export interface ConnectorEnv {
  DB: D1Database;
  CONNECTOR_ENCRYPTION_KEY?: string;
}

type ConnectorRecord = {
  connector_id: string;
  encrypted_key: string | null;
  iv: string | null;
  enabled: number;
  updated_at: string;
  last_test_status: string | null;
  last_test_at: string | null;
};

const json = (value: unknown, status = 200) => new Response(JSON.stringify(value), {
  status,
  headers: { "content-type": "application/json; charset=utf-8", "cache-control": "no-store" },
});

const bytesToBase64 = (bytes: Uint8Array) => btoa(String.fromCharCode(...bytes));
const base64ToBytes = (value: string) => Uint8Array.from(atob(value), (char) => char.charCodeAt(0));

async function cryptoKey(secret: string) {
  if (secret.length < 24) throw new Error("Connector encryption is not configured");
  const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(secret));
  return crypto.subtle.importKey("raw", digest, "AES-GCM", false, ["encrypt", "decrypt"]);
}

async function encryptSecret(value: string, masterSecret: string) {
  const iv = crypto.getRandomValues(new Uint8Array(12));
  const encrypted = await crypto.subtle.encrypt({ name: "AES-GCM", iv }, await cryptoKey(masterSecret), new TextEncoder().encode(value));
  return { encrypted: bytesToBase64(new Uint8Array(encrypted)), iv: bytesToBase64(iv) };
}

async function decryptSecret(record: ConnectorRecord, masterSecret: string) {
  if (!record.encrypted_key || !record.iv) return "";
  const clear = await crypto.subtle.decrypt(
    { name: "AES-GCM", iv: base64ToBytes(record.iv) },
    await cryptoKey(masterSecret),
    base64ToBytes(record.encrypted_key),
  );
  return new TextDecoder().decode(clear);
}

async function ensureConnectorSchema(db: D1Database) {
  await db.prepare(`CREATE TABLE IF NOT EXISTS data_connectors (
    connector_id TEXT PRIMARY KEY,
    encrypted_key TEXT,
    iv TEXT,
    enabled INTEGER NOT NULL DEFAULT 0,
    updated_at TEXT NOT NULL,
    last_test_status TEXT,
    last_test_at TEXT
  )`).run();
}

const publicConnector = (definition: DataConnectorDefinition, record?: ConnectorRecord | null) => ({
  ...definition,
  configured: definition.keyRequired ? Boolean(record?.encrypted_key) : Boolean(record?.enabled),
  enabled: Boolean(record?.enabled),
  apiKeyMasked: record?.encrypted_key ? "••••••••" : null,
  lastTestStatus: record?.last_test_status ?? null,
  lastTestAt: record?.last_test_at ?? null,
  secretStorage: definition.keyRequired ? "server-encrypted" : "not-required",
});

async function recordFor(db: D1Database, connectorId: string) {
  return db.prepare("SELECT * FROM data_connectors WHERE connector_id = ?").bind(connectorId).first<ConnectorRecord>();
}

const bounded = (value: unknown, fallback: number, max: number) => Math.min(Math.max(Number(value) || fallback, 1), max);
const clean = (value: unknown, fallback: string) => String(value || fallback).trim().slice(0, 120);

async function upstream(url: string, init?: RequestInit) {
  const response = await fetch(url, { ...init, signal: AbortSignal.timeout(20_000), headers: { Accept: "application/json", ...init?.headers } });
  const payload = await response.json().catch(() => null) as Record<string, unknown> | unknown[] | null;
  if (!response.ok) throw new Error(`Upstream returned HTTP ${response.status}`);
  if (!payload) throw new Error("Upstream returned an invalid response");
  return payload;
}

async function execute(definition: DataConnectorDefinition, apiKey: string, parameters: Record<string, unknown>) {
  switch (definition.id) {
    case "fred": {
      const seriesId = clean(parameters.series_id, "GDP");
      const limit = bounded(parameters.limit, 10, 100);
      const url = new URL("https://api.stlouisfed.org/fred/series/observations");
      Object.entries({ series_id: seriesId, api_key: apiKey, file_type: "json", sort_order: "desc", limit: String(limit) }).forEach(([key, value]) => url.searchParams.set(key, value));
      const payload = await upstream(url.toString()) as { observations?: unknown[]; error_message?: string };
      if (!payload.observations) throw new Error(payload.error_message || "FRED returned no observations");
      return { dataset: seriesId, rows: payload.observations, metadata: { source: "FRED", limit } };
    }
    case "tushare": {
      const apiName = clean(parameters.api_name, "trade_cal");
      const allowed = new Set(["trade_cal", "daily", "stock_basic", "daily_basic", "income", "balancesheet", "cashflow", "moneyflow"]);
      if (!allowed.has(apiName)) throw new Error("This Tushare operation is not enabled in the reviewed connector");
      const params = { ...parameters }; delete params.api_name; delete params.limit;
      const payload = await upstream("https://api.tushare.pro", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ api_name: apiName, token: apiKey, params, fields: "" }) }) as { code?: number; msg?: string; data?: { fields?: string[]; items?: unknown[][] } };
      if (payload.code !== 0 || !payload.data) throw new Error(payload.msg || "Tushare rejected the request");
      const fields = payload.data.fields ?? [];
      const rows = (payload.data.items ?? []).slice(0, 100).map((item) => Object.fromEntries(fields.map((field, index) => [field, item[index]])));
      return { dataset: apiName, rows, metadata: { source: "Tushare", truncated: (payload.data.items?.length ?? 0) > 100 } };
    }
    case "alpha-vantage": {
      const fn = clean(parameters.function, "TIME_SERIES_DAILY");
      const allowed = new Set(["TIME_SERIES_DAILY", "GLOBAL_QUOTE", "OVERVIEW", "CPI", "REAL_GDP", "TREASURY_YIELD", "NEWS_SENTIMENT"]);
      if (!allowed.has(fn)) throw new Error("This Alpha Vantage function is not enabled in the reviewed connector");
      const url = new URL("https://www.alphavantage.co/query");
      for (const [key, value] of Object.entries({ ...parameters, function: fn, apikey: apiKey })) if (value !== undefined) url.searchParams.set(key, String(value).slice(0, 160));
      const payload = await upstream(url.toString()) as Record<string, unknown>;
      if (payload["Error Message"] || payload.Note || payload.Information) throw new Error(String(payload["Error Message"] || payload.Note || payload.Information));
      return { dataset: fn, rows: payload, metadata: { source: "Alpha Vantage" } };
    }
    case "nasdaq-data-link": {
      const dataset = clean(parameters.dataset, "FRED/GDP").replace(/[^A-Za-z0-9_./-]/g, "");
      const limit = bounded(parameters.limit, 10, 100);
      const url = new URL(`https://data.nasdaq.com/api/v3/datasets/${dataset}.json`);
      url.searchParams.set("api_key", apiKey); url.searchParams.set("limit", String(limit)); url.searchParams.set("order", "desc");
      const payload = await upstream(url.toString()) as { dataset?: Record<string, unknown>; quandl_error?: { message?: string } };
      if (!payload.dataset) throw new Error(payload.quandl_error?.message || "Nasdaq Data Link returned no dataset");
      return { dataset, rows: payload.dataset.data ?? [], metadata: { source: "Nasdaq Data Link", columns: payload.dataset.column_names } };
    }
    case "world-bank": {
      const country = clean(parameters.country, "US").replace(/[^A-Za-z0-9-]/g, "");
      const indicator = clean(parameters.indicator, "NY.GDP.MKTP.CD").replace(/[^A-Za-z0-9.]/g, "");
      const payload = await upstream(`https://api.worldbank.org/v2/country/${country}/indicator/${indicator}?format=json&per_page=20`) as unknown[];
      return { dataset: `${country}/${indicator}`, rows: payload[1] ?? [], metadata: { source: "World Bank", page: payload[0] ?? null } };
    }
    case "treasury": {
      const payload = await upstream("https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v2/accounting/od/debt_to_penny?page%5Bsize%5D=20&sort=-record_date") as { data?: unknown[]; meta?: unknown };
      return { dataset: "debt_to_penny", rows: payload.data ?? [], metadata: { source: "U.S. Treasury", meta: payload.meta } };
    }
    case "nyfed": {
      const payload = await upstream("https://markets.newyorkfed.org/api/rates/all/latest.json") as { refRates?: unknown[] };
      return { dataset: "reference-rates", rows: payload.refRates ?? [], metadata: { source: "New York Fed" } };
    }
    case "yahoo-finance": {
      const symbol = clean(parameters.symbol, "NVDA").replace(/[^A-Za-z0-9.^=-]/g, "");
      const range = clean(parameters.range, "1mo").replace(/[^0-9a-z]/gi, "");
      const payload = await upstream(`https://query1.finance.yahoo.com/v8/finance/chart/${symbol}?range=${range}&interval=1d`) as { chart?: { result?: unknown[]; error?: { description?: string } } };
      if (!payload.chart?.result) throw new Error(payload.chart?.error?.description || "Yahoo Finance returned no chart data");
      return { dataset: symbol, rows: payload.chart.result, metadata: { source: "Yahoo Finance", range, unofficial: true } };
    }
    default:
      throw new Error("This connector requires a separate bridge or institutional license");
  }
}

export async function handleConnectorApi(request: Request, env: ConnectorEnv): Promise<Response | null> {
  const url = new URL(request.url);
  if (!url.pathname.startsWith("/api/v1/connectors")) return null;
  if (!env.DB) return json({ detail: "Connector storage is unavailable" }, 503);
  await ensureConnectorSchema(env.DB);
  const path = url.pathname.slice("/api/v1/connectors".length);
  const method = request.method;

  if ((path === "" || path === "/") && method === "GET") {
    const result = await env.DB.prepare("SELECT * FROM data_connectors").all<ConnectorRecord>();
    const records = new Map((result.results ?? []).map((item) => [item.connector_id, item]));
    return json({ connectors: DATA_CONNECTORS.map((item) => publicConnector(item, records.get(item.id))), secretPolicy: { browserStorage: false, encryptedAtRest: true, returnedToClient: false } });
  }

  const match = path.match(/^\/([^/]+)(?:\/(test|query))?$/);
  if (!match) return json({ detail: "Connector route not found" }, 404);
  const connectorId = decodeURIComponent(match[1]);
  const action = match[2];
  const definition = connectorById(connectorId);
  if (!definition) return json({ detail: "Unknown data connector" }, 404);

  if (!action && method === "PUT") {
    if (definition.runtime !== "native") return json({ detail: "This source requires a reviewed bridge or institutional license" }, 409);
    const body = await request.json<{ apiKey?: string; enabled?: boolean }>();
    const existing = await recordFor(env.DB, connectorId);
    let encrypted = existing?.encrypted_key ?? null;
    let iv = existing?.iv ?? null;
    if (definition.keyRequired && body.apiKey?.trim()) {
      if (!env.CONNECTOR_ENCRYPTION_KEY) return json({ detail: "Server-side connector encryption is not configured" }, 503);
      const sealed = await encryptSecret(body.apiKey.trim(), env.CONNECTOR_ENCRYPTION_KEY);
      encrypted = sealed.encrypted; iv = sealed.iv;
    }
    if (definition.keyRequired && !encrypted) return json({ detail: "API key is required" }, 422);
    const updatedAt = new Date().toISOString();
    await env.DB.prepare("INSERT INTO data_connectors VALUES (?, ?, ?, ?, ?, ?, ?) ON CONFLICT(connector_id) DO UPDATE SET encrypted_key=excluded.encrypted_key, iv=excluded.iv, enabled=excluded.enabled, updated_at=excluded.updated_at")
      .bind(connectorId, encrypted, iv, body.enabled === false ? 0 : 1, updatedAt, existing?.last_test_status ?? null, existing?.last_test_at ?? null).run();
    return json(publicConnector(definition, await recordFor(env.DB, connectorId)));
  }

  if (!action && method === "DELETE") {
    await env.DB.prepare("DELETE FROM data_connectors WHERE connector_id = ?").bind(connectorId).run();
    return json(publicConnector(definition, null));
  }

  if ((action === "test" || action === "query") && method === "POST") {
    if (definition.runtime !== "native") return json({ detail: "This source is catalogued but not executable in the web runtime" }, 409);
    const record = await recordFor(env.DB, connectorId);
    if (!record?.enabled) return json({ detail: "Connector is not enabled" }, 409);
    let apiKey = "";
    if (definition.keyRequired) {
      if (!env.CONNECTOR_ENCRYPTION_KEY || !record.encrypted_key) return json({ detail: "Connector key is not configured" }, 422);
      try { apiKey = await decryptSecret(record, env.CONNECTOR_ENCRYPTION_KEY); } catch { return json({ detail: "Stored connector key cannot be decrypted" }, 500); }
    }
    const body = action === "query" ? await request.json<Record<string, unknown>>() : definition.sampleQuery;
    try {
      const started = Date.now();
      const result = await execute(definition, apiKey, body);
      const testedAt = new Date().toISOString();
      await env.DB.prepare("UPDATE data_connectors SET last_test_status = 'CONNECTED', last_test_at = ? WHERE connector_id = ?").bind(testedAt, connectorId).run();
      return json({ ok: true, connectorId, latencyMs: Date.now() - started, ...result });
    } catch (error) {
      const testedAt = new Date().toISOString();
      await env.DB.prepare("UPDATE data_connectors SET last_test_status = 'FAILED', last_test_at = ? WHERE connector_id = ?").bind(testedAt, connectorId).run();
      return json({ detail: error instanceof Error ? error.message : "Connector request failed" }, 502);
    }
  }

  return json({ detail: "Connector route not found" }, 404);
}
