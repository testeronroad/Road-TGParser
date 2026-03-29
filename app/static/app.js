const $ = (id) => document.getElementById(id);

let searchTimer = null;
let categoriesCache = [];

function showToast(text, isError = false) {
  const t = $("toast");
  t.textContent = text;
  t.hidden = false;
  t.classList.toggle("error", isError);
  clearTimeout(t._hide);
  t._hide = setTimeout(() => {
    t.hidden = true;
  }, 4500);
}

function badgeClass(categoryId) {
  if (categoryId === "crypto") return "badge badge-crypto";
  if (categoryId === "scam") return "badge badge-scam";
  return "badge";
}

function categorySelectClass(categoryId) {
  return `cat-select ${badgeClass(categoryId)}`;
}

function escapeAttr(s) {
  return String(s ?? "")
    .replace(/&/g, "&amp;")
    .replace(/"/g, "&quot;")
    .replace(/</g, "&lt;");
}

function categoryOptionsHtml(selectedId, fallbackName) {
  const sel = String(selectedId ?? "");
  const known = new Set(categoriesCache.map((c) => c.id));
  let html = "";
  if (sel && !known.has(sel)) {
    html += `<option value="${escapeAttr(sel)}" selected>${escapeHtml(fallbackName || sel)}</option>`;
  }
  for (const c of categoriesCache) {
    const isSel = c.id === sel;
    html += `<option value="${escapeAttr(c.id)}"${isSel ? " selected" : ""}>${escapeHtml(c.name)}</option>`;
  }
  return html;
}

async function fetchJSON(url, options) {
  const res = await fetch(url, options);
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const msg = data.detail || data.message || res.statusText || "Ошибка запроса";
    throw new Error(typeof msg === "string" ? msg : JSON.stringify(msg));
  }
  return data;
}

async function loadHealth() {
  const pill = $("healthPill");
  const dot = $("healthDot");
  const text = $("healthText");
  try {
    const h = await fetchJSON("/api/health");
    pill.classList.remove("ok", "warn", "bad");
    if (h.telegram_authorized) {
      pill.classList.add("ok");
      text.textContent = "Telegram подключён";
    } else {
      pill.classList.add("warn");
      text.textContent = "Нет сессии Telegram";
    }
  } catch {
    pill.classList.remove("ok", "warn", "bad");
    pill.classList.add("bad");
    text.textContent = "Сервер недоступен";
  }
}

async function loadCategories() {
  const { categories } = await fetchJSON("/api/categories");
  categoriesCache = categories || [];
  const sel = $("categoryFilter");
  const keep = sel.querySelector('option[value="all"]');
  sel.innerHTML = "";
  sel.appendChild(keep);
  for (const c of categories) {
    const o = document.createElement("option");
    o.value = c.id;
    o.textContent = c.name;
    sel.appendChild(o);
  }
}

async function loadStats() {
  const s = await fetchJSON("/api/stats");
  $("statTotal").textContent = s.total_channels ?? 0;
  const ul = $("catStats");
  ul.innerHTML = "";
  for (const row of s.by_category || []) {
    const li = document.createElement("li");
    li.innerHTML = `<span>${escapeHtml(row.category_name)}</span><span class="count">${row.cnt}</span>`;
    ul.appendChild(li);
  }
}

function escapeHtml(s) {
  const d = document.createElement("div");
  d.textContent = s ?? "";
  return d.innerHTML;
}

function formatMembers(n) {
  if (n == null || n === "") return "—";
  return new Intl.NumberFormat("ru-RU").format(n);
}

function exportQueryParams() {
  const p = new URLSearchParams();
  const q = $("dbSearch").value.trim();
  const category = $("categoryFilter").value;
  if (q) p.set("q", q);
  if (category && category !== "all") p.set("category", category);
  return p.toString();
}

function triggerExport(format) {
  const qs = exportQueryParams();
  const path = format === "xlsx" ? "/api/export/xlsx" : "/api/export/csv";
  window.location.href = qs ? `${path}?${qs}` : path;
}

async function deleteChannelRecord(rowId, title) {
  const label = (title || "").trim() || `запись #${rowId}`;
  if (!confirm(`Удалить из базы данных?\n\n«${label}»`)) return;
  const res = await fetch(`/api/channels/${rowId}`, { method: "DELETE" });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const msg = data.detail;
    showToast(typeof msg === "string" ? msg : "Не удалось удалить запись", true);
    return;
  }
  showToast("Запись удалена");
  await loadStats();
  await loadChannels();
}

