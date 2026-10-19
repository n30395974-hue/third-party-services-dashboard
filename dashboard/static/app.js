// Services Dashboard: search across data exported to dataExports/.
// All exported data is untrusted (emails, messages), so it is only ever inserted
// with textContent / text nodes, never innerHTML.

"use strict";

const SERVICE_NAMES = { gmail: "Gmail", github: "GitHub", notion: "Notion", slack: "Slack" };
const SERVICE_ORDER = ["gmail", "github", "notion", "slack"];

const state = { items: [], selected: new Set(), query: "" };

const el = {
  query: document.getElementById("query"),
  filters: document.getElementById("service-filters"),
  status: document.getElementById("status"),
  warnings: document.getElementById("warnings"),
  results: document.getElementById("results"),
  empty: document.getElementById("empty"),
};

function serviceName(id) {
  return SERVICE_NAMES[id] || id.charAt(0).toUpperCase() + id.slice(1);
}

function make(tag, props = {}, children = []) {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(props)) {
    if (key === "text") node.textContent = value;
    else if (key === "dataset") Object.assign(node.dataset, value);
    else node.setAttribute(key, value);
  }
  for (const child of children) node.append(child);
  return node;
}

// ---------- search ----------

// 'joe "study group"' -> ["joe", "study group"]; every term must match.
function parseQuery(query) {
  const terms = [];
  const re = /"([^"]+)"|(\S+)/g;
  let match;
  while ((match = re.exec(query))) terms.push((match[1] || match[2]).toLowerCase());
  return terms;
}

function flatten(value) {
  if (value === null || value === undefined) return "";
  if (Array.isArray(value)) return value.map(flatten).filter(Boolean).join(", ");
  if (typeof value === "object" && "email" in value) return value.name ? `${value.name} <${value.email}>` : value.email;
  if (typeof value === "object") return Object.values(value).map(flatten).filter(Boolean).join(" ");
  return String(value);
}

function haystack(item) {
  if (!item._haystack) {
    item._haystack = [item.title, item.author, item.type, serviceName(item.service),
      item.content, flatten(item.fields)].join("\n").toLowerCase();
  }
  return item._haystack;
}

function matches(item, terms) {
  const text = haystack(item);
  return terms.every((term) => text.includes(term));
}

// ---------- rendering helpers ----------

