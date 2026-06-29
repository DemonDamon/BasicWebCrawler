const DEFAULT_CONFIG = {
  apiBaseUrl: "http://127.0.0.1:8787",
  apiToken: "",
  clientId: "chrome-extension",
  pollIntervalMinutes: 1,
  minDelayMs: 8000,
  autoCrawlEnabled: false,
  busy: false,
  stopOnBlock: true,
};

export async function getConfig() {
  const stored = await chrome.storage.sync.get(DEFAULT_CONFIG);
  return { ...DEFAULT_CONFIG, ...stored };
}

export async function saveConfig(partial) {
  await chrome.storage.sync.set(partial);
  return getConfig();
}

export function normalizeBaseUrl(url) {
  let normalized = (url || "").trim().replace(/\/+$/, "");
  // 0.0.0.0 是服务端 bind 地址，浏览器/插件无法作为客户端连接
  if (/^https?:\/\/0\.0\.0\.0(?::\d+)?$/i.test(normalized)) {
    normalized = normalized.replace("0.0.0.0", "127.0.0.1");
  }
  return normalized;
}
