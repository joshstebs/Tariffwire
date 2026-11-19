const main = document.querySelector("#main");
const tabs = [...document.querySelectorAll(".tabs a")];

const state = {
  meta: null,
  query: "",
};

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function humanize(value) {
  return String(value ?? "").replaceAll("_", " ");
}

function badge(text, kind = "") {
  return `<span class="badge ${kind}">${escapeHtml(humanize(text))}</span>`;
}

async function api(path, options) {
  const response = await fetch(path, options);
  const payload = await response.json();
  if (!response.ok) {
    throw new Error(payload.error || `Request failed (${response.status})`);
  }
  return payload;
}

function setTab(name) {
  for (const tab of tabs) {
    const current = tab.dataset.tab === name;
    tab.setAttribute("aria-current", current ? "page" : "false");
  }
}

function dateRows(pairs) {
  const rows = pairs.filter(([, value]) => value);
  if (!rows.length) return "";
  return `<dl class="dates">${rows
    .map(([label, value]) => `<dt>${escapeHtml(label)}</dt><dd>${escapeHtml(value)}</dd>`)
    .join("")}</dl>`;
}

function layout(title, body) {
  main.innerHTML = `<article class="panel"><h2>${escapeHtml(title)}</h2>${body}</article>`;
}

function renderSearch(resultsHtml = "") {
  setTab("search");
  layout(
    "Search public titles",
    `<form id="search-form" class="search-row" role="search">
      <div>
        <label for="q">Chapter title, document, or a number such as 0901.11</label>
        <input id="q" name="q" value="${escapeHtml(state.query)}" autocomplete="off" enterkeyhint="search">
      </div>
      <button type="submit">Search</button>
    </form>
    <p class="fine">A match opens a source. It is not a classification and it has no duty rate. Edition ${escapeHtml(state.meta?.edition || "")}, index read ${escapeHtml(state.meta?.index_retrieved_at || "")}. Live tariff integration: no.</p>
    <div id="search-results">${resultsHtml}</div>`
  );
  const form = document.querySelector("#search-form");
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    state.query = document.querySelector("#q").value.trim();
    location.hash = `#/search?q=${encodeURIComponent(state.query)}`;
  });
}

function resultCard(item) {
  const href = item.kind === "chapter" ? `#/chapter/${item.chapter}` : `#/document/${item.id}`;
  const when = item.kind === "chapter" ? item.effective_date : item.effective || item.revised || item.published || "Date not stated on the stored record";
  return `<article class="result">
    <div class="kicker">${badge(item.kind)} ${badge(item.jurisdiction, "neutral")}</div>
    <h3><a href="${href}">${escapeHtml(item.title)}</a></h3>
    <p>${escapeHtml(item.match_reason)}</p>
    <p class="meta">${escapeHtml(item.publisher)} · ${escapeHtml(when)}</p>
  </article>`;
}

async function showSearch(query) {
  state.query = query || "";
  if (!query) {
    renderSearch("");
    return;
  }
  renderSearch(`<p>Searching…</p>`);
  try {
    const payload = await api(`/api/search?q=${encodeURIComponent(query)}`);
    const body = payload.results.length
      ? `<p class="status-line">${payload.result_count} result${payload.result_count === 1 ? "" : "s"}. ${escapeHtml(payload.disclaimer)}</p><div class="results">${payload.results.map(resultCard).join("")}</div>`
      : `<p class="status-line">No stored title or document uses those words. Nothing was guessed.</p>`;
    renderSearch(body);
  } catch (error) {
    renderSearch(`<p class="error">${escapeHtml(error.message)}</p>`);
  }
}

async function showChapters() {
  setTab("chapters");
  layout("Chapter index", "<p>Loading the stored CBSA index…</p>");
  const catalog = await api("/api/chapters");
  const cards = catalog.chapters
    .map(
      (chapter) => `<article class="result">
        <div class="kicker">${badge(`Section ${chapter.section}`, "neutral")} ${badge(chapter.effective_date)}</div>
        <h3><a href="#/chapter/${chapter.chapter}">Chapter ${chapter.chapter} — ${escapeHtml(chapter.title)}</a></h3>
        <p class="meta">${escapeHtml(chapter.section_title)}</p>
      </article>`
    )
    .join("");
  layout(
    `${catalog.edition} chapter index`,
    `<p>${escapeHtml(catalog.caveat)} Retrieved ${escapeHtml(catalog.retrieved_at)}.</p>
     <p><a href="${escapeHtml(catalog.index_url)}">Official chapter index</a></p>
     <div class="results">${cards}</div>`
  );
}

