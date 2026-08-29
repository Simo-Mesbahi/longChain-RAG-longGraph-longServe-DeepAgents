"use strict";

const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];

const state = {
  runs: 0,
  lastResponse: null,
  scenarios: [],
  stageTimer: null,
  toastTimer: null,
};

const elements = {
  form: $("#investigation-form"),
  question: $("#question-input"),
  runButton: $("#run-button"),
  resultEmpty: $("#result-empty"),
  resultPanel: $("#result-panel"),
  systemState: $("#access-button"),
  systemLabel: $("#system-label"),
  accessDialog: $("#access-dialog"),
  accessForm: $("#access-form"),
  tokenInput: $("#token-input"),
  toast: $("#toast"),
};

document.addEventListener("DOMContentLoaded", () => {
  bindNavigation();
  bindComposer();
  bindResultTabs();
  bindAccessDialog();
  bootstrap();
});

async function bootstrap() {
  try {
    const [platform, readiness, scenarios] = await Promise.all([
      apiFetch("/api/v1/platform"),
      apiFetch("/ready"),
      apiFetch("/api/v1/scenarios"),
    ]);
    state.scenarios = scenarios;
    setSystemState("online", "ONLINE");
    $("#environment-label").textContent = String(platform.environment).toUpperCase();
    $("#scenario-count").textContent = pad(platform.business_scenarios);
    $("#scenario-total").textContent = pad(platform.business_scenarios);
    renderReadiness(readiness);
    renderScenarioCatalog(scenarios);
  } catch (error) {
    setSystemState("offline", "OFFLINE");
    showToast(error.message || "La plateforme ne repond pas.", true);
  }
}

function bindNavigation() {
  $$(".nav-tab").forEach((button) => {
    button.addEventListener("click", () => setView(button.dataset.view));
  });

  $$(".case-button").forEach((button) => {
    button.addEventListener("click", () => {
      elements.question.value = button.dataset.question || "";
      updateComposerMeta();
      elements.question.focus();
    });
  });

  $("#evaluate-button").addEventListener("click", runEvaluation);
  $("#copy-result").addEventListener("click", copyLastResult);
}

function bindComposer() {
  elements.question.addEventListener("input", updateComposerMeta);
  elements.question.addEventListener("keydown", (event) => {
    if ((event.ctrlKey || event.metaKey) && event.key === "Enter") {
      event.preventDefault();
      elements.form.requestSubmit();
    }
  });
  $$('input[name="mode"]').forEach((input) => {
    input.addEventListener("change", updateComposerMeta);
  });
  elements.form.addEventListener("submit", runInvestigation);
}

function bindResultTabs() {
  $$(".result-tab").forEach((button) => {
    button.addEventListener("click", () => {
      $$(".result-tab").forEach((item) => item.classList.remove("is-active"));
      $$(".result-tab-panel").forEach((item) => item.classList.remove("is-active"));
      button.classList.add("is-active");
      $(`[data-result-panel="${button.dataset.resultTab}"]`).classList.add("is-active");
    });
  });
}

function bindAccessDialog() {
  elements.systemState.addEventListener("click", () => {
    elements.tokenInput.value = sessionStorage.getItem("asteria_api_token") || "";
    elements.accessDialog.showModal();
    setTimeout(() => elements.tokenInput.focus(), 0);
  });

  elements.accessDialog.addEventListener("close", () => {
    if (elements.accessDialog.returnValue === "save") {
      const token = elements.tokenInput.value.trim();
      if (token) {
        sessionStorage.setItem("asteria_api_token", token);
        showToast("Jeton actif pour cette session.");
      }
    }
    if (elements.accessDialog.returnValue === "clear") {
      sessionStorage.removeItem("asteria_api_token");
      elements.tokenInput.value = "";
      showToast("Jeton de session efface.");
    }
  });
}

function setView(name) {
  $$(".nav-tab").forEach((button) => {
    button.classList.toggle("is-active", button.dataset.view === name);
  });
  $$("[data-view-panel]").forEach((panel) => {
    const active = panel.dataset.viewPanel === name;
    panel.hidden = !active;
    panel.classList.toggle("is-active", active);
  });
  window.scrollTo({ top: 0, behavior: "smooth" });
}

function updateComposerMeta() {
  const mode = selectedMode();
  $("#character-count").textContent = `${elements.question.value.length} / 8000`;
  $("#mode-preview").textContent = mode === "auto" ? "AUTO ROUTING" : modeLabel(mode);
}

