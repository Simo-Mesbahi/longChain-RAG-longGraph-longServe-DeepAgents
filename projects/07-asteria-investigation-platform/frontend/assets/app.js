"use strict";

const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];

const state = {
  lastResponse: null,
  history: [],
  scenarios: [],
  evaluation: null,
  investigating: false,
  evaluating: false,
  toastTimer: null,
  token: readSessionToken(),
};

const elements = {
  form: $("#investigation-form"),
  question: $("#question-input"),
  mode: $("#mode-select"),
  runButton: $("#run-button"),
  resultEmpty: $("#result-empty"),
  resultPanel: $("#result-panel"),
  accessDialog: $("#access-dialog"),
  tokenInput: $("#token-input"),
};

const sourceNames = {
  "home-protection-policy.md": "Contrat habitation",
  "claim-handling-procedure.md": "Gestion des sinistres",
  "fraud-review-policy.md": "Revue des risques",
  "water-damage-playbook.md": "D\u00e9g\u00e2t des eaux",
  "theft-claim-procedure.md": "Vol et vandalisme",
  "compensation-rules.md": "R\u00e8gles d'indemnisation",
  "exclusions-and-limits.md": "Exclusions et limites",
  "customer-faq.md": "Questions des assur\u00e9s",
  "quality-audit-policy.md": "Qualit\u00e9 et audit",
  "handler-decision-guide.md": "Guide du gestionnaire",
};

document.addEventListener("DOMContentLoaded", () => {
  bindNavigation();
  bindComposer();
  bindResultTabs();
  bindAccessDialog();
  bootstrap();
});

async function bootstrap() {
  $("#reconnect-button").disabled = true;
  setSystemState("connecting", "Connexion...");
  try {
    const [platform, readiness, scenarios] = await Promise.all([
      apiFetch("/api/v1/platform"),
      apiFetch("/ready"),
      apiFetch("/api/v1/scenarios"),
    ]);
    state.scenarios = scenarios;
    $("#corpus-count").textContent = platform.corpus_documents;
    $("#scenario-total").textContent = platform.business_scenarios;
    $("#platform-version").textContent = platform.version;
    $("#environment-label").textContent = platform.environment;
    $("#readiness-score").textContent = formatPercent(readiness.score);
    $("#readiness-status").textContent =
      readiness.status === "ready"
        ? "Contr\u00f4les de d\u00e9monstration valid\u00e9s."
        : "Des contr\u00f4les n\u00e9cessitent une v\u00e9rification.";
    $("#connection-error").hidden = true;
    setSystemState("online", "Connect\u00e9");
    renderScenarioCatalog();
  } catch (error) {
    setSystemState("offline", "Hors ligne");
    $("#connection-error-text").textContent = friendlyError(error);
    $("#connection-error").hidden = false;
    $("#readiness-score").textContent = "--";
    $("#readiness-status").textContent = "V\u00e9rification indisponible.";
    if (!state.scenarios.length) {
      const cell = make("td", "", "Sc\u00e9narios indisponibles. R\u00e9essayez la connexion.");
      cell.colSpan = 5;
      const row = make("tr");
      row.append(cell);
      $("#scenario-table-body").replaceChildren(row);
    }
  } finally {
    $("#reconnect-button").disabled = false;
  }
}

function bindNavigation() {
  $("#history-button").addEventListener("click", () => {
    renderHistory();
    $("#history-dialog").showModal();
  });
  $$("[data-view]").forEach((button) => {
    button.addEventListener("click", () => setView(button.dataset.view));
  });
  $$(".case-button").forEach((button) => {
    button.addEventListener("click", () => prepareQuestion(button.dataset.question));
  });
  $("#new-question").addEventListener("click", () => prepareQuestion(""));
  $("#evaluate-button").addEventListener("click", runEvaluation);
  $("#reconnect-button").addEventListener("click", bootstrap);
  $("#copy-result").addEventListener("click", copyLastResult);
  $("#download-result").addEventListener("click", downloadLastResult);
  $("#dismiss-error").addEventListener("click", () => {
    $("#request-error").hidden = true;
  });
}