async function showChapter(number) {
  setTab("chapters");
  layout("Chapter", "<p>Loading…</p>");
  try {
    const chapter = await api(`/api/chapters/${number}`);
    layout(
      `Chapter ${chapter.chapter}`,
      `${badge(chapter.edition || "")} ${badge("Canada", "neutral")} ${badge("No duty rate stored", "warn")}
       <h2>${escapeHtml(chapter.title)}</h2>
       ${dateRows([
         ["Jurisdiction", chapter.jurisdiction],
         ["Publisher", chapter.publisher],
         ["Section", `${chapter.section}. ${chapter.section_title}`],
         ["Effective date on the index row", chapter.effective_date],
         ["Index retrieved", chapter.retrieved_at],
         ["Tariff classification", "Not determined"],
         ["Duty rate", "Not stored"],
       ])}
       <p>${escapeHtml(chapter.caveat)}</p>
       <div class="actions">
         <a class="button" href="${escapeHtml(chapter.html_url)}">Open official HTML</a>
         ${chapter.pdf_url ? `<a class="button secondary" href="${escapeHtml(chapter.pdf_url)}">Open official PDF</a>` : ""}
         <a class="button secondary" href="#/chapters">All chapters</a>
       </div>`
    );
  } catch (error) {
    layout("Chapter", `<p class="error">${escapeHtml(error.message)}</p>`);
  }
}

function quoteBlock(document) {
  if (!document.quotations?.length) return "";
  return document.quotations.map((quote) => `<blockquote>${escapeHtml(quote)}</blockquote>`).join("");
}

function conflictBlock(document) {
  if (!document.conflicts?.length) return "";
  return `<div class="callout"><strong>Sources disagree.</strong><ul class="clean">${document.conflicts
    .map((item) => `<li>${escapeHtml(item.topic)}: ${escapeHtml(item.detail)}</li>`)
    .join("")}</ul></div>`;
}

async function showDocument(id) {
  setTab("search");
  layout("Document", "<p>Loading…</p>");
  try {
    const document = await api(`/api/documents/${id}`);
    const labels = document.date_labels || {};
    layout(
      document.instrument,
      `${badge(document.jurisdiction, "neutral")} ${badge("Not a determination", "warn")}
       <h2>${escapeHtml(document.title)}</h2>
       ${dateRows([
         ["Publisher", document.publisher],
         ["Published", document.published ? `${document.published}. ${labels.published || ""}` : null],
         ["Revised", document.revised ? `${document.revised}. ${labels.revised || ""}` : null],
         ["Effective", document.effective ? `${document.effective}. ${labels.effective || ""}` : labels.effective || "Not stated as a single date on the page that was read"],
         ["Consolidation currency", labels.consolidation_currency],
         ["Other date note", labels.service_hours],
         ["Retrieved", document.retrieved_at],
       ])}
       <p>${escapeHtml(document.summary)}</p>
       ${quoteBlock(document)}
       ${conflictBlock(document)}
       <p><strong>Limit.</strong> ${escapeHtml(document.limitation)}</p>
       <div class="actions">
         <a class="button" href="${escapeHtml(document.url)}">Open official source</a>
         <a class="button secondary" href="#/search">Back to search</a>
       </div>`
    );
  } catch (error) {
    layout("Document", `<p class="error">${escapeHtml(error.message)}</p>`);
  }
}