async function runInvestigation(event) {
  event.preventDefault();
  const question = elements.question.value.trim();
  if (question.length < 5) {
    showToast("La question doit contenir au moins cinq caracteres.", true);
    elements.question.focus();
    return;
  }

  setLoading(true);
  startPipeline();
  try {
    const payload = {
      question,
      mode: selectedMode(),
      require_human_review_on_insufficient: $("#review-toggle").checked,
      enforce_production_gate: $("#production-toggle").checked,
    };
    const [response] = await Promise.all([
      apiFetch("/api/v1/investigations", {
        method: "POST",
        body: JSON.stringify(payload),
      }),
      sleep(620),
    ]);
    state.runs += 1;
    state.lastResponse = response;
    $("#run-counter").textContent = `RUN ${String(state.runs).padStart(3, "0")}`;
    completePipeline();
    renderInvestigation(response);
  } catch (error) {
    stopPipeline();
    if (error.status === 401) {
      showToast("Authentification requise. Ouvrez le statut systeme pour saisir le jeton.", true);
      elements.accessDialog.showModal();
    } else {
      showToast(error.message || "Echec de l'investigation.", true);
    }
  } finally {
    setLoading(false);
  }
}

function renderInvestigation(response) {
  elements.resultEmpty.hidden = true;
  elements.resultPanel.hidden = false;

  const status = $("#result-status");
  status.className = "status-badge";
  if (response.status === "review_required") status.classList.add("is-review");
  if (response.status === "refused") status.classList.add("is-refused");
  status.textContent = statusLabel(response.status);
  $("#result-run-id").textContent = response.request_id.toUpperCase();
  $("#answer-text").textContent = response.answer;

  renderCitations(response.citations);
  renderEvidence(response.evidence);
  renderTasks(response.tasks);
  renderAudit(response.audit_trail);
  renderChecks(response.business_checks);
  renderTelemetry(response);

  elements.resultPanel.scrollIntoView({ behavior: "smooth", block: "nearest" });
}

function renderCitations(citations) {
  const root = $("#citation-row");
  root.replaceChildren();
  citations.forEach((citation) => {
    root.append(make("span", "citation-chip", citation.source));
  });
}

function renderEvidence(evidence) {
  const root = $("#evidence-list");
  root.replaceChildren();
  if (!evidence.length) {
    root.append(make("div", "empty-detail", "Aucune preuve exploitable. La reponse est bloquee."));
    return;
  }
  evidence.forEach((item) => {
    const card = make("article", "evidence-card");
    const header = make("header");
    header.append(make("strong", "", item.source));
    header.append(make("span", "", `${Math.round(item.score * 100)}%`));
    card.append(header, make("p", "", item.excerpt));
    root.append(card);
  });
}

function renderTasks(tasks) {
  const root = $("#task-list");
  root.replaceChildren();
  tasks.forEach((task, index) => {
    const row = make("div", "task-row");
    const detail = make("div");
    detail.append(make("strong", "", task.title), make("small", "", `${task.owner} / ${task.summary}`));
    row.append(make("span", "", pad(index + 1)), detail);
    root.append(row);
  });
}

function renderAudit(auditTrail) {
  const root = $("#audit-list");
  root.replaceChildren();
  auditTrail.forEach((event) => root.append(make("li", "", event)));
}

function renderChecks(checks) {
  const root = $("#check-list");
  root.replaceChildren();
  checks.forEach((check) => {
    const row = make("div", `check-row${check.status === "fail" ? " is-fail" : ""}`);
    const detail = make("div");
    detail.append(make("strong", "", check.title), make("small", "", check.detail));
    row.append(make("span", "", check.status === "pass" ? "PASS" : "FAIL"), detail);
    root.append(row);
  });
}

function renderTelemetry(response) {
  $("#latency-value").textContent = Number(response.latency_ms).toFixed(1);
  $("#confidence-value").textContent = `${Math.round(response.confidence * 100)}%`;
  $("#evidence-value").textContent = pad(response.evidence_count);
  $("#engine-value").textContent = shortModeLabel(response.mode_used);
  $("#trace-id").textContent = response.trace_id;
  $("#trace-state").textContent = "CAPTURED";
  $(".trace-module").classList.add("is-active");
  $$(".engine-row").forEach((row) => {
    row.classList.toggle("is-active", row.dataset.engine === response.mode_used);
  });
}

function renderReadiness(readiness) {
  const score = Math.round(Number(readiness.score) * 100);
  $("#readiness-score").textContent = String(score);
  $("#readiness-meter").style.width = `${score}%`;
  $("#readiness-status").textContent =
    readiness.status === "ready" ? "Tous les controles sont operationnels" : readiness.status;
}

function renderScenarioCatalog(scenarios, results = null) {
  const root = $("#scenario-table-body");
  const resultMap = new Map((results || []).map((result) => [result.scenario.id, result]));
  root.replaceChildren();

  scenarios.forEach((scenario) => {
    const result = resultMap.get(scenario.id);
    const row = document.createElement("tr");
    const behavior = scenario.expected_answered
      ? "Reponse citee"
      : scenario.expected_human_review
        ? "Revue humaine"
        : "Refus controle";
    const source = scenario.expected_sources.length ? scenario.expected_sources.join(", ") : "Aucune";
    row.append(
      make("td", "", scenario.title),
      make("td", "", modeLabel(scenario.expected_mode)),
      make("td", "", behavior),
      make("td", "", source),
    );
    const statusCell = document.createElement("td");
    const statusClass = result ? (result.passed ? " is-pass" : " is-fail") : "";
    statusCell.append(
      make("span", `table-status${statusClass}`, result ? (result.passed ? "PASS" : "FAIL") : "PENDING"),
    );
    row.append(statusCell);
    root.append(row);
  });
}