function setView(name) {
  const labels = {
    cockpit: "Assistant",
    scenarios: "Validations",
    architecture: "Plateforme",
  };
  if (!labels[name]) return;
  $$(".nav-tab").forEach((button) => {
    const active = button.dataset.view === name;
    button.classList.toggle("is-active", active);
    if (active) button.setAttribute("aria-current", "page");
    else button.removeAttribute("aria-current");
  });
  $$("[data-view-panel]").forEach((panel) => {
    panel.hidden = panel.dataset.viewPanel !== name;
  });
  $("#view-label").textContent = labels[name];
  document.title = "Asteria | " + labels[name];
  window.scrollTo({ top: 0, behavior: scrollBehavior() });
}

function prepareQuestion(question, mode = "auto") {
  if (state.investigating) return;
  state.lastResponse = null;
  elements.question.value = question || "";
  elements.mode.value = mode;
  elements.resultPanel.hidden = true;
  elements.resultEmpty.hidden = false;
  $("#analysis-summary").hidden = true;
  $("#suggestions").hidden = false;
  $("#request-error").hidden = true;
  elements.question.setCustomValidity("");
  $("#question-error").hidden = true;
  elements.question.removeAttribute("aria-invalid");
  updateComposerMeta();
  renderHistory();
  setView("cockpit");
  elements.question.focus();
}

function bindComposer() {
  elements.question.addEventListener("input", () => {
    updateComposerMeta();
    elements.question.removeAttribute("aria-invalid");
    $("#question-error").hidden = true;
  });
  elements.question.addEventListener("keydown", (event) => {
    if ((event.ctrlKey || event.metaKey) && event.key === "Enter") {
      event.preventDefault();
      if (!state.investigating) elements.form.requestSubmit();
    }
  });
  elements.form.addEventListener("submit", runInvestigation);
}

function updateComposerMeta() {
  $("#character-count").textContent =
    new Intl.NumberFormat("fr-FR").format(elements.question.value.length) + " / 8 000";
}

function bindResultTabs() {
  const tabs = $$(".result-tab");
  tabs.forEach((button, index) => {
    button.addEventListener("click", () => selectResultTab(button.dataset.resultTab));
    button.addEventListener("keydown", (event) => {
      let next;
      if (event.key === "ArrowRight") next = (index + 1) % tabs.length;
      else if (event.key === "ArrowLeft") next = (index + tabs.length - 1) % tabs.length;
      else if (event.key === "Home") next = 0;
      else if (event.key === "End") next = tabs.length - 1;
      else return;
      event.preventDefault();
      selectResultTab(tabs[next].dataset.resultTab);
      tabs[next].focus();
    });
  });
}

function selectResultTab(name) {
  $$(".result-tab").forEach((tab) => {
    const active = tab.dataset.resultTab === name;
    tab.classList.toggle("is-active", active);
    tab.setAttribute("aria-selected", String(active));
    tab.tabIndex = active ? 0 : -1;
  });
  $$("[data-result-panel]").forEach((panel) => {
    panel.hidden = panel.dataset.resultPanel !== name;
  });
}

function bindAccessDialog() {
  $("#access-button").addEventListener("click", openAccessDialog);
  elements.accessDialog.addEventListener("close", () => {
    const action = elements.accessDialog.returnValue;
    if (action !== "save" && action !== "clear") return;
    state.token = action === "save" ? elements.tokenInput.value.trim() : "";
    try {
      if (state.token) sessionStorage.setItem("asteria_api_token", state.token);
      else sessionStorage.removeItem("asteria_api_token");
      showToast(state.token ? "Jeton enregistr\u00e9 pour cette session." : "Jeton effac\u00e9.");
    } catch {
      showToast("Stockage indisponible : jeton conserv\u00e9 jusqu'au rechargement.");
    }
    elements.tokenInput.value = "";
  });
}

function openAccessDialog() {
  if (elements.accessDialog.open) return;
  elements.tokenInput.value = state.token;
  // Reset the previous submit value so Escape never replays a save or clear.
  elements.accessDialog.returnValue = "cancel";
  elements.accessDialog.showModal();
  elements.tokenInput.focus();
}

function readSessionToken() {
  try {
    return sessionStorage.getItem("asteria_api_token") || "";
  } catch {
    return "";
  }
}

