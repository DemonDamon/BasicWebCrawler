import { getConfig } from "./lib/storage.js";

const statusEl = document.getElementById("status");
const collectBtn = document.getElementById("collectBtn");
const autoBtn = document.getElementById("autoBtn");
const optionsLink = document.getElementById("optionsLink");

optionsLink.addEventListener("click", (event) => {
  event.preventDefault();
  chrome.runtime.openOptionsPage();
});

function setStatus(text, kind = "muted") {
  statusEl.textContent = text;
  statusEl.className = kind;
}

async function refreshAutoButton() {
  const config = await getConfig();
  autoBtn.textContent = config.autoCrawlEnabled ? "停止自动采集" : "开始自动采集";
}

collectBtn.addEventListener("click", async () => {
  collectBtn.disabled = true;
  setStatus("采集中...", "muted");
  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (!tab?.url?.includes("mp.weixin.qq.com")) {
      throw new Error("当前页不是微信公众号文章");
    }

    const response = await chrome.runtime.sendMessage({ type: "COLLECT_ACTIVE_TAB" });
    if (!response?.ok) {
      throw new Error(response?.error || "采集失败");
    }
    const created = response.result?.ingest?.created;
    const title = response.result?.article?.title || "文章";
    setStatus(
      created ? `已入库：${title}` : `重复文章：${title}`,
      created ? "success" : "muted"
    );
  } catch (error) {
    const msg = error instanceof Error ? error.message : String(error);
    const friendly = /Receiving end does not exist|Could not establish/i.test(msg)
      ? "请先刷新微信文章页，再点击采集"
      : msg;
    setStatus(friendly, "error");
  } finally {
    collectBtn.disabled = false;
  }
});

autoBtn.addEventListener("click", async () => {
  autoBtn.disabled = true;
  try {
    const config = await getConfig();
    const enabled = !config.autoCrawlEnabled;
    const response = await chrome.runtime.sendMessage({
      type: "SET_AUTO_CRAWL",
      enabled,
    });
    if (!response?.ok) {
      throw new Error(response?.error || "切换自动采集失败");
    }
    setStatus(enabled ? "自动采集已开启" : "自动采集已停止", "success");
    await refreshAutoButton();
  } catch (error) {
    setStatus(error instanceof Error ? error.message : String(error), "error");
  } finally {
    autoBtn.disabled = false;
  }
});

refreshAutoButton();