async function runEvaluation() {
  const button = $("#evaluate-button");
  button.disabled = true;
  button.firstElementChild.textContent = "Execution...";
  try {
    const [summary] = await Promise.all([
      apiFetch("/api/v1/evaluations", { method: "POST" }),
      sleep(720),
    ]);
    const rate = Math.round(summary.pass_rate * 100);
    $("#pass-rate").textContent = `${rate}%`;
    $("#scenario-passed").textContent = pad(summary.passed);
    $("#scenario-failed").textContent = pad(summary.failed);
    $("#release-gate").textContent = summary.release_gate_passed ? "PASS" : "BLOCK";
    $("#release-label").textContent = summary.release_gate_passed
      ? "Version autorisee pour la production"
      : "Version bloquee par les tests metier";
    renderScenarioCatalog(state.scenarios, summary.results);
    showToast(
      summary.release_gate_passed
        ? "Release gate valide: tous les scenarios passent."
        : "Release gate bloque: un scenario a echoue.",
      !summary.release_gate_passed,
    );
  } catch (error) {
    if (error.status === 401) elements.accessDialog.showModal();
    showToast(error.message || "Echec de la suite metier.", true);
  } finally {
    button.disabled = false;
    button.firstElementChild.textContent = "Lancer la suite";
  }
}

async function copyLastResult() {
  if (!state.lastResponse) return;
  const sources = state.lastResponse.citations.map((item) => item.source).join(", ");
  const text = `${state.lastResponse.answer}\n\nSources: ${sources || "aucune"}`;
  try {
    await navigator.clipboard.writeText(text);
    showToast("Reponse copiee.");
  } catch {
    showToast("La copie automatique n'est pas disponible.", true);
  }
}

function startPipeline() {
  stopPipeline();
  const stages = $$(".execution-step");
  stages.forEach((stage) => stage.classList.remove("is-active", "is-complete"));
  let index = 0;
  stages[0].classList.add("is-active");
  state.stageTimer = window.setInterval(() => {
    stages[index].classList.remove("is-active");
    stages[index].classList.add("is-complete");
    index = Math.min(index + 1, stages.length - 1);
    stages[index].classList.add("is-active");
    if (index === stages.length - 1) window.clearInterval(state.stageTimer);
  }, 150);
}

function completePipeline() {
  stopPipeline();
  $$(".execution-step").forEach((stage) => {
    stage.classList.remove("is-active");
    stage.classList.add("is-complete");
  });
}

function stopPipeline() {
  if (state.stageTimer) window.clearInterval(state.stageTimer);
  state.stageTimer = null;
  $$(".execution-step").forEach((stage) => stage.classList.remove("is-active"));
}

function setLoading(isLoading) {
  elements.runButton.disabled = isLoading;
  elements.runButton.firstElementChild.textContent = isLoading ? "Execution..." : "Executer";
  elements.form.setAttribute("aria-busy", String(isLoading));
}

function setSystemState(status, label) {
  elements.systemState.classList.remove("is-online", "is-offline");
  elements.systemState.classList.add(`is-${status}`);
  elements.systemLabel.textContent = label;
}

async function apiFetch(path, options = {}) {
  const headers = new Headers(options.headers || {});
  headers.set("Accept", "application/json");
  if (options.body) headers.set("Content-Type", "application/json");
  const token = sessionStorage.getItem("asteria_api_token");
  if (token) headers.set("Authorization", `Bearer ${token}`);

  const response = await fetch(path, { ...options, headers });
  let payload = null;
  try {
    payload = await response.json();
  } catch {
    payload = null;
  }
  if (!response.ok) {
    const error = new Error(payload?.detail || `Erreur HTTP ${response.status}`);
    error.status = response.status;
    throw error;
  }
  return payload;
}

function selectedMode() {
  return $('input[name="mode"]:checked').value;
}

function modeLabel(mode) {
  return { auto: "Auto", rag: "RAG", graph: "LangGraph", deep_agent: "Deep Agent" }[mode] || mode;
}

function shortModeLabel(mode) {
  return { rag: "RAG", graph: "GRAPH", deep_agent: "DEEP" }[mode] || "--";
}

function statusLabel(status) {
  return {
    completed: "TERMINE",
    review_required: "REVUE REQUISE",
    refused: "REFUSE",
  }[status] || status.toUpperCase();
}

function make(tag, className = "", text = "") {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== "") node.textContent = text;
  return node;
}

function pad(value) {
  return String(value).padStart(2, "0");
}

function sleep(milliseconds) {
  return new Promise((resolve) => window.setTimeout(resolve, milliseconds));
}

function showToast(message, isError = false) {
  window.clearTimeout(state.toastTimer);
  elements.toast.textContent = message;
  elements.toast.classList.toggle("is-error", isError);
  elements.toast.hidden = false;
  state.toastTimer = window.setTimeout(() => {
    elements.toast.hidden = true;
  }, 3600);
}