async function runInvestigation(event) {
  event.preventDefault();
  if (state.investigating) return;
  const question = elements.question.value.trim().replace(/\s+/g, " ");
  if (question.length < 5) {
    $("#question-error").textContent = "Saisissez au moins cinq caract\u00e8res.";
    $("#question-error").hidden = false;
    elements.question.setAttribute("aria-invalid", "true");
    elements.question.focus();
    return;
  }
  const payload = {
    question,
    mode: elements.mode.value,
    require_human_review_on_insufficient: $("#review-toggle").checked,
    enforce_production_gate: $("#production-toggle").checked,
  };
  state.lastResponse = null;
  elements.resultPanel.hidden = true;
  $("#analysis-summary").hidden = true;
  $("#request-error").hidden = true;
  $("#question-error").hidden = true;
  setLoading(true);
  try {
    const response = await apiFetch("/api/v1/investigations", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    state.lastResponse = response;
    state.history.unshift({ response, payload });
    state.history = state.history.slice(0, 8);
    renderInvestigation(response);
    renderHistory();
    showToast(statusLabel(response.status) + ". Analyse disponible.");
  } catch (error) {
    $("#request-error-text").textContent = friendlyError(error);
    $("#request-error").hidden = false;
    if (error.status === 401) openAccessDialog();
  } finally {
    setLoading(false);
    if (state.lastResponse && !$("#view-cockpit").hidden) {
      $("#answer-heading").focus({ preventScroll: true });
      elements.resultPanel.scrollIntoView({
        behavior: scrollBehavior(),
        block: "nearest",
      });
    }
  }
}

function setLoading(loading) {
  state.investigating = loading;
  elements.form.setAttribute("aria-busy", String(loading));
  $("#loading-state").hidden = !loading;
  elements.resultEmpty.hidden = loading || Boolean(state.lastResponse);
  $("#suggestions").hidden = loading || Boolean(state.lastResponse);
  const controls = [
    ...$$("input, select, textarea, button", elements.form),
    ...$$(".case-button, .history-list button, .scenario-open"),
    $("#new-question"),
    $("#review-toggle"),
    $("#production-toggle"),
  ];
  controls.forEach((control) => {
    control.disabled = loading;
  });
  elements.runButton.firstElementChild.textContent = loading ? "Analyse..." : "Analyser";
}

function renderInvestigation(response) {
  elements.resultEmpty.hidden = true;
  elements.resultPanel.hidden = false;
  $("#suggestions").hidden = true;
  $("#analysis-summary").hidden = false;
  const status = $("#result-status");
  status.className = "status-badge";
  if (response.status === "review_required") status.classList.add("is-review");
  if (response.status === "refused") status.classList.add("is-refused");
  status.textContent = statusLabel(response.status);
  $("#result-question").textContent = response.question;
  $("#answer-text").textContent = response.answer;
  $("#result-run-id").textContent = response.request_id;
  $("#trace-id").textContent = response.trace_id;
  $("#result-engine").textContent = modeLabel(response.mode_used);
  $("#result-time").textContent = new Intl.DateTimeFormat("fr-FR", {
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(response.created_at));
  $("#engine-value").textContent = modeLabel(response.mode_used);
  $("#latency-value").textContent = formatNumber(response.latency_ms) + " ms";
  $("#evidence-value").textContent = response.evidence_count;
  $("#confidence-value").textContent = formatPercent(response.confidence);
  $("#sources-count").textContent = new Set(response.evidence.map((item) => item.source)).size;
  renderEvidence(response.evidence);
  renderCitations(response.citations, response.evidence);
  renderTasks(response.tasks);
  renderAudit(response.audit_trail);
  renderChecks(response.business_checks);
  selectResultTab("evidence");
}

function renderCitations(citations, evidence) {
  const root = $("#citation-row");
  root.replaceChildren();
  const uniqueSources = [...new Set(citations.map((item) => item.source))];
  uniqueSources.forEach((source, index) => {
    const button = make("button", "citation-chip");
    button.type = "button";
    button.title = source;
    button.append(icon("file-text"), make("span", "", index + 1 + ". " + sourceLabel(source)));
    button.addEventListener("click", () => {
      selectResultTab("evidence");
      const evidenceIndex = evidence.findIndex((item) => item.source === source);
      const target = $("#evidence-" + evidenceIndex);
      if (target) {
        target.open = true;
        $("summary", target).focus({ preventScroll: true });
        target.scrollIntoView({
          behavior: scrollBehavior(),
          block: "nearest",
        });
      } else {
        $("#panel-evidence").focus();
      }
    });
    root.append(button);
  });
}

function renderEvidence(evidence) {
  const root = $("#evidence-list");
  root.replaceChildren();
  if (!evidence.length) {
    root.append(make("p", "empty-detail", "Aucun passage exploitable pour cette question."));
    return;
  }
  evidence.forEach((item, index) => {
    const detail = make("details", "evidence-item");
    detail.id = "evidence-" + index;
    detail.open = index === 0;
    const summary = make("summary");
    const score = make("span", "evidence-score", formatPercent(item.score) + " de correspondance");
    summary.append(
      icon("file-text"),
      make("strong", "", sourceLabel(item.source)),
      score,
      icon("chevron-down", "small chevron"),
    );
    detail.append(summary, make("small", "", item.source), make("p", "", item.excerpt));
    root.append(detail);
  });
}

function renderTasks(tasks) {
  const root = $("#task-list");
  root.replaceChildren();
  if (!tasks.length) {
    root.append(
      make("p", "empty-detail", "Aucune \u00e9tape d\u00e9taill\u00e9e pour cette analyse."),
    );
  }
  tasks.forEach((task, index) => {
    const row = make("div", "task-row");
    const detail = make("div");
    detail.append(
      make("strong", "", task.title),
      make("small", "", task.owner + " : " + task.summary),
    );
    row.append(make("span", "", String(index + 1).padStart(2, "0")), detail);
    detail.append(
      make("small", "task-status", task.status === "blocked" ? "Bloqu\u00e9e" : "Termin\u00e9e"),
    );
    root.append(row);
  });
}

function renderAudit(events) {
  $("#audit-list").replaceChildren(...events.map((event) => make("li", "", event)));
}

function renderChecks(checks) {
  const root = $("#check-list");
  root.replaceChildren();
  if (!checks.length) root.append(make("p", "empty-detail", "Aucun contr\u00f4le disponible."));
  checks.forEach((check) => {
    const failed = check.status !== "pass";
    const row = make("div", "check-row" + (failed ? " is-fail" : ""));
    const detail = make("div");
    detail.append(make("strong", "", check.title), make("small", "", check.detail));
    row.append(icon(failed ? "circle-alert" : "circle-check"), detail);
    detail.append(make("small", "", failed ? "\u00c9chec" : "Valid\u00e9"));
    root.append(row);
  });
}

function renderHistory() {
  $("#history-empty").hidden = state.history.length > 0;
  $("#history-dialog-empty").hidden = state.history.length > 0;
  $("#history-note").hidden = !state.history.length;
  for (const root of [$("#history-list"), $("#history-dialog-list")]) {
    root.replaceChildren();
    state.history.forEach(({ response, payload }) => {
      const item = make("li");
      const button = make("button");
      button.type = "button";
      button.title = response.question;
      const active = state.lastResponse?.request_id === response.request_id;
      button.classList.toggle("is-active", active);
      if (active) button.setAttribute("aria-current", "true");
      button.disabled = state.investigating;
      button.append(icon("clock"), make("span", "", response.question));
      button.addEventListener("click", () => {
        if (state.investigating) return;
        $("#history-dialog").close();
        state.lastResponse = response;
        elements.question.value = response.question;
        elements.mode.value = payload.mode;
        $("#review-toggle").checked = payload.require_human_review_on_insufficient;
        $("#production-toggle").checked = payload.enforce_production_gate;
        $("#request-error").hidden = true;
        $("#question-error").hidden = true;
        elements.question.removeAttribute("aria-invalid");
        updateComposerMeta();
        setView("cockpit");
        renderInvestigation(response);
        renderHistory();
        $("#answer-heading").focus({ preventScroll: true });
      });
      item.append(button);
      root.append(item);
    });
  }
}

function renderScenarioCatalog() {
  const root = $("#scenario-table-body");
  const resultMap = new Map(
    (state.evaluation?.results || []).map((result) => [result.scenario.id, result]),
  );
  root.replaceChildren();
  if (!state.scenarios.length) {
    const cell = make("td", "", "Aucun sc\u00e9nario disponible.");
    cell.colSpan = 5;
    const row = make("tr");
    row.append(cell);
    root.append(row);
    return;
  }
  state.scenarios.forEach((scenario) => {
    const result = resultMap.get(scenario.id);
    const row = make("tr");
    const title = make("td");
    title.append(make("strong", "", scenario.title));
    if (scenario.expected_sources.length) {
      title.append(make("small", "", scenario.expected_sources.map(sourceLabel).join(", ")));
    }
    const behavior = scenario.expected_answered
      ? "R\u00e9ponse avec sources"
      : scenario.expected_human_review
        ? "Revue humaine"
        : "Refus encadr\u00e9";
    row.append(title, make("td", "", modeLabel(scenario.expected_mode)), make("td", "", behavior));
    const status = make("td");
    status.append(
      make(
        "span",
        "table-status" + (result ? (result.passed ? " is-pass" : " is-fail") : ""),
        result ? (result.passed ? "Valid\u00e9" : "\u00c9chec") : "Non test\u00e9",
      ),
    );
    const action = make("td");
    const button = make("button", "text-button scenario-open", "Essayer");
    button.type = "button";
    button.disabled = state.investigating;
    button.setAttribute("aria-label", "Essayer : " + scenario.title);
    button.append(icon("arrow-up-right"));
    button.addEventListener("click", () => prepareQuestion(scenario.question));
    action.append(button);
    row.append(status, action);
    root.append(row);
  });
}

async function runEvaluation() {
  if (state.evaluating) return;
  state.evaluating = true;
  const button = $("#evaluate-button");
  button.disabled = true;
  button.firstElementChild.textContent = "Tests en cours...";
  $("#view-scenarios").setAttribute("aria-busy", "true");
  $("#evaluation-error").hidden = true;
  // Do not present results from a previous suite as the current outcome.
  state.evaluation = null;
  ["pass-rate", "scenario-passed", "scenario-failed"].forEach((id) => {
    $("#" + id).textContent = "--";
  });
  $("#release-label").textContent = "Tests en cours...";
  renderScenarioCatalog();
  try {
    const summary = await apiFetch("/api/v1/evaluations", {
      method: "POST",
    });
    state.evaluation = summary;
    state.scenarios = summary.results.map((result) => result.scenario);
    $("#pass-rate").textContent = formatPercent(summary.pass_rate);
    $("#scenario-total").textContent = summary.scenarios;
    $("#scenario-passed").textContent = summary.passed;
    $("#scenario-failed").textContent = summary.failed;
    $("#release-label").textContent = summary.release_gate_passed
      ? "Tous les sc\u00e9narios sont valid\u00e9s"
      : "Des sc\u00e9narios sont \u00e0 corriger";
    renderScenarioCatalog();
    showToast(
      summary.release_gate_passed
        ? "Validations termin\u00e9es avec succ\u00e8s."
        : "Des tests ont \u00e9chou\u00e9.",
      !summary.release_gate_passed,
    );
  } catch (error) {
    $("#evaluation-error").textContent = friendlyError(error);
    $("#evaluation-error").hidden = false;
    $("#release-label").textContent = "\u00c9valuation interrompue";
    if (error.status === 401) openAccessDialog();
  } finally {
    state.evaluating = false;
    button.disabled = false;
    button.firstElementChild.textContent = "Lancer les tests";
    $("#view-scenarios").setAttribute("aria-busy", "false");
  }
}

async function copyLastResult() {
  if (!state.lastResponse) return;
  const response = state.lastResponse;
  const text =
    response.answer +
    "\n\nSources : " +
    [...new Set(response.citations.map((item) => item.source))].join(", ");
  try {
    await navigator.clipboard.writeText(text);
    showToast("R\u00e9ponse et sources copi\u00e9es.");
  } catch {
    showToast("Copie indisponible. Utilisez le t\u00e9l\u00e9chargement du rapport.", true);
  }
}

function downloadLastResult() {
  if (!state.lastResponse) return;
  const response = state.lastResponse;
  const text = [
    "ASTERIA | Rapport d'analyse",
    "D\u00e9monstration p\u00e9dagogique - corpus fictif",
    "",
    "Question : " + response.question,
    "Statut : " + statusLabel(response.status),
    "Moteur : " + modeLabel(response.mode_used),
    "Date : " + response.created_at,
    "",
    response.answer,
    "",
    "SOURCES",
    ...response.citations.map((item) => "- " + item.source + " (" + item.chunk_id + ")"),
    "",
    "PASSAGES",
    ...response.evidence.map((item) => item.source + "\n" + item.excerpt + "\n"),
    "CONTROLES",
    ...response.business_checks.map(
      (item) => item.status + " | " + item.title + " : " + item.detail,
    ),
    "",
    "Trace locale : " + response.trace_id,
    "Requ\u00eate : " + response.request_id,
  ].join("\n");
  const url = URL.createObjectURL(new Blob([text], { type: "text/plain;charset=utf-8" }));
  const link = make("a");
  link.href = url;
  link.download = "asteria-" + response.request_id.replace(/[^a-z0-9_-]/gi, "") + ".txt";
  document.body.append(link);
  link.click();
  link.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
  showToast("Rapport t\u00e9l\u00e9charg\u00e9.");
}

async function apiFetch(path, options = {}) {
  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), 60000);
  const headers = new Headers(options.headers || {});
  headers.set("Accept", "application/json");
  if (options.body) headers.set("Content-Type", "application/json");
  if (state.token) headers.set("Authorization", "Bearer " + state.token);
  try {
    const response = await fetch(path, {
      ...options,
      headers,
      signal: controller.signal,
    });
    let payload;
    try {
      payload = await response.json();
    } catch {
      if (response.ok) throw new Error("INVALID_RESPONSE");
    }
    if (!response.ok) {
      const error = new Error("HTTP_" + response.status);
      error.status = response.status;
      throw error;
    }
    if (payload === null || typeof payload !== "object") throw new Error("INVALID_RESPONSE");
    return payload;
  } finally {
    window.clearTimeout(timeout);
  }
}

