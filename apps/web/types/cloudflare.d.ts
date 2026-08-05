/**
 * Local fallback types for the Cloudflare bindings used by the web worker.
 * Production deployments replace these with Wrangler's generated bindings.
 */

interface Fetcher {
  fetch(input: RequestInfo, init?: RequestInit): Promise<Response>;
}

type D1Database = any;

declare module "cloudflare:workers" {
  export const env: { DB?: D1Database };
}
