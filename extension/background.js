import {
  ApiError,
  fetchNextTask,
  importCandidates,
  ingestArticle,
  markTaskFailed,
  markTaskSuccess,
} from "./lib/api.js";
import { getConfig, saveConfig } from "./lib/storage.js";

const AUTO_ALARM = "wechat-collector-auto-poll";
let manualCollectInFlight = false;

chrome.runtime.onInstalled.addListener(async () => {
  const config = await getConfig();
  await syncAutoAlarm(config.autoCrawlEnabled, config.pollIntervalMinutes);
});

chrome.storage.onChanged.addListener((changes, area) => {
  if (area !== "sync") return;
  if (changes.autoCrawlEnabled || changes.pollIntervalMinutes) {
    chrome.storage.sync.get(["autoCrawlEnabled", "pollIntervalMinutes"]).then((cfg) => {
      syncAutoAlarm(cfg.autoCrawlEnabled, cfg.pollIntervalMinutes || 1);
    });
  }
});

chrome.alarms.onAlarm.addListener((alarm) => {
  if (alarm.name === AUTO_ALARM) {
    processAutoQueue().catch((error) => {
      console.warn("[wechat-collector] auto poll failed:", error);
    });
  }
});

chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (message?.type === "COLLECT_ACTIVE_TAB") {
    collectActiveTab()
      .then((result) => sendResponse({ ok: true, result }))
      .catch((error) =>
        sendResponse({
          ok: false,
          error: error instanceof Error ? error.message : String(error),
        })
      );
    return true;
  }

  if (message?.type === "PROCESS_AUTO_ONCE") {
    processAutoQueue()
      .then((result) => sendResponse({ ok: true, result }))
      .catch((error) =>
        sendResponse({
          ok: false,
          error: error instanceof Error ? error.message : String(error),
        })
      );
    return true;
  }

  if (message?.type === "ENQUEUE_FROM_TAB") {
    enqueueFromTab(message.tabId)
      .then((result) => sendResponse({ ok: true, result }))
      .catch((error) =>
        sendResponse({
          ok: false,
          error: error instanceof Error ? error.message : String(error),
        })
      );
    return true;
  }

  if (message?.type === "SET_AUTO_CRAWL") {
    saveConfig({ autoCrawlEnabled: Boolean(message.enabled) })
      .then(async (cfg) => {
        await syncAutoAlarm(cfg.autoCrawlEnabled, cfg.pollIntervalMinutes);
        sendResponse({ ok: true, autoCrawlEnabled: cfg.autoCrawlEnabled });
      })
      .catch((error) =>
        sendResponse({
          ok: false,
          error: error instanceof Error ? error.message : String(error),
        })
      );
    return true;
  }

  return false;
});

async function syncAutoAlarm(enabled, pollIntervalMinutes) {
  await chrome.alarms.clear(AUTO_ALARM);
  if (enabled) {
    const minutes = Math.max(0.5, Number(pollIntervalMinutes) || 1);
    chrome.alarms.create(AUTO_ALARM, { periodInMinutes: minutes });
  }
}

async function collectActiveTab(taskMeta = {}) {
  if (manualCollectInFlight) {
    throw new Error("已有采集任务进行中");
  }
  manualCollectInFlight = true;
  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (!tab?.id) {
      throw new Error("未找到当前标签页");
    }
    return await collectFromTab(tab.id, taskMeta);
  } finally {
    manualCollectInFlight = false;
  }
}

async function collectFromTab(tabId, taskMeta = {}) {
  const response = await chrome.tabs.sendMessage(tabId, { type: "COLLECT_ARTICLE" });
  if (!response?.ok) {
    throw new Error(response?.error || "页面采集失败");
  }

  const article = response.article;
  if (!article?.ok) {
    const reason = (article?.errors || []).join(", ") || "parse_failed";
    if (taskMeta.candidate_id) {
      await markTaskFailed(taskMeta.candidate_id, reason);
    }
    throw new Error(`解析失败: ${reason}`);
  }

  const ingestPayload = {
    title: article.title,
    account_name: article.account_name,
    url: article.url,
    canonical_url: article.canonical_url,
    publish_time: normalizePublishTime(article.publish_time) || null,
    cover_url: article.cover_url,
    summary: article.summary,
    content_html: article.content_html,
    content_text: article.content_text,
    biz: article.biz || null,
  };

  try {
    const ingestResult = await ingestArticle(ingestPayload, taskMeta);
    if (taskMeta.candidate_id) {
      await markTaskSuccess(taskMeta.candidate_id);
    }
    return { article: ingestPayload, ingest: ingestResult };
  } catch (error) {
    const reason = error instanceof ApiError ? error.message : String(error);
    if (taskMeta.candidate_id) {
      await markTaskFailed(taskMeta.candidate_id, reason);
    }
    throw error;
  }
}

function waitForTabComplete(tabId, timeoutMs = 30000) {
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => {
      chrome.tabs.onUpdated.removeListener(listener);
      reject(new Error("页面加载超时"));
    }, timeoutMs);

    function listener(updatedTabId, info) {
      if (updatedTabId === tabId && info.status === "complete") {
        clearTimeout(timer);
        chrome.tabs.onUpdated.removeListener(listener);
        resolve();
      }
    }

    chrome.tabs.onUpdated.addListener(listener);
  });
}

