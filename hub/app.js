import { lessons, checks } from "./lessons.js";

const base = "https://github.com/mahsa-teimourikia/awsome-ai-agents/blob/main/";
const filters = document.querySelector("#filters");
const cards = document.querySelector("#cards");
const workspace = document.querySelector("#workspace");
const trackList = document.querySelector("#track-list");

let selected = lessons[0];
let level = "All";
let tab = "learn";
let completed = JSON.parse(localStorage.getItem("ai-agents-hub-progress") || "[]");

const link = path => path.startsWith("http") ? path : base + path;
const agentOpsLessons = lessons.filter(lesson => lesson.title.startsWith("AgentOps Lab"));

function sourceLabel(ref) {
  if (ref.startsWith("http")) {
    const url = new URL(ref);
    return url.hostname.replace(/^www\./, "");
  }
  if (ref.includes("notebooks/")) return "Notebook lesson";
  if (ref.includes("agentops_lab/")) return "Implementation source";
  if (ref.endsWith("README.md")) return "Notebook track index";
  if (ref.startsWith("docs/")) return "Course guide";
  if (ref.startsWith("labs/")) return "Lab resource";
  return ref;
}

function selectLesson(id) {
  selected = lessons.find(lesson => lesson.id === id) || selected;
  tab = "learn";
  renderCards();
  renderTrack();
  renderWorkspace();
  workspace.scrollIntoView({behavior: "smooth", block: "start"});
}

function renderFilters() {
  filters.innerHTML = ["All", "Beginner", "Intermediate", "Advanced"]
    .map(item => `<button class="${level === item ? "active" : ""}" data-level="${item}">${item}</button>`)
    .join("");
  filters.querySelectorAll("button").forEach(button => {
    button.onclick = () => {
      level = button.dataset.level;
      renderFilters();
      renderCards();
    };
  });
}

function renderTrack() {
  if (!trackList) return;
  trackList.innerHTML = agentOpsLessons.map((lesson, index) => `
    <button class="track-card ${lesson.id === selected.id ? "selected" : ""}" data-id="${lesson.id}">
      <span class="track-step">${String(index + 1).padStart(2, "0")}</span>
      <span>
        <b>${lesson.title.replace("AgentOps Lab: ", "")}</b>
        <small>${lesson.summary}</small>
      </span>
    </button>`).join("");
  trackList.querySelectorAll(".track-card").forEach(card => {
    card.onclick = () => selectLesson(card.dataset.id);
  });
}

function renderCards() {
  const shown = level === "All" ? lessons : lessons.filter(lesson => lesson.level === level);
  cards.innerHTML = `<p class="progress">${completed.length}/${lessons.length} lessons complete</p>` + shown.map(lesson => `
    <button class="card ${lesson.id === selected.id ? "selected" : ""}" data-id="${lesson.id}">
      <span class="pill">${lesson.level} · ${lesson.step}</span>
      <h3>${lesson.title} ${completed.includes(lesson.id) ? "✓" : ""}</h3>
      <p>${lesson.summary}</p>
      <span class="arrow">→</span>
    </button>`).join("");
  cards.querySelectorAll(".card").forEach(card => {
    card.onclick = () => selectLesson(card.dataset.id);
  });
}

function renderWorkspace() {
  const isComplete = completed.includes(selected.id);
  const check = checks[selected.id];
  const notebookLink = selected.notebook
    ? `<a class="button secondary" href="${link(selected.notebook)}" target="_blank">Open notebook lesson ↗</a>`
    : "";
  const content = tab === "learn"
    ? `<article><p class="eyebrow">OUTCOME</p><p class="outcome">${selected.outcome}</p><p class="eyebrow">THE IDEA</p><p>${selected.detail || "Start with the notebook lesson, then explain the system boundary, control loop, and trade-offs in your own words."}</p><p>The notebook is the primary training material: read the theory, inspect the diagram, run the implementation cells, trigger the failure case, and answer the architecture question.</p><a class="button" href="${link(selected.material)}" target="_blank">Open notebook lesson ↗</a></article>`
    : tab === "lab"
      ? `<article><p class="eyebrow">PRACTICAL LAB</p><p class="outcome">${selected.run || "Run the design, change one assumption, and inspect the failure mode."}</p><p>The Python module is the reusable implementation behind the notebook. Use it to inspect source, run deterministic examples, extend contracts, and keep policy checks outside the model.</p><a class="button" href="${link(selected.lab)}" target="_blank">Open implementation module ↗</a>${notebookLink}</article>`
      : `<article><p class="eyebrow">CHECKPOINT</p><ol><li><b>${check[0]}</b></li><li>What failure mode would you test for?</li><li>What evidence would convince you the design works?</li></ol><details><summary>Reveal an answer guide</summary><p>${check[1]}</p></details><a class="quiz-link" href="../quiz/index.html">Take the full graded Knowledge Check ↗</a></article>`;

  workspace.innerHTML = `<div class="workspace-head"><div><p class="eyebrow">LESSON ${selected.step} · ${selected.level.toUpperCase()}</p><h2>${selected.title}</h2></div><span class="pill">${selected.level}</span></div><div class="lesson-tabs"><button class="${tab === "learn" ? "active" : ""}" data-tab="learn">01 / Learn</button><button class="${tab === "lab" ? "active" : ""}" data-tab="lab">02 / Lab</button><button class="${tab === "checkpoint" ? "active" : ""}" data-tab="checkpoint">03 / Checkpoint</button></div><div class="lesson-grid">${content}<aside><p class="eyebrow">SOURCES</p>${selected.refs.map((ref, index) => `<a class="source" href="${link(ref)}" target="_blank"><span>0${index + 1}</span><b>${sourceLabel(ref)}</b><small>${ref}</small> ↗</a>`).join("")}<button class="complete" id="complete">${isComplete ? "Completed ✓" : "Mark lesson complete"}</button></aside></div>`;
  workspace.querySelectorAll("[data-tab]").forEach(button => {
    button.onclick = () => {
      tab = button.dataset.tab;
      renderWorkspace();
    };
  });
  document.querySelector("#complete").onclick = () => {
    completed = isComplete ? completed.filter(id => id !== selected.id) : [...completed, selected.id];
    localStorage.setItem("ai-agents-hub-progress", JSON.stringify(completed));
    renderCards();
    renderTrack();
    renderWorkspace();
  };
}

renderFilters();
renderTrack();
renderCards();
renderWorkspace();