function friendlyError(error) {
  if (error.status === 401)
    return "Acc\u00e8s prot\u00e9g\u00e9 : renseignez le jeton Asteria, puis relancez votre demande.";
  if (error.status === 429)
    return "Trop de demandes. Patientez une minute avant de r\u00e9essayer.";
  if (error.status === 422)
    return "La question ou les param\u00e8tres ne sont pas valides. V\u00e9rifiez votre saisie.";
  if (error.name === "AbortError")
    return "Le serveur met trop de temps \u00e0 r\u00e9pondre. R\u00e9essayez dans un instant.";
  if (error.status >= 500)
    return "Le serveur a rencontr\u00e9 une erreur. Votre question est conserv\u00e9e ; vous pouvez r\u00e9essayer.";
  if (error.message === "INVALID_RESPONSE")
    return "La r\u00e9ponse du serveur est illisible. V\u00e9rifiez que l'API Asteria est d\u00e9marr\u00e9e.";
  return "Connexion au serveur impossible. V\u00e9rifiez que l'application est d\u00e9marr\u00e9e, puis r\u00e9essayez.";
}

function setSystemState(status, label) {
  $("#system-state").className = "system-state is-" + status;
  $("#system-label").textContent = label;
}

function modeLabel(mode) {
  return (
    {
      auto: "Automatique",
      rag: "RAG",
      graph: "LangGraph",
      deep_agent: "Deep Agent",
    }[mode] || mode
  );
}