async function sleep(ms) {
  await new Promise((resolve) => setTimeout(resolve, ms));
}

/**
 * 把各种微信日期格式统一转成 ISO 8601 字符串，方便服务端 Pydantic 解析。
 * 支持：
 *   "2026年6月25日"  → "2026-06-25T00:00:00"
 *   "2026年6月25日 10:30"  → "2026-06-25T10:30:00"
 *   "2026-06-25"    → 原样保留
 *   ISO 格式        → 原样保留
 */
function normalizePublishTime(raw) {
  if (!raw) return null;
  const chinese = raw.match(/(\d{4})年\s*(\d{1,2})月\s*(\d{1,2})日(?:\s+(\d{1,2}):(\d{2}))?/);
  if (chinese) {
    const [, y, m, d, hh = "00", mm = "00"] = chinese;
    return `${y}-${String(m).padStart(2, "0")}-${String(d).padStart(2, "0")}T${String(hh).padStart(2, "0")}:${mm}:00`;
  }
  return raw;
}

async function processAutoQueue() {
  const config = await getConfig();
  if (!config.autoCrawlEnabled) {
    return { skipped: "auto_disabled" };
  }
  if (config.busy) {
    return { skipped: "busy" };
  }

  await saveConfig({ busy: true });
  let openedTabId = null;

  try {
    const task = await fetchNextTask();
    if (!task) {
      return { skipped: "no_task" };
    }

    const tab = await chrome.tabs.create({ url: task.url, active: false });
    openedTabId = tab.id;
    await waitForTabComplete(openedTabId);
    await sleep(1500);

    try {
      const result = await collectFromTab(openedTabId, {
        candidate_id: task.id,
        org_id: task.org_id,
        account_id: task.account_id,
        source: "extension_auto",
      });
      await sleep(config.minDelayMs || 8000);
      return { ok: true, task, result };
    } catch (error) {
      const reason = error instanceof ApiError ? error.message : String(error);
      if (task?.id && !(error instanceof ApiError && error.message.includes("解析失败"))) {
        await markTaskFailed(task.id, reason);
      }
      if (config.stopOnBlock && /captcha|blocked|403|验证|环境异常/i.test(reason)) {
        await saveConfig({ autoCrawlEnabled: false });
        await syncAutoAlarm(false, config.pollIntervalMinutes);
      }
      throw error;
    }
  } finally {
    if (openedTabId) {
      try {
        await chrome.tabs.remove(openedTabId);
      } catch {
        // tab may already be closed
      }
    }
    await saveConfig({ busy: false });
  }
}

  /**
   * 从 freewechat.com 列表页提取所有微信文章链接并批量入队。
   * freewechat.com 的列表页链接格式有两种：
   *   1. 直接的 mp.weixin.qq.com 文章链接
   *   2. freewechat.com 内部文章链接 /a/{biz}/{id}/1
   * 两种都收集并入队。
   */
async function enqueueFromTab(tabId) {
  const [{ result: urls }] = await chrome.scripting.executeScript({
    target: { tabId },
    func: () => {
      const seen = new Set();
      const out = [];

      function addUrl(href) {
        const clean = (href || "").split("#")[0].trim();
        if (!clean || seen.has(clean)) return;
        seen.add(clean);
        out.push(clean);
      }

      // 1. 直接在链接 href 中找 mp.weixin.qq.com
      for (const a of document.querySelectorAll("a[href]")) {
        const href = a.href || "";
        if (/mp\.weixin\.qq\.com\/s/i.test(href)) {
          addUrl(href);
        }
        // freewechat.com 内部文章链接
        if (/freewechat\.com\/a\/[^/]+\/\d+\/\d/i.test(href)) {
          addUrl(href);
        }
      }

      // 2. 在 data-* 属性中搜 mp.weixin.qq.com（搜狗常用 data-url 等）
      for (const el of document.querySelectorAll("[data-url],[data-link],[data-href]")) {
        for (const attr of ["data-url", "data-link", "data-href"]) {
          const val = el.getAttribute(attr) || "";
          if (/mp\.weixin\.qq\.com\/s/i.test(val)) addUrl(val);
        }
      }

      // 3. 全文搜索页面 HTML，正则提取所有 mp.weixin.qq.com/s/... 链接
      // 搜狗等页面把 URL 藏在 JS 变量或 JSON 数据里
      const html = document.documentElement.innerHTML;
      const re = /https?:\/\/mp\.weixin\.qq\.com\/s\/[A-Za-z0-9_\-]+/gi;
      let m;
      while ((m = re.exec(html)) !== null) {
        addUrl(m[0]);
      }

      return out;
    },
  });

  if (!urls || urls.length === 0) {
    throw new Error("当前页面未找到微信文章链接（已搜索链接、data属性、页面全文）");
  }

  const result = await importCandidates(urls, "sogou_search");
  return { found: urls.length, ...result };
}