async function loadChannels() {
  const q = $("dbSearch").value.trim();
  const category = $("categoryFilter").value;
  const params = new URLSearchParams({ limit: "200", offset: "0" });
  if (q) params.set("q", q);
  if (category && category !== "all") params.set("category", category);

  const { total, items } = await fetchJSON(`/api/channels?${params}`);
  const tbody = $("tableBody");
  tbody.innerHTML = "";

  if (!items.length) {
    const tr = document.createElement("tr");
    tr.innerHTML = `<td colspan="7" class="muted" style="text-align:center;padding:2rem">Ничего не найдено. Запустите парсинг или измените фильтры.</td>`;
    tbody.appendChild(tr);
  } else {
    for (const row of items) {
      const tr = document.createElement("tr");
      const desc = (row.description || "").slice(0, 220);
      const descMore = (row.description || "").length > 220 ? "…" : "";
      const link = row.link
        ? `<a href="${escapeHtml(row.link)}" target="_blank" rel="noopener">${escapeHtml(row.link)}</a>`
        : '<span class="muted">нет публичной ссылки</span>';
      const typeLabel =
        row.is_broadcast === 1 || row.is_broadcast === true
          ? "Канал"
          : "Супергруппа";
      tr.innerHTML = `
        <td class="cell-title">
          <strong>${escapeHtml(row.title || "—")}</strong>
          ${desc ? `<span class="desc">${escapeHtml(desc)}${descMore}</span>` : ""}
        </td>
        <td><span class="muted">${typeLabel}</span></td>
        <td class="cell-category">
          <select class="${categorySelectClass(row.category_id)}" data-row-id="${row.id}" aria-label="Категория">
            ${categoryOptionsHtml(row.category_id, row.category_name)}
          </select>
        </td>
        <td>${formatMembers(row.members_count)}</td>
        <td><span class="muted">${escapeHtml(row.search_keyword || "—")}</span></td>
        <td>${link}</td>
        <td class="cell-actions">
          <button type="button" class="btn-delete" title="Удалить из базы">Удалить</button>
        </td>
      `;
      tr.querySelector(".btn-delete").addEventListener("click", () => {
        deleteChannelRecord(row.id, row.title || "").catch((err) =>
          showToast(err.message || String(err), true)
        );
      });
      const catSel = tr.querySelector("select.cat-select");
      const prevCat = String(row.category_id || "");
      catSel.addEventListener("change", async () => {
        const newId = catSel.value;
        if (newId === prevCat) return;
        catSel.disabled = true;
        try {
          await fetchJSON(`/api/channels/${row.id}`, {
            method: "PATCH",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ category_id: newId }),
          });
          showToast("Категория обновлена");
          await loadStats();
          await loadChannels();
        } catch (err) {
          catSel.value = prevCat;
          showToast(err.message || String(err), true);
        } finally {
          catSel.disabled = false;
        }
      });
      tbody.appendChild(tr);
    }
  }

  $("tableMeta").textContent = `Показано ${items.length} из ${total}`;
}

$("parseForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const btn = $("parseBtn");
  const msg = $("parseMessage");
  msg.hidden = true;
  btn.disabled = true;
  const keyword = $("keyword").value.trim();
  const limit = parseInt($("limit").value, 10) || 30;
  try {
    const data = await fetchJSON("/api/parse", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ keyword, limit }),
    });
    msg.hidden = false;
    msg.className = "message success";
    msg.textContent = `Сохранено в базу: ${data.saved} каналов/групп по запросу «${keyword}».`;
    showToast(`Добавлено записей: ${data.saved}`);
    await loadStats();
    await loadChannels();
  } catch (err) {
    msg.hidden = false;
    msg.className = "message error";
    msg.textContent = err.message || String(err);
    showToast(msg.textContent, true);
  } finally {
    btn.disabled = false;
  }
});

function scheduleSearch() {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(() => {
    loadChannels().catch((err) => showToast(err.message, true));
  }, 300);
}

$("dbSearch").addEventListener("input", scheduleSearch);
$("categoryFilter").addEventListener("change", () => {
  loadChannels().catch((err) => showToast(err.message, true));
});

$("exportCsv").addEventListener("click", () => triggerExport("csv"));
$("exportXlsx").addEventListener("click", () => triggerExport("xlsx"));

async function init() {
  await loadHealth();
  try {
    await loadCategories();
    await loadStats();
    await loadChannels();
  } catch (e) {
    showToast(e.message || String(e), true);
  }
}

init();
