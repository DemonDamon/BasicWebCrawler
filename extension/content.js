/**
 * Content script：响应 background 的采集请求
 */
chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (message?.type !== "COLLECT_ARTICLE") {
    return false;
  }

  try {
    if (typeof WechatArticleParser === "undefined") {
      sendResponse({ ok: false, error: "解析器未加载，请刷新页面后重试" });
      return true;
    }
    const parsed = WechatArticleParser.parseWechatArticle(document, window.location.href);
    sendResponse({ ok: true, article: parsed });
  } catch (error) {
    sendResponse({
      ok: false,
      error: error instanceof Error ? error.message : String(error),
    });
  }
  return true;
});