function statusLabel(status) {
  return (
    {
      completed: "Analyse termin\u00e9e",
      review_required: "Revue humaine requise",
      refused: "R\u00e9ponse non disponible",
    }[status] || status
  );
}

function sourceLabel(source) {
  return sourceNames[source] || source;
}

function formatNumber(value) {
  return new Intl.NumberFormat("fr-FR", { maximumFractionDigits: 1 }).format(value);
}

function formatPercent(value) {
  return new Intl.NumberFormat("fr-FR", {
    style: "percent",
    maximumFractionDigits: 0,
  }).format(value);
}

function scrollBehavior() {
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "instant" : "smooth";
}

function make(tag, className = "", text = "") {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== "") node.textContent = text;
  return node;
}

function icon(name, extraClass = "small") {
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("class", "icon " + extraClass);
  svg.setAttribute("aria-hidden", "true");
  const use = document.createElementNS("http://www.w3.org/2000/svg", "use");
  use.setAttribute("href", "/assets/icons.svg#" + name);
  svg.append(use);
  return svg;
}

function showToast(message, isError = false) {
  window.clearTimeout(state.toastTimer);
  const toast = $("#toast");
  toast.textContent = message;
  toast.classList.toggle("is-error", isError);
  toast.hidden = false;
  state.toastTimer = window.setTimeout(() => {
    toast.hidden = true;
  }, 4500);
}