function escapeRegExp(text) {
  return text.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

// Returns a fragment of text nodes and <mark> elements. Never parses HTML.
function highlight(text, terms) {
  const fragment = document.createDocumentFragment();
  if (!terms.length || !text) {
    fragment.append(text || "");
    return fragment;
  }
  const re = new RegExp(`(${terms.map(escapeRegExp).join("|")})`, "gi");
  text.split(re).forEach((part, index) => {
    if (!part) return;
    fragment.append(index % 2 ? make("mark", { text: part }) : part);
  });
  return fragment;
}

function bodyText(item) {
  // Drop the "# heading" line, which repeats the title.
  return item.content.replace(/^# .*\n+/, "").trim();
}

function snippet(item, terms) {
  const body = bodyText(item).replace(/^#+\s*/gm, "").replace(/\s+/g, " ");
  const lower = body.toLowerCase();
  let start = 0;
  for (const term of terms) {
    const at = lower.indexOf(term);
    if (at !== -1) { start = Math.max(0, at - 60); break; }
  }
  const cut = body.slice(start, start + 220);
  return (start > 0 ? "…" : "") + cut + (start + 220 < body.length ? "…" : "");
}

function formatTime(iso) {
  if (!iso) return "";
  const date = new Date(iso);
  return isNaN(date) ? iso : date.toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" });
}

function safeUrl(url) {
  try {
    const parsed = new URL(url);
    return parsed.protocol === "https:" || parsed.protocol === "http:" ? parsed.href : null;
  } catch {
    return null;
  }
}

function metadataTable(item) {
  const rows = [
    ["Service", serviceName(item.service)],
    ["Type", item.type],
    ["Author", item.author],
    ["Time", formatTime(item.time)],
    ["Downloaded", formatTime(item.exportedAt)],
    ["Local folder", item.folder],
  ];
  for (const [key, value] of Object.entries(item.fields || {})) rows.push([key, flatten(value) || "—"]);
  return make("table", { class: "meta" }, [
    make("tbody", {}, rows.map(([key, value]) =>
      make("tr", {}, [make("th", { scope: "row", text: key }), make("td", { text: value })]))),
  ]);
}

function card(item, terms) {
  const head = make("div", { class: "card-head" }, [
    make("span", { class: "badge", text: serviceName(item.service) }),
    make("span", { class: "type", text: item.type.replace("_", " ") }),
    make("time", { class: "time", datetime: item.time || "", text: formatTime(item.time) }),
  ]);
  const title = make("h3");
  title.append(highlight(item.title, terms));
  const author = make("p", { class: "author" });
  author.append(highlight(item.author, terms));
  const preview = make("p", { class: "snippet" });
  preview.append(highlight(snippet(item, terms), terms));

  const content = make("pre", { class: "content" });
  content.append(highlight(bodyText(item), terms));
  const details = make("details", {}, [make("summary", { text: "Full content & metadata" }), content, metadataTable(item)]);
  const url = safeUrl(item.url);
  if (url) {
    details.append(make("a", {
      class: "source-link", href: url, target: "_blank", rel: "noopener noreferrer",
      text: `Open in ${serviceName(item.service)} ↗`,
    }));
  }
  return make("li", { class: "card", dataset: { service: item.service } }, [head, title, author, preview, details]);
}

// ---------- page ----------

function servicesPresent() {
  const present = new Set(state.items.map((item) => item.service));
  return [...SERVICE_ORDER.filter((s) => present.has(s)), ...[...present].filter((s) => !SERVICE_ORDER.includes(s)).sort()];
}

function renderFilters(countsByService, totalMatches) {
  const chip = (id, label, count, pressed) => make("button", {
    type: "button", class: "chip", "aria-pressed": String(pressed),
    dataset: id ? { service: id } : {},
  }, [label, make("span", { class: "count", text: `(${count})` })]);

  const chips = [chip(null, "All services", totalMatches, state.selected.size === 0)];
  for (const id of servicesPresent()) {
    chips.push(chip(id, serviceName(id), countsByService[id] || 0, state.selected.has(id)));
  }
  el.filters.replaceChildren(...chips);
}

function render() {
  const terms = parseQuery(state.query);
  const matching = state.items.filter((item) => matches(item, terms));
  const counts = {};
  for (const item of matching) counts[item.service] = (counts[item.service] || 0) + 1;
  const shown = state.selected.size ? matching.filter((item) => state.selected.has(item.service)) : matching;

  renderFilters(counts, matching.length);
  el.results.replaceChildren(...shown.map((item) => card(item, terms)));

  const servicesShown = new Set(shown.map((item) => item.service)).size;
  const scope = state.selected.size ? [...state.selected].map(serviceName).join(", ") : "all services";
  if (!state.items.length) {
    el.status.textContent = "";
  } else if (terms.length) {
    el.status.textContent = `${shown.length} result${shown.length === 1 ? "" : "s"} from ${servicesShown} service${servicesShown === 1 ? "" : "s"} for “${state.query.trim()}” (searching ${scope})`;
  } else {
    el.status.textContent = `Showing ${shown.length} item${shown.length === 1 ? "" : "s"} from ${scope}, newest first`;
  }
}

el.filters.addEventListener("click", (event) => {
  const button = event.target.closest(".chip");
  if (!button) return;
  const id = button.dataset.service;
  if (!id) state.selected.clear();
  else if (state.selected.has(id)) state.selected.delete(id);
  else state.selected.add(id);
  render();
});

let debounce;
el.query.addEventListener("input", () => {
  clearTimeout(debounce);
  debounce = setTimeout(() => { state.query = el.query.value; render(); }, 120);
});

async function load() {
  try {
    const response = await fetch("/api/items", { cache: "no-store" });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const data = await response.json();
    state.items = data.items;
    if (data.warnings.length) {
      el.warnings.hidden = false;
      el.warnings.replaceChildren(make("strong", { text: "Some exported files could not be read:" }),
        make("ul", {}, data.warnings.map((w) => make("li", { text: w }))));
    }
    el.empty.hidden = state.items.length > 0;
    render();
  } catch (error) {
    el.status.textContent = `Could not load data from the local server: ${error.message}. Is "python3 dashboard/server.py" running?`;
  }
}

load();
