const state = { events: [], category: "全部", query: "", activeId: null };
const $ = (selector) => document.querySelector(selector);

const formatTime = (value) => {
  if (!value) return "时间未知";
  const date = new Date(value);
  return new Intl.DateTimeFormat("zh-CN", {
    month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit", hour12: false,
  }).format(date);
};

const appendText = (element, text) => {
  element.textContent = text || "暂无可靠信息";
  return element;
};

function renderMetrics(payload) {
  const articles = new Set(); const sources = new Set(); const regions = new Set();
  payload.events.forEach((event) => {
    (event.articles || []).forEach((article) => articles.add(article.canonical_url || article.url));
    (event.sources || []).forEach((source) => sources.add(source));
    (event.regions || []).forEach((region) => regions.add(region));
  });
  $("#metric-events").textContent = payload.events.length;
  $("#metric-articles").textContent = articles.size;
  $("#metric-sources").textContent = sources.size;
  $("#metric-regions").textContent = regions.size;
  $("#updated-at").textContent = `更新 ${formatTime(payload.generated_at)}`;
  $("#run-status").textContent = payload.run?.status === "success" ? "雷达运行正常" : "部分信源异常";
}

function renderFilters() {
  const categories = ["全部", ...new Set(state.events.map((event) => event.category))];
  const container = $("#category-filters"); container.replaceChildren();
  categories.forEach((category) => {
    const button = document.createElement("button");
    button.className = `filter-button${state.category === category ? " active" : ""}`;
    button.type = "button"; button.textContent = category;
    button.addEventListener("click", () => { state.category = category; renderFilters(); renderList(); });
    container.append(button);
  });
}

function matchingEvents() {
  const query = state.query.toLowerCase();
  return state.events.filter((event) => {
    const categoryMatch = state.category === "全部" || event.category === state.category;
    const haystack = [event.title, event.category, ...(event.sources || []), ...(event.keywords || [])].join(" ").toLowerCase();
    return categoryMatch && (!query || haystack.includes(query));
  });
}

function renderList() {
  const list = $("#event-list"); list.replaceChildren();
  const events = matchingEvents();
  if (!events.length) {
    const empty = document.createElement("div"); empty.className = "empty-list";
    empty.textContent = "没有符合当前筛选条件的事件"; list.append(empty); return;
  }
  events.forEach((event) => {
    const rank = state.events.findIndex((item) => item.event_id === event.event_id) + 1;
    const button = document.createElement("button");
    button.className = `event-card${state.activeId === event.event_id ? " active" : ""}`;
    button.type = "button";

    const rankElement = document.createElement("span"); rankElement.className = "rank"; rankElement.textContent = String(rank).padStart(2, "0");
    const main = document.createElement("div"); main.className = "card-main";
    const meta = document.createElement("div"); meta.className = "card-meta";
    const category = document.createElement("span"); category.className = "category"; category.textContent = event.category;
    const time = document.createElement("span"); time.textContent = formatTime(event.last_updated);
    const count = document.createElement("span"); count.textContent = `${event.article_count} 篇报道`;
    meta.append(category, time, count);
    const title = document.createElement("h3"); title.textContent = event.title;
    const source = document.createElement("p"); source.className = "source-line"; source.textContent = (event.sources || []).join(" · ");
    main.append(meta, title, source);
    const score = document.createElement("div"); score.className = "score score-ring"; score.style.setProperty("--score", event.score);
    const scoreInner = document.createElement("span");
    const strong = document.createElement("strong"); strong.textContent = Math.round(event.score);
    const small = document.createElement("small"); small.textContent = "HEAT";
    scoreInner.append(strong, small); score.append(scoreInner);
    button.append(rankElement, main, score);
    button.addEventListener("click", () => { state.activeId = event.event_id; renderList(); renderDetail(event); });
    list.append(button);
  });
}

function detailSection(title, content, list = false) {
  const section = document.createElement("section"); section.className = "detail-section";
  const heading = document.createElement("h4"); heading.textContent = title; section.append(heading);
  if (list) {
    const ul = document.createElement("ul");
    (Array.isArray(content) ? content : [content]).filter(Boolean).forEach((item) => {
      const li = document.createElement("li"); li.textContent = item; ul.append(li);
    });
    section.append(ul);
  } else {
    const paragraph = document.createElement("p"); paragraph.textContent = content || "暂无可靠信息"; section.append(paragraph);
  }
  return section;
}

function renderDetail(event) {
  const aside = $("#event-detail"); const content = document.createElement("div"); content.className = "detail-content";
  const topline = document.createElement("div"); topline.className = "detail-topline";
  const label = document.createElement("span"); label.textContent = `${event.category} · 热度 ${event.score}`;
  const close = document.createElement("button"); close.type = "button"; close.ariaLabel = "关闭详情"; close.textContent = "×";
  close.addEventListener("click", () => aside.classList.remove("open")); topline.append(label, close);
  const title = document.createElement("h3"); title.textContent = event.title;
  content.append(topline, title);
  const analysis = event.analysis || {};
  content.append(
    detailSection("发生了什么", analysis.what_happened),
    detailSection("为什么重要", analysis.why_important),
    detailSection("主要参与方", analysis.participants || [], true),
    detailSection("最新进展", analysis.latest_progress || [], true),
    detailSection("对中国可能影响", analysis.china_impact),
    detailSection("对金融市场可能影响", analysis.market_impact),
    detailSection("后续观察指标", analysis.watch_indicators || [], true),
  );
  const sources = document.createElement("section"); sources.className = "detail-section";
  const sourceHeading = document.createElement("h4"); sourceHeading.textContent = "信息来源";
  const links = document.createElement("div"); links.className = "source-links";
  (event.articles || []).forEach((article) => {
    const link = document.createElement("a"); link.href = article.url; link.target = "_blank"; link.rel = "noopener noreferrer";
    link.textContent = `${article.source} · ${article.title}`; links.append(link);
  });
  sources.append(sourceHeading, links); content.append(sources);
  const mode = document.createElement("span"); mode.className = "analysis-mode"; mode.textContent = analysis.analysis_mode || "自动分析"; content.append(mode);
  aside.replaceChildren(content); aside.classList.add("open");
}

async function init() {
  try {
    const response = await fetch("data/events.json", { cache: "no-store" });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const payload = await response.json();
    state.events = payload.events || [];
    renderMetrics(payload); renderFilters(); renderList();
    if (state.events[0] && window.innerWidth > 960) {
      state.activeId = state.events[0].event_id; renderList(); renderDetail(state.events[0]);
    }
  } catch (error) {
    const list = $("#event-list"); list.replaceChildren();
    const box = document.createElement("div"); box.className = "error-state";
    box.textContent = "暂时无法载入雷达数据，请稍后刷新。"; list.append(box);
    $("#run-status").textContent = "数据载入失败";
  }
}

$("#search").addEventListener("input", (event) => { state.query = event.target.value.trim(); renderList(); });
init();