function renderClassify(resultHtml = "") {
  setTab("classify");
  layout(
    "Classification research aid",
    `<p>Describe the goods. The aid compares your words with official chapter titles and tells you what it did not decide. It will not produce a 10-digit classification or a duty rate.</p>
     <form id="classify-form" class="stack">
       <div>
         <label for="description">Goods description</label>
         <textarea id="description" name="description" required placeholder="Example: roasted coffee beans, not decaffeinated"></textarea>
       </div>
       <div>
         <label for="materials">Materials</label>
         <input id="materials" name="materials" placeholder="What the goods are made of">
       </div>
       <div>
         <label for="function">Function</label>
         <input id="function" name="function" placeholder="What the goods do">
       </div>
       <div>
         <label for="condition">Condition</label>
         <select id="condition" name="condition">
           <option value="">Not specified</option>
           <option>New</option>
           <option>Used</option>
           <option>Assembled</option>
           <option>Unassembled</option>
         </select>
       </div>
       <div>
         <label for="origin">Country of origin, if you already know it</label>
         <input id="origin" name="origin" placeholder="This is not an origin determination">
       </div>
       <div>
         <label for="importation">Commercial or casual</label>
         <select id="importation" name="importation">
           <option value="">Not specified</option>
           <option>Commercial</option>
           <option>Casual</option>
         </select>
       </div>
       <button type="submit">Build research packet</button>
     </form>
     <div id="packet">${resultHtml}</div>`
  );
  document.querySelector("#classify-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = event.currentTarget;
    const body = Object.fromEntries(new FormData(form).entries());
    const packetHost = document.querySelector("#packet");
    packetHost.innerHTML = "<p>Comparing chapter titles…</p>";
    try {
      const packet = await api("/api/classify", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      packetHost.innerHTML = renderPacket(packet);
    } catch (error) {
      packetHost.innerHTML = `<p class="error">${escapeHtml(error.message)}</p>`;
    }
  });
}

function renderPacket(packet) {
  const candidates = packet.candidate_chapters.length
    ? `<div class="results">${packet.candidate_chapters
        .map(
          (item) => `<article class="result">
            <div class="kicker">${badge("Title overlap only", "warn")} ${badge(`Section ${item.section}`, "neutral")}</div>
            <h3><a href="#/chapter/${item.chapter}">Chapter ${item.chapter} — ${escapeHtml(item.title)}</a></h3>
            <p>Matched words: ${escapeHtml(item.matched_terms.join(", ") || "named chapter")}.</p>
            <p class="meta">Index effective date ${escapeHtml(item.effective_date_on_index)} · ${escapeHtml(item.edition)}</p>
          </article>`
        )
        .join("")}</div>`
    : `<p>No chapter title overlapped the description. No chapter was guessed.</p>`;
  const code = packet.user_supplied_code
    ? `<div class="callout"><strong>Number in the description: ${escapeHtml(packet.user_supplied_code.normalized)}.</strong> ${escapeHtml(packet.user_supplied_code.reason)}</div>`
    : "";
  return `<section class="card" style="margin-top:1rem">
    <div class="kicker">${badge("Uncertainty: high", "bad")} ${badge("Professional review required", "warn")}</div>
    <h3>Research packet</h3>
    <p>${escapeHtml(packet.disclaimer)}</p>
    <p><strong>Status:</strong> ${escapeHtml(packet.status.replaceAll("_", " "))}. Tariff classification: not determined. Duty rate: not stored.</p>
    ${code}
    <h3>Why this stays uncertain</h3>
    <ul class="clean">${packet.uncertainty.reasons.map((reason) => `<li>${escapeHtml(reason)}</li>`).join("")}</ul>
    <h3>Review triggers</h3>
    <ul class="clean">${packet.review_triggers.map((reason) => `<li>${escapeHtml(reason)}</li>`).join("")}</ul>
    <h3>Chapters to open, not a choice of one</h3>
    ${candidates}
    ${packet.conflicts.length ? `<div class="callout"><strong>A stored source conflict applies.</strong><ul class="clean">${packet.conflicts.map((item) => `<li>${escapeHtml(item.observation)}</li>`).join("")}</ul></div>` : ""}
    <h3>What to do next</h3>
    <ul class="clean">${packet.next_steps.map((step) => `<li>${escapeHtml(step)}</li>`).join("")}</ul>
    <h3>Citations</h3>
    <ul class="clean">${packet.citations
      .map(
        (item) => `<li><a href="#/document/${escapeHtml(item.id)}">${escapeHtml(item.title)}</a> — ${escapeHtml(item.publisher)}, retrieved ${escapeHtml(item.retrieved_at)}</li>`
      )
      .join("")}</ul>
    <p class="fine">${escapeHtml(packet.search_expansion_status)}</p>
  </section>`;
}

