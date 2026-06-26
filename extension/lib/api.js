import { getConfig, normalizeBaseUrl } from "./storage.js";

const PLUGIN_VERSION = chrome.runtime.getManifest().version;

export class ApiError extends Error {
  constructor(message, status, body) {
    super(message);
    this.status = status;
    this.body = body;
  }
}

async function buildHeaders(extra = {}) {
  const config = await getConfig();
  return {
    "Content-Type": "application/json",
    "X-API-Token": config.apiToken || "",
    "X-Client-Id": config.clientId || "chrome-extension",
    "X-Plugin-Version": PLUGIN_VERSION,
    ...extra,
  };
}

export async function apiFetch(path, options = {}) {
  const config = await getConfig();
  const base = normalizeBaseUrl(config.apiBaseUrl);
  if (!base) {
    throw new ApiError("API Base URL 未配置", 0, null);
  }
  if (!config.apiToken) {
    throw new ApiError("API Token 未配置", 0, null);
  }

  const response = await fetch(`${base}${path}`, {
    ...options,
    headers: await buildHeaders(options.headers),
  });

  const text = await response.text();
  let body = null;
  if (text) {
    try {
      body = JSON.parse(text);
    } catch {
      body = text;
    }
  }

  if (!response.ok) {
    const raw = typeof body === "object" && body?.detail ? body.detail : null;
    let detail;
    if (Array.isArray(raw)) {
      // FastAPI 422 validation errors: [{loc, msg, type}, ...]
      detail = raw.map((e) => (typeof e === "object" ? e.msg || JSON.stringify(e) : String(e))).join("; ");
    } else if (raw !== null && raw !== undefined) {
      detail = typeof raw === "string" ? raw : JSON.stringify(raw);
    } else {
      detail = `HTTP ${response.status}`;
    }
    throw new ApiError(detail, response.status, body);
  }

  return body;
}

export async function ingestArticle(article, taskMeta = {}) {
  return apiFetch("/api/articles", {
    method: "POST",
    body: JSON.stringify({
      ...article,
      org_id: taskMeta.org_id ?? null,
      account_id: taskMeta.account_id ?? null,
      candidate_id: taskMeta.candidate_id ?? null,
      source: taskMeta.source || "extension",
    }),
  });
}

export async function fetchNextTask(priority = null) {
  const query = priority ? `?priority=${encodeURIComponent(priority)}` : "";
  return apiFetch(`/api/crawl/tasks/next${query}`, { method: "GET" });
}

export async function markTaskSuccess(taskId) {
  return apiFetch(`/api/crawl/tasks/${taskId}/success`, { method: "POST", body: "{}" });
}

export async function markTaskFailed(taskId, failReason) {
  return apiFetch(`/api/crawl/tasks/${taskId}/failed`, {
    method: "POST",
    body: JSON.stringify({ fail_reason: failReason || "unknown" }),
  });
}

export async function pingHealthz() {
  const config = await getConfig();
  const base = normalizeBaseUrl(config.apiBaseUrl);
  const response = await fetch(`${base}/healthz`);
  return response.ok;
}
