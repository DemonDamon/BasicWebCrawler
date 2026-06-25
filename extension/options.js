import { pingHealthz } from "./lib/api.js";
import { getConfig, saveConfig } from "./lib/storage.js";

const form = document.getElementById("optionsForm");
const statusEl = document.getElementById("status");
const testBtn = document.getElementById("testBtn");

function setStatus(text, kind = "muted") {
  statusEl.textContent = text;
  statusEl.className = kind;
}

async function loadOptions() {
  const config = await getConfig();
  document.getElementById("apiBaseUrl").value = config.apiBaseUrl;
  document.getElementById("apiToken").value = config.apiToken;
  document.getElementById("clientId").value = config.clientId;
  document.getElementById("pollIntervalMinutes").value = config.pollIntervalMinutes;
  document.getElementById("minDelayMs").value = config.minDelayMs;
  document.getElementById("stopOnBlock").checked = Boolean(config.stopOnBlock);
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  try {
    await saveConfig({
      apiBaseUrl: document.getElementById("apiBaseUrl").value.trim(),
      apiToken: document.getElementById("apiToken").value.trim(),
      clientId: document.getElementById("clientId").value.trim() || "chrome-extension",
      pollIntervalMinutes: Number(document.getElementById("pollIntervalMinutes").value) || 1,
      minDelayMs: Number(document.getElementById("minDelayMs").value) || 8000,
      stopOnBlock: document.getElementById("stopOnBlock").checked,
    });
    setStatus("配置已保存", "success");
  } catch (error) {
    setStatus(error instanceof Error ? error.message : String(error), "error");
  }
});

testBtn.addEventListener("click", async () => {
  setStatus("测试中...", "muted");
  try {
    await saveConfig({
      apiBaseUrl: document.getElementById("apiBaseUrl").value.trim(),
      apiToken: document.getElementById("apiToken").value.trim(),
      clientId: document.getElementById("clientId").value.trim() || "chrome-extension",
      pollIntervalMinutes: Number(document.getElementById("pollIntervalMinutes").value) || 1,
      minDelayMs: Number(document.getElementById("minDelayMs").value) || 8000,
      stopOnBlock: document.getElementById("stopOnBlock").checked,
    });
    const ok = await pingHealthz();
    setStatus(ok ? "连接成功（healthz OK）" : "healthz 失败", ok ? "success" : "error");
  } catch (error) {
    setStatus(error instanceof Error ? error.message : String(error), "error");
  }
});

loadOptions();
