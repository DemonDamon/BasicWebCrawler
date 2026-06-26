/**
 * 与 P5 wechat.json 对齐的前端解析器（轻量版）
 */
const WECHAT_SELECTORS = {
  title: ["meta[property='og:title']", "#activity-name"],
  account_name: ["#js_name", ".profile_nickname", "#js_profile_qrcode > div > strong"],
  content: ["#js_content"],
  cover: ["meta[property='og:image']"],
  publish_time: ["#publish_time", "meta[property='og:article:published_time']", "em#publish_time"],
};

function selectMeta(document, property) {
  const node = document.querySelector(`meta[property="${property}"]`);
  return node?.getAttribute("content")?.trim() || null;
}

function selectFirst(document, selectors) {
  for (const selector of selectors) {
    if (selector.startsWith("meta[property=")) {
      const match = selector.match(/meta\[property='([^']+)'\]/);
      if (match) {
        const value = selectMeta(document, match[1]);
        if (value) return value;
      }
      continue;
    }
    const node = document.querySelector(selector);
    const text = node?.textContent?.trim();
    if (text) return text;
  }
  return null;
}

function cleanContentHtml(node) {
  const clone = node.cloneNode(true);
  clone.querySelectorAll("script, style, iframe").forEach((el) => el.remove());
  return clone.innerHTML.trim();
}

function detectPageBlocked(document) {
  const bodyText = document.body?.innerText || "";
  if (/环境异常|完成验证|访问过于频繁|请在微信客户端打开/.test(bodyText)) {
    return "captcha_or_blocked";
  }
  if (!document.querySelector("#js_content")) {
    return "content_not_found";
  }
  return null;
}

function normalizeWechatUrl(url) {
  try {
    const parsed = new URL(url);
    const keep = ["__biz", "mid", "idx"];
    const params = new URLSearchParams();
    keep.forEach((key) => {
      const value = parsed.searchParams.get(key);
      if (value) params.set(key, value);
    });
    parsed.hash = "";
    parsed.search = params.toString() ? `?${params.toString()}` : "";
    parsed.protocol = "https:";
    return parsed.toString();
  } catch {
    return url;
  }
}

function extractBiz(url) {
  try {
    const parsed = new URL(url);
    const biz = parsed.searchParams.get("__biz");
    if (biz) return biz;
    return null;
  } catch {
    return null;
  }
}

/**
 * 从页面 script 标签中提取微信公众号的 __biz 值。
 *
 * 微信文章页实际格式（curl 验证）：
 *   var biz = "MzA3MzI4MjgzMw==" || ""   ← 主要格式，window.biz 引用此变量
 *   __biz = window.biz                    ← 后续赋值，不含实际值
 *   "__biz":"MzA3..."                     ← JSON 格式（部分页面）
 *   __biz=MzA3...&mid=...                 ← URL 参数格式（部分场景）
 */
function extractBizFromPage(document) {
  const scripts = document.querySelectorAll("script");
  for (const script of scripts) {
    const text = script.textContent || "";

    // 最常见：var biz = "MzA3MzI4MjgzMw==" || ""
    let m = text.match(/var\s+biz\s*=\s*["']([A-Za-z0-9+/=]{8,})["']/);
    if (m) return m[1];

    if (!text.includes("__biz")) continue;

    // JSON 键值：  "__biz":"MzA3..."
    m = text.match(/"__biz"\s*:\s*"([A-Za-z0-9+/=]{8,})"/);
    if (m) return m[1];

    // URL 参数字符串：  __biz=MzA3...& 或 __biz=MzA3..."
    m = text.match(/__biz=([A-Za-z0-9+/%]{8,})(?:&|"|')/);
    if (m) return decodeURIComponent(m[1]);
  }
  return null;
}

function parseWechatArticle(document, url) {
  const blockReason = detectPageBlocked(document);
  const errors = blockReason ? [blockReason] : [];

  const contentNode = document.querySelector("#js_content");
  let content_html = null;
  let content_text = null;
  if (contentNode) {
    content_html = cleanContentHtml(contentNode);
    content_text = contentNode.innerText.trim();
  } else if (!blockReason) {
    errors.push("content_not_found");
  }

  const title = selectFirst(document, WECHAT_SELECTORS.title);
  if (!title && !errors.includes("content_not_found")) {
    errors.push("title_not_found");
  }

  // 从当前 URL 或 og:url meta 提取 __biz；若均无则从页面脚本中提取
  const ogUrl = selectMeta(document, "og:url");
  const biz = extractBiz(url) || extractBiz(ogUrl || "") || extractBizFromPage(document);

  return {
    title,
    account_name: selectFirst(document, WECHAT_SELECTORS.account_name),
    url: url || window.location.href,
    canonical_url: normalizeWechatUrl(url || window.location.href),
    publish_time: selectFirst(document, WECHAT_SELECTORS.publish_time),
    cover_url: selectFirst(document, WECHAT_SELECTORS.cover),
    summary: content_text ? content_text.slice(0, 200) : null,
    content_html,
    content_text,
    biz,
    errors,
    ok: Boolean(title && content_html && errors.length === 0),
  };
}

// content script + tests
if (typeof globalThis !== "undefined") {
  globalThis.WechatArticleParser = {
    parseWechatArticle,
    normalizeWechatUrl,
    detectPageBlocked,
  };
}