async function showSources() {
  setTab("sources");
  layout("Sources", "<p>Loading the source registry…</p>");
  const payload = await api("/api/sources");
  const cards = payload.sources
    .map((source) => {
      const kind = source.status === "verified_public_page" || source.status === "verified_public_file" ? "neutral" : "warn";
      const link = source.url ? `<a href="${escapeHtml(source.url)}">Official page</a>` : "No URL stored";
      return `<article class="card">
        <div class="kicker">${badge(source.status, kind)} ${badge(source.jurisdiction, "neutral")}</div>
        <h3>${escapeHtml(source.title)}</h3>
        <p>${escapeHtml(source.notes)}</p>
        ${dateRows([
          ["Publisher", source.publisher],
          ["Retrieved", source.retrieved_at],
          ["Ingestion", humanize(source.ingestion)],
          ["Live integration", source.live_integration ? "Yes" : "No"],
        ])}
        <p>${link}</p>
      </article>`;
    })
    .join("");
  layout(
    "Source registry",
    `<p>${escapeHtml(payload.method)}</p><div class="list">${cards}</div>`
  );
}

function monitorTable(report) {
  if (!report?.observations?.length) {
    return `<p>${escapeHtml(report?.meaning || "No fingerprint has been saved.")}</p>`;
  }
  const rows = report.observations
    .map(
      (item) => `<tr>
        <td><a href="${escapeHtml(item.url)}">${escapeHtml(item.title || item.id)}</a></td>
        <td>${escapeHtml(item.http_status ?? "—")}</td>
        <td>${escapeHtml(item.change)}</td>
        <td><code>${escapeHtml((item.sha256 || "").slice(0, 12))}</code></td>
      </tr>`
    )
    .join("");
  return `<p>Checked ${escapeHtml(report.checked_at)}. Failures: ${escapeHtml(report.failure_count)}. Pages whose bytes differ from the baseline: ${escapeHtml(report.changed_count)}.</p>
    <p>${escapeHtml(report.meaning)}</p>
    <div class="table-wrap"><table>
      <thead><tr><th>Page</th><th>HTTP</th><th>Compared with baseline</th><th>SHA-256 prefix</th></tr></thead>
      <tbody>${rows}</tbody>
    </table></div>`;
}

async function showChanges() {
  setTab("changes");
  layout("Change check", "<p>Loading the last fingerprint…</p>");
  const report = await api("/api/monitor");
  layout(
    "Change check",
    `<p>This checks whether the saved public pages still have the same bytes. A change is a reason to re-read the page. It is not a list of amended duty rates, and it is not a live tariff feed.</p>
     <button id="run-check" type="button">Check the public pages now</button>
     <div id="monitor">${monitorTable(report)}</div>`
  );
  document.querySelector("#run-check").addEventListener("click", async (buttonEvent) => {
    const button = buttonEvent.currentTarget;
    button.disabled = true;
    button.textContent = "Checking public pages…";
    try {
      const fresh = await api("/api/monitor/run", { method: "POST", body: "{}" });
      document.querySelector("#monitor").innerHTML = monitorTable(fresh);
    } catch (error) {
      document.querySelector("#monitor").innerHTML = `<p class="error">${escapeHtml(error.message)}</p>`;
    } finally {
      button.disabled = false;
      button.textContent = "Check the public pages now";
    }
  });
}

async function route() {
  const raw = location.hash.replace(/^#/, "") || "/search";
  const [path, queryString] = raw.split("?");
  const params = new URLSearchParams(queryString || "");
  try {
    if (!state.meta) state.meta = await api("/api/meta");
    if (path.startsWith("/chapter/")) return showChapter(path.split("/")[2]);
    if (path.startsWith("/document/")) return showDocument(path.split("/")[2]);
    if (path.startsWith("/chapters")) return showChapters();
    if (path.startsWith("/classify")) return renderClassify();
    if (path.startsWith("/sources")) return showSources();
    if (path.startsWith("/changes")) return showChanges();
    return showSearch(params.get("q") || "");
  } catch (error) {
    layout("Something went wrong", `<p class="error">${escapeHtml(error.message)}</p>`);
  }
}

window.addEventListener("hashchange", route);
if (!location.hash) location.hash = "#/search";
route();
