import { integer, sqliteTable, text } from "drizzle-orm/sqlite-core";

export const workspaces = sqliteTable("workspaces", {
  id: text("id").primaryKey(),
  name: text("name").notNull(),
  description: text("description"),
  createdBy: text("created_by").notNull(),
  createdAt: text("created_at").notNull(),
  status: text("status").notNull(),
});

export const ingestBatches = sqliteTable("ingest_batches", {
  id: text("id").primaryKey(),
  workspaceId: text("workspace_id").notNull(),
  status: text("status").notNull(),
  createdAt: text("created_at").notNull(),
});

export const assets = sqliteTable("assets", {
  id: text("id").primaryKey(),
  workspaceId: text("workspace_id").notNull(),
  name: text("name").notNull(),
  versionId: text("version_id").notNull(),
  parentVersionId: text("parent_version_id"),
  contentHash: text("content_hash").notNull(),
  mimeType: text("mime_type").notNull(),
  formatKind: text("format_kind").notNull(),
  sizeBytes: integer("size_bytes").notNull(),
  storageKey: text("storage_key").notNull(),
  createdAt: text("created_at").notNull(),
  status: text("status").notNull(),
});

export const theses = sqliteTable("theses", {
  id: text("id").primaryKey(),
  projectId: text("project_id").notNull(),
  versionId: text("version_id").notNull(),
  payload: text("payload").notNull(),
  createdAt: text("created_at").notNull(),
});

export const thesisBuilds = sqliteTable("thesis_builds", {
  id: text("id").primaryKey(),
  thesisId: text("thesis_id").notNull(),
  versionId: text("version_id").notNull(),
  parentBuildId: text("parent_build_id"),
  payload: text("payload").notNull(),
  createdAt: text("created_at").notNull(),
});

export const toolRuns = sqliteTable("tool_runs", {
  id: text("id").primaryKey(),
  requestId: text("request_id").notNull().unique(),
  payload: text("payload").notNull(),
  createdAt: text("created_at").notNull(),
});
