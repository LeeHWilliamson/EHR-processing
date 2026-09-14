const state = {
  patients: [],
  catalog: null,
  tools: [],
  selectedPatientId: null,
  finalized: false,
  validationAttempted: false,
  validationErrors: [],
  referenceRequest: 0,
  readerPatientId: null,
  readerData: null,
  readerCache: new Map(),
  task: null,
  taskFinalized: false,
  argumentVocabularies: {},
  noise: null,
  noiseSources: [],
  noiseFinalized: false,
  verificationResults: null,
  agentResults: null,
};

const storageKey = "synth-ehr-toolset-v1";
const taskStorageKey = "synth-ehr-task-v1";
const noiseStorageKey = "synth-ehr-noise-v1";
const byId = (id) => document.getElementById(id);

async function api(path, options = {}) {
  const response = await fetch(path, options);
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(payload.detail || `Request failed (${response.status})`);
  return payload;
}

function setStatus(element, message, kind = "") {
  element.textContent = message;
  element.className = `status ${kind}`.trim();
}

function normalizeToolName(value) {
  let normalized = value
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9_-]+/g, "_")
    .replace(/[_-]{2,}/g, "_")
    .replace(/^[_-]+|[_-]+$/g, "");
  if (normalized && !/^[a-z]/.test(normalized)) normalized = `tool_${normalized}`;
  return normalized.slice(0, 64);
}

function saveTools() {
  localStorage.setItem(storageKey, JSON.stringify({
    tools: state.tools,
    finalized: state.finalized,
    argumentVocabularies: state.argumentVocabularies,
  }));
}

function loadSavedTools() {
  try {
    const saved = JSON.parse(localStorage.getItem(storageKey));
    return Array.isArray(saved?.tools) ? saved : null;
  } catch (_) {
    return null;
  }
}

function saveTask() {
  if (state.task) localStorage.setItem(taskStorageKey, JSON.stringify({ task: state.task, finalized: state.taskFinalized }));
}

function loadSavedTask() {
  try {
    const saved = JSON.parse(localStorage.getItem(taskStorageKey));
    return saved?.task && typeof saved.task === "object" ? saved : null;
  } catch (_) {
    return null;
  }
}

function saveNoise() {
  if (state.noise) localStorage.setItem(noiseStorageKey, JSON.stringify({
    configuration: state.noise,
    finalized: state.noiseFinalized,
  }));
}

function loadSavedNoise() {
  try {
    const saved = JSON.parse(localStorage.getItem(noiseStorageKey));
    return typeof saved?.configuration?.enabled === "boolean" ? saved : null;
  } catch (_) {
    return null;
  }
}

function renderPatients() {
  const container = byId("patient-tiles");
  const select = byId("preview-patient");
  container.replaceChildren();
  select.replaceChildren();
  state.patients.forEach((patient) => {
    const option = document.createElement("option");
    option.value = patient.patient_id;
    option.textContent = `${patient.first_name} ${patient.last_name}`;
    select.append(option);
  });

  const grid = document.createElement("div");
  grid.className = "patient-grid";
  state.patients.forEach((patient) => {
    const card = document.createElement("div");
    card.className = `patient-card${patient.cohort_group === "diabetes_keep" ? " keep-patient" : ""}${patient.patient_id === state.selectedPatientId ? " selected" : ""}`;
    card.dataset.patientId = patient.patient_id;
    card.tabIndex = 0;
    card.setAttribute("role", "button");
    card.setAttribute("aria-label", `Select ${patient.first_name} ${patient.last_name} for tool testing`);
    const readerButton = document.createElement("button");
    readerButton.type = "button";
    readerButton.className = "patient-reader-button";
    readerButton.setAttribute("aria-label", `Read ${patient.first_name} ${patient.last_name}'s patient JSON`);
    readerButton.title = "Read patient JSON";
    readerButton.textContent = "📖";
    const name = document.createElement("strong");
    name.textContent = `${patient.first_name} ${patient.last_name}`;
    const details = document.createElement("small");
    details.textContent = `DOB ${patient.date_of_birth} · ${patient.gender}`;
    const counts = document.createElement("div");
    counts.className = "patient-counts";
    ["conditions", "medications", "careplans", "allergies"].forEach((entity) => {
      const chip = document.createElement("span");
      chip.textContent = `${patient.counts[entity] || 0} ${entity}`;
      counts.append(chip);
    });
    card.append(readerButton, name, details, counts);
    card.addEventListener("click", () => selectPatient(patient.patient_id));
    card.addEventListener("keydown", (event) => {
      if ((event.key === "Enter" || event.key === " ") && event.target === card) {
        event.preventDefault();
        selectPatient(patient.patient_id);
      }
    });
    readerButton.addEventListener("click", (event) => {
      event.stopPropagation();
      openPatientReader(patient.patient_id);
    });
    grid.append(card);
  });
  container.append(grid);
  select.value = state.selectedPatientId;
  select.addEventListener("change", () => selectPatient(select.value));
  setStatus(byId("population-status"), `${state.patients.length} synthetic patients loaded.`, "success");
}

function readerEndpoint(patientId) {
  return `/api/patients/${encodeURIComponent(patientId)}/original-view`;
}

function renderReaderRecord(record) {
  const content = byId("reader-content");
  content.replaceChildren();
  Object.entries(record).forEach(([entity, value], index) => {
    const section = document.createElement("details");
    section.className = "reader-entity";
    section.open = index === 0;
    const summary = document.createElement("summary");
    const label = document.createElement("strong");
    label.textContent = entity.replaceAll("_", " ");
    const count = document.createElement("span");
    if (Array.isArray(value)) count.textContent = `${value.length} record${value.length === 1 ? "" : "s"}`;
    else count.textContent = value && typeof value === "object" ? `${Object.keys(value).length} fields` : "1 value";
    summary.append(label, count);
    const formatted = document.createElement("pre");
    formatted.textContent = JSON.stringify(value, null, 2);
    section.append(summary, formatted);
    content.append(section);
  });
}

async function loadReaderView() {
  byId("reader-notice").textContent = "Original normalized Synthea record. Agent censorship is applied later, after the task is finalized.";
  setStatus(byId("reader-status"), "Loading record…");
  byId("reader-content").replaceChildren();
  byId("open-raw-json").disabled = true;
  const patientId = state.readerPatientId;
  const cacheKey = `${patientId}:original`;
  try {
    const record = state.readerCache.has(cacheKey)
      ? state.readerCache.get(cacheKey)
      : await api(readerEndpoint(patientId));
    if (patientId !== state.readerPatientId) return;
    state.readerCache.set(cacheKey, record);
    state.readerData = record;
    renderReaderRecord(record);
    setStatus(byId("reader-status"), `${Object.keys(record).length} sections loaded.`, "success");
    byId("open-raw-json").disabled = false;
  } catch (error) {
    setStatus(byId("reader-status"), error.message, "error");
  }
}

function openPatientReader(patientId) {
  const patient = state.patients.find((item) => item.patient_id === patientId);
  state.readerPatientId = patientId;
  state.readerData = null;
  byId("reader-title").textContent = patient ? `${patient.first_name} ${patient.last_name}` : "Patient record";
  byId("reader-subtitle").textContent = patientId;
  const dialog = byId("patient-reader");
  if (!dialog.open) dialog.showModal();
  loadReaderView();
}

function openRawJson() {
  if (!state.readerData) return;
  const blob = new Blob([JSON.stringify(state.readerData, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  window.open(url, "_blank", "noopener,noreferrer");
  window.setTimeout(() => URL.revokeObjectURL(url), 60000);
}

function selectPatient(patientId) {
  state.selectedPatientId = patientId;
  document.querySelectorAll(".patient-card").forEach((card) => {
    card.classList.toggle("selected", card.dataset.patientId === patientId);
  });
  byId("preview-patient").value = patientId;
  syncPreviewArgument();
}

function entityNames() {
  return Object.keys(state.catalog.entities).filter((name) => name !== "patient");
}

function sharedKeyFields(tool) {
  const entities = Object.keys(tool.returns);
  if (!entities.length) return ["patient_id"];
  const lists = entities.map((entity) => new Set(state.catalog.entities[entity]?.key_fields || []));
  return [...lists[0]].filter((field) => lists.every((fields) => fields.has(field)));
}

function input(className, value, onChange, multiline = false) {
  const wrapper = document.createElement("div");
  wrapper.className = className;
  const element = document.createElement(multiline ? "textarea" : "input");
  element.value = value;
  element.placeholder = multiline ? "Description" : "Tool Name";
  element.addEventListener("input", () => {
    onChange(element.value);
    refreshValidationHighlights();
  });
  if (className === "tool-name") {
    element.addEventListener("blur", () => {
      const normalized = normalizeToolName(element.value);
      if (normalized !== element.value) {
        element.value = normalized;
        onChange(normalized);
      }
      refreshValidationHighlights();
    });
  }
  wrapper.append(element);
  return wrapper;
}

function renderReturnGroup(tool, entity, rowIndex) {
  const group = document.createElement("div");
  group.className = "return-group";
  group.dataset.entity = entity;
  const head = document.createElement("div");
  head.className = "return-head";
  const entitySelect = document.createElement("select");
  entityNames().forEach((name) => {
    const option = document.createElement("option");
    option.value = name;
    option.textContent = name.replaceAll("_", " ");
    option.selected = name === entity;
    option.disabled = name !== entity && Object.prototype.hasOwnProperty.call(tool.returns, name);
    entitySelect.append(option);
  });
  entitySelect.addEventListener("change", () => {
    const fields = tool.returns[entity];
    delete tool.returns[entity];
    tool.returns[entitySelect.value] = fields.filter((field) => state.catalog.entities[entitySelect.value].fields[field]);
    if (!tool.returns[entitySelect.value].length) {
      tool.returns[entitySelect.value] = Object.keys(state.catalog.entities[entitySelect.value].fields).slice(0, 4);
    }
    renderTools();
  });
  const remove = document.createElement("button");
  remove.type = "button";
  remove.className = "icon-button";
  remove.setAttribute("aria-label", `Remove ${entity} return`);
  remove.textContent = "×";
  remove.disabled = Object.keys(tool.returns).length === 1;
  remove.addEventListener("click", () => { delete tool.returns[entity]; renderTools(); });
  head.append(entitySelect, remove);

  const fields = document.createElement("div");
  fields.className = "field-picker";
  Object.keys(state.catalog.entities[entity].fields).forEach((field) => {
    const label = document.createElement("label");
    label.className = "field-chip";
    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.checked = tool.returns[entity].includes(field);
    checkbox.addEventListener("change", () => {
      const chosen = new Set(tool.returns[entity]);
      checkbox.checked ? chosen.add(field) : chosen.delete(field);
      tool.returns[entity] = [...chosen];
      saveTools();
      refreshValidationHighlights();
    });
    const text = document.createElement("span");
    text.textContent = field;
    label.append(checkbox, text);
    fields.append(label);
  });
  group.append(head, fields);
  return group;
}

function renderTools() {
  const list = byId("tool-list");
  list.replaceChildren();
  list.classList.toggle("finalized", state.finalized);
  state.tools.forEach((tool, index) => {
    const row = document.createElement("article");
    row.className = "tool-row";
    row.dataset.toolIndex = String(index);
    const name = input("tool-name", tool.name, (value) => { tool.name = value; saveTools(); refreshPreviewTools(); });
    const description = input("tool-description", tool.description, (value) => { tool.description = value; saveTools(); }, true);
    const returns = document.createElement("div");
    returns.className = "tool-returns";
    Object.keys(tool.returns).forEach((entity, entityIndex) => {
      if (entityIndex > 0) {
        const conjunction = document.createElement("div");
        conjunction.className = "return-conjunction";
        conjunction.textContent = "AND";
        returns.append(conjunction);
      }
      returns.append(renderReturnGroup(tool, entity, index));
    });
    const addReturn = document.createElement("button");
    addReturn.type = "button";
    addReturn.className = "add-return";
    addReturn.textContent = "+ Return another entity";
    addReturn.addEventListener("click", () => {
      const unused = entityNames().find((entity) => !(entity in tool.returns));
      if (unused) {
        tool.returns[unused] = Object.keys(state.catalog.entities[unused].fields).slice(0, 4);
        renderTools();
      }
    });
    returns.append(addReturn);

    const keyWrap = document.createElement("div");
    keyWrap.className = "tool-key";
    const keySelect = document.createElement("select");
    const keys = sharedKeyFields(tool);
    if (!keys.includes(tool.key.field)) tool.key.field = "patient_id";
    keys.forEach((field) => {
      const option = document.createElement("option");
      option.value = field;
      option.textContent = field.replaceAll("_", " ");
      option.selected = field === tool.key.field;
      keySelect.append(option);
    });
    keySelect.addEventListener("change", () => { tool.key.field = keySelect.value; saveTools(); syncPreviewArgument(); });
    keyWrap.append(keySelect);

    const removeTool = document.createElement("button");
    removeTool.type = "button";
    removeTool.className = "icon-button";
    removeTool.setAttribute("aria-label", `Remove ${tool.name}`);
    removeTool.textContent = "×";
    removeTool.addEventListener("click", () => { state.tools.splice(index, 1); renderTools(); });
    const errors = document.createElement("ul");
    errors.className = "tool-errors";
    row.append(name, description, returns, keyWrap, removeTool, errors);
    row.querySelectorAll("input, select, textarea, button").forEach((control) => { control.disabled = state.finalized; });
    list.append(row);
  });
  byId("add-tool").disabled = state.finalized;
  byId("finalize-tools").disabled = state.finalized;
  byId("edit-tools").disabled = !state.finalized;
  saveTools();
  refreshPreviewTools();
  refreshValidationHighlights();
  if (state.task) renderTask();
}

function refreshPreviewTools() {
  const select = byId("preview-tool");
  const previous = select.value;
  select.replaceChildren();
  state.tools.forEach((tool, index) => {
    const option = document.createElement("option");
    option.value = String(index);
    option.textContent = tool.name || `Tool ${index + 1}`;
    select.append(option);
  });
  if ([...select.options].some((option) => option.value === previous)) select.value = previous;
  syncPreviewArgument();
}

async function syncPreviewArgument() {
  const tool = state.tools[Number(byId("preview-tool")?.value || 0)];
  const argumentSelect = byId("preview-argument");
  const runButton = byId("run-preview");
  argumentSelect.replaceChildren();
  runButton.disabled = true;
  const requestNumber = ++state.referenceRequest;
  if (!tool) return;
  byId("preview-argument-wrap").firstChild.textContent = `${tool.key.field.replaceAll("_", " ")} `;
  const placeholder = document.createElement("option");
  if (!state.finalized) {
    placeholder.textContent = "Finalize the toolset to load arguments";
    argumentSelect.append(placeholder);
    return;
  }
  placeholder.textContent = "Loading valid arguments…";
  argumentSelect.append(placeholder);
  try {
    const lockedVocabulary = state.argumentVocabularies[tool.id];
    const result = lockedVocabulary?.scope === "cohort"
      ? { options: lockedVocabulary.options }
      : await api("/api/tool-design/references", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ tool, assigned_patient_id: state.selectedPatientId }),
      });
    if (requestNumber !== state.referenceRequest) return;
    argumentSelect.replaceChildren();
    result.options.forEach((reference) => {
      const option = document.createElement("option");
      option.value = reference.value;
      option.textContent = reference.label;
      argumentSelect.append(option);
    });
    if (!result.options.length) {
      const empty = document.createElement("option");
      empty.textContent = "No valid arguments in the cohort vocabulary";
      argumentSelect.append(empty);
    }
    runButton.disabled = !state.finalized || !result.options.length;
  } catch (_) {
    if (requestNumber !== state.referenceRequest) return;
    argumentSelect.replaceChildren();
    const unavailable = document.createElement("option");
    unavailable.textContent = "Arguments unavailable for this tool";
    argumentSelect.append(unavailable);
  }
}

function newTool() {
  const suffix = Date.now().toString(36);
  return {
    id: `custom_${suffix}`,
    name: `custom_tool_${state.tools.length + 1}`,
    description: "Describe what this tool returns and when the agent should use it.",
    key: { field: "patient_id", operator: "equals" },
    returns: { observations: ["description", "value", "units", "date"] },
  };
}

function localValidationErrors() {
  const errors = [];
  if (!state.tools.length) {
    errors.push({ scope: "toolset", message: "Add at least one tool before finalizing the toolset." });
    return errors;
  }
  if (state.tools.length > 15) {
    errors.push({ scope: "toolset", message: "The toolset can contain no more than 15 tools. Remove at least one tool." });
  }
  const nameGroups = new Map();
  state.tools.forEach((tool, toolIndex) => {
    const name = tool.name.trim();
    if (!name) errors.push({ scope: "tool", toolIndex, field: "name", message: "Give this tool a name." });
    if (name) nameGroups.set(name, [...(nameGroups.get(name) || []), toolIndex]);
    if (!tool.description.trim()) {
      errors.push({ scope: "tool", toolIndex, field: "description", message: "Please add a description." });
    }
    if (!Object.keys(tool.returns).length) {
      errors.push({ scope: "tool", toolIndex, field: "returns", message: "Choose at least one entity to return." });
    }
    Object.entries(tool.returns).forEach(([entity, fields]) => {
      if (!fields.length) {
        errors.push({ scope: "tool", toolIndex, field: "returns", entity, message: `Select at least one ${entity.replaceAll("_", " ")} field.` });
      }
    });
  });
  nameGroups.forEach((indexes) => {
    if (indexes.length > 1) indexes.forEach((toolIndex) => {
      errors.push({ scope: "tool", toolIndex, field: "name", message: "This tool name is duplicated. Give it a unique name." });
    });
  });
  return errors;
}

function applyValidationHighlights(errors) {
  const list = byId("tool-list");
  list.classList.toggle("invalid-list", errors.some((error) => error.scope === "toolset"));
  list.querySelectorAll(".tool-row").forEach((row) => {
    row.classList.remove("invalid-tool");
    row.querySelectorAll(".invalid-control").forEach((element) => element.classList.remove("invalid-control"));
    row.querySelector(".tool-errors").replaceChildren();
  });
  errors.filter((error) => error.scope === "tool").forEach((error) => {
    const row = list.querySelector(`[data-tool-index="${error.toolIndex}"]`);
    if (!row) return;
    row.classList.add("invalid-tool");
    let control;
    if (error.field === "name") control = row.querySelector(".tool-name input");
    if (error.field === "description") control = row.querySelector(".tool-description textarea");
    if (error.field === "returns") {
      control = error.entity
        ? row.querySelector(`.return-group[data-entity="${CSS.escape(error.entity)}"]`)
        : row.querySelector(".tool-returns");
    }
    control?.classList.add("invalid-control");
    const item = document.createElement("li");
    item.textContent = error.message;
    row.querySelector(".tool-errors").append(item);
  });
}

function refreshValidationHighlights() {
  if (!state.validationAttempted) return;
  state.validationErrors = localValidationErrors();
  applyValidationHighlights(state.validationErrors);
  if (!state.validationErrors.length) {
    setStatus(byId("tool-status"), "All visible issues are fixed. Finalize the toolset when ready.", "success");
  }
}

async function finalizeTools() {
  state.validationAttempted = true;
  state.validationErrors = localValidationErrors();
  applyValidationHighlights(state.validationErrors);
  if (state.validationErrors.length) {
    const toolsetError = state.validationErrors.find((error) => error.scope === "toolset");
    setStatus(
      byId("tool-status"),
      toolsetError?.message || "Some tools are invalid. Please examine tools highlighted in red.",
      "error",
    );
    byId("tool-list").querySelector(".invalid-control, input, textarea, select")?.focus();
    return;
  }
  try {
    const result = await api("/api/tool-design/validate", {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ tools: state.tools }),
    });
    state.argumentVocabularies = result.argument_vocabularies;
    state.finalized = true;
    state.validationAttempted = false;
    state.validationErrors = [];
    renderTools();
    setStatus(byId("tool-status"), `${state.tools.length} tools finalized. Choose Edit toolset to make changes.`, "success");
  } catch (error) {
    setStatus(byId("tool-status"), error.message, "error");
  }
}

function editTools() {
  if (state.task?.ideal_workflow?.length) {
    const confirmed = window.confirm(
      "Editing the toolset will clear the ideal workflow because its steps depend on the current tools. Continue?",
    );
    if (!confirmed) return;
    state.task.ideal_workflow = [];
  }
  invalidateVerification();
  state.finalized = false;
  state.argumentVocabularies = {};
  state.taskFinalized = false;
  state.noiseFinalized = false;
  state.validationAttempted = false;
  state.validationErrors = [];
  renderTools();
  renderTask();
  renderNoise();
  setStatus(byId("tool-status"), "Editing enabled. Finalize the toolset again before continuing.");
}

async function previewTool() {
  const tool = state.tools[Number(byId("preview-tool").value)];
  if (!tool) return;
  setStatus(byId("preview-summary"), "Running tool…");
  try {
    const result = await api("/api/tool-design/preview", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        tool,
        assigned_patient_id: state.selectedPatientId,
        argument: byId("preview-argument").value,
      }),
    });
    byId("preview-output").textContent = JSON.stringify(result.output, null, 2);
    setStatus(
      byId("preview-summary"),
      `${result.audit.records_returned} records returned · ${result.audit.elapsed_ms} ms`,
      "success",
    );
  } catch (error) {
    setStatus(byId("preview-summary"), error.message, "error");
  }
}

async function resetDefaults() {
  invalidateVerification();
  const defaults = await api("/api/tool-design/defaults");
  state.tools = defaults.tools;
  state.finalized = false;
  state.validationAttempted = false;
  state.validationErrors = [];
  state.argumentVocabularies = {};
  state.taskFinalized = false;
  state.noiseFinalized = false;
  renderTools();
  renderTask();
  renderNoise();
  setStatus(byId("tool-status"), "Default patient-ID tools restored.", "success");
}

function updateTaskCount(field) {
  byId(`${field}-count`).textContent = String(byId(field).value.length);
}

function renderWorkflow() {
  const list = byId("workflow-list");
  list.replaceChildren();
  byId("workflow-empty").hidden = state.task.ideal_workflow.length > 0;
  state.task.ideal_workflow.forEach((step, index) => {
    const row = document.createElement("div");
    row.className = "workflow-step";
    const number = document.createElement("span");
    number.className = "workflow-step-number";
    number.textContent = String(index + 1);
    const toolSelect = document.createElement("select");
    toolSelect.setAttribute("aria-label", `Tool call ${index + 1}`);
    state.tools.forEach((tool) => {
      const option = document.createElement("option");
      option.value = tool.id;
      option.textContent = tool.name;
      option.selected = tool.id === step.tool_id;
      toolSelect.append(option);
    });
    toolSelect.addEventListener("change", () => {
      step.tool_id = toolSelect.value;
      saveTask();
      renderWorkflow();
    });
    const remove = document.createElement("button");
    remove.type = "button";
    remove.className = "icon-button";
    remove.setAttribute("aria-label", `Remove workflow step ${index + 1}`);
    remove.textContent = "×";
    remove.addEventListener("click", () => {
      state.task.ideal_workflow.splice(index, 1);
      saveTask();
      renderWorkflow();
    });
    row.append(number, toolSelect, remove);
    row.querySelectorAll("select, button").forEach((control) => { control.disabled = state.taskFinalized; });
    list.append(row);
  });
}

function renderTask() {
  if (!state.task) return;
  const bindings = [
    ["task-name", "name"],
    ["task-description", "description"],
    ["task-type", "task_type"],
    ["task-condition", "condition"],
    ["system-instructions", "system_instructions"],
    ["user-instructions", "user_instructions"],
  ];
  bindings.forEach(([elementId, property]) => {
    const element = byId(elementId);
    element.value = state.task[property];
    element.disabled = state.taskFinalized;
    element.oninput = () => {
      state.task[property] = element.value;
      if (elementId !== "task-type" && elementId !== "task-condition") updateTaskCount(elementId);
      saveTask();
    };
  });
  ["task-name", "task-description", "system-instructions", "user-instructions"].forEach(updateTaskCount);
  renderWorkflow();
  byId("task-form").classList.toggle("finalized", state.taskFinalized);
  byId("add-workflow-step").disabled = state.taskFinalized || !state.finalized || !state.tools.length || state.task.ideal_workflow.length >= 20;
  byId("finalize-task").disabled = state.taskFinalized || !state.finalized;
  byId("edit-task").disabled = !state.taskFinalized;
  saveTask();
}

function addWorkflowStep() {
  const tool = state.tools[0];
  if (!tool || state.task.ideal_workflow.length >= 20) return;
  state.task.ideal_workflow.push({ tool_id: tool.id });
  saveTask();
  renderWorkflow();
}

function localTaskError() {
  if (!state.finalized) return "Finalize the toolset before finalizing the task.";
  if (!state.task.name.trim()) return "Give the task a name.";
  if (!state.task.description.trim()) return "Give the task a description.";
  if (!state.task.system_instructions.trim()) return "Add system instructions.";
  if (!state.task.user_instructions.trim()) return "Add user instructions.";
  return null;
}

async function finalizeTask() {
  const localError = localTaskError();
  if (localError) {
    setStatus(byId("task-status"), localError, "error");
    return;
  }
  try {
    const result = await api("/api/task-design/validate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ task: state.task, toolset: { tools: state.tools } }),
    });
    state.task = result.task;
    state.taskFinalized = true;
    renderTask();
    renderNoise();
    setStatus(byId("task-status"), "Task finalized. Choose Edit task to make changes.", "success");
  } catch (error) {
    setStatus(byId("task-status"), error.message, "error");
  }
}

function editTask() {
  invalidateVerification();
  state.taskFinalized = false;
  state.noiseFinalized = false;
  renderTask();
  renderNoise();
  setStatus(byId("task-status"), "Editing enabled. Finalize the task again before continuing.");
}

function renderNoise() {
  if (!state.noise) return;
  const enabled = state.noise.enabled;
  const sources = byId("noise-sources");
  sources.classList.toggle("disabled", !enabled);
  sources.classList.toggle("finalized", state.noiseFinalized);
  const toggle = byId("toggle-noise");
  toggle.textContent = enabled ? "Disable noise" : "Enable noise";
  toggle.disabled = state.noiseFinalized;
  toggle.classList.toggle("danger", enabled);
  toggle.classList.toggle("secondary", !enabled);
  byId("finalize-noise").disabled = state.noiseFinalized || !state.taskFinalized;
  byId("edit-noise").disabled = !state.noiseFinalized;
  saveNoise();
  renderVerificationState();
  renderAgentState();
}

function invalidateVerification() {
  state.verificationResults = null;
  const results = byId("verification-results");
  if (results) results.replaceChildren();
  invalidateAgentResults();
}

function invalidateAgentResults() {
  state.agentResults = null;
  const results = byId("agent-results");
  if (results) results.replaceChildren();
  const dashboard = byId("summary-dashboard");
  if (dashboard) dashboard.hidden = true;
  const empty = byId("summary-empty");
  if (empty) empty.hidden = false;
  const filter = byId("summary-patient-filter");
  if (filter) filter.disabled = true;
}

function toggleNoise() {
  invalidateVerification();
  state.noise.enabled = !state.noise.enabled;
  renderNoise();
  setStatus(
    byId("noise-status"),
    state.noise.enabled
      ? "Both predefined noise sources are enabled."
      : "Noise is disabled. Agent records will remain unchanged after baseline censorship.",
    state.noise.enabled ? "" : "success",
  );
}

async function finalizeNoise() {
  if (!state.taskFinalized) {
    setStatus(byId("noise-status"), "Finalize the task before finalizing noise.", "error");
    return;
  }
  try {
    const result = await api("/api/noise/validate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(state.noise),
    });
    state.noise = result.configuration;
    state.noiseFinalized = true;
    renderNoise();
    if (!state.noise.enabled) {
      setStatus(byId("noise-status"), "Noise disabled and finalized. No noise edits will be produced.", "success");
      return;
    }
    const impact = result.impact;
    setStatus(
      byId("noise-status"),
      `Noise finalized · ${impact.observations_jittered} glucose observations jittered · ${impact.conditions_censored} conditions censored across ${impact.patients_affected} patients.`,
      "success",
    );
  } catch (error) {
    setStatus(byId("noise-status"), error.message, "error");
  }
}

function editNoise() {
  invalidateVerification();
  state.noiseFinalized = false;
  renderNoise();
  setStatus(byId("noise-status"), "Editing enabled. Enable or disable noise, then finalize again.");
}

function renderVerificationState() {
  const button = byId("run-verification");
  if (!button) return;
  button.disabled = !state.noiseFinalized;
  if (!state.noiseFinalized && !state.verificationResults) {
    setStatus(byId("verification-status"), "Finalize the noise configuration to verify the task.");
  }
}

function verificationStatusLabel(status) {
  return {
    unchanged: "Unchanged",
    modified_by_noise: "Modified by noise",
    missing_after_noise: "Missing after noise",
    baseline_censored: "Removed by baseline censorship",
    modified_by_baseline: "Modified by baseline censorship",
  }[status] || status.replaceAll("_", " ");
}

function renderVerificationResults(result) {
  const container = byId("verification-results");
  container.replaceChildren();
  result.patients.forEach((patient) => {
    const card = document.createElement("button");
    card.type = "button";
    card.className = `verification-card ${patient.status}`;
    const name = document.createElement("strong");
    name.textContent = patient.patient_name;
    const diagnosis = document.createElement("small");
    diagnosis.textContent = patient.has_type_2_diabetes ? "Ground truth: diabetes present" : "Ground truth: diabetes absent";
    const coverage = document.createElement("div");
    coverage.className = "verification-count";
    coverage.textContent = `${patient.counts.accessible_after_noise} / ${patient.counts.baseline_accessible}`;
    const caption = document.createElement("p");
    caption.textContent = "baseline-accessible records retained after noise";
    card.append(name, diagnosis, coverage, caption);
    card.addEventListener("click", () => openVerificationReport(patient));
    container.append(card);
  });
}

function verificationStat(value, label) {
  const stat = document.createElement("div");
  stat.className = "verification-stat";
  const number = document.createElement("strong");
  number.textContent = String(value);
  const text = document.createElement("span");
  text.textContent = label;
  stat.append(number, text);
  return stat;
}

function openVerificationReport(patient) {
  byId("verification-reader-title").textContent = patient.patient_name;
  byId("verification-reader-subtitle").textContent = `${patient.patient_id} · ${patient.has_type_2_diabetes ? "diabetes present" : "diabetes absent"}`;
  const summary = byId("verification-reader-summary");
  summary.replaceChildren(
    verificationStat(patient.counts.expected, "Expected evidence records"),
    verificationStat(patient.counts.accessible_after_noise, "Accessible after noise"),
    verificationStat(patient.counts.modified_by_noise, "Modified by noise"),
    verificationStat(patient.counts.missing_after_noise, "Removed by noise"),
    verificationStat(patient.counts.baseline_censored, "Removed by baseline"),
    verificationStat(patient.counts.modified_by_baseline, "Modified by baseline"),
  );
  const records = byId("verification-reader-content");
  records.replaceChildren();
  patient.records.forEach((record) => {
    const row = document.createElement("article");
    row.className = `verification-record ${record.status}`;
    const header = document.createElement("div");
    header.className = "verification-record-header";
    const title = document.createElement("strong");
    title.textContent = record.description || record.record_id;
    const status = document.createElement("span");
    status.textContent = verificationStatusLabel(record.status);
    header.append(title, status);
    const metadata = document.createElement("p");
    metadata.textContent = `${record.entity} · ${record.record_id}${record.date ? ` · ${record.date}` : ""}`;
    row.append(header, metadata);
    if (record.noise_edit) {
      const edit = document.createElement("div");
      edit.className = "noise-edit";
      edit.textContent = record.noise_edit.operation === "jitter_observation"
        ? `value: ${record.noise_edit.original_value} → ${record.noise_edit.resulting_value}`
        : "condition record → removed";
      row.append(edit);
    }
    records.append(row);
  });
  byId("verification-reader").showModal();
}

async function runVerification() {
  byId("run-verification").disabled = true;
  setStatus(byId("verification-status"), "Verifying evidence across all ten patient records…");
  try {
    const result = await api("/api/verification/run", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(state.noise),
    });
    state.verificationResults = result;
    renderVerificationResults(result);
    const summary = result.summary;
    setStatus(
      byId("verification-status"),
      `${summary.patients_verified} patients verified · ${summary.green} preserved · ${summary.amber} modified · ${summary.red} with evidence removed by noise.`,
      summary.red ? "error" : "success",
    );
  } catch (error) {
    setStatus(byId("verification-status"), error.message, "error");
  } finally {
    renderVerificationState();
  }
}

function renderAgentState() {
  const button = byId("run-agent");
  if (!button) return;
  const ready = state.finalized && state.taskFinalized && state.noiseFinalized;
  button.disabled = !ready;
  if (!ready && !state.agentResults) {
    setStatus(byId("agent-status"), "Finalize the toolset, task, and noise configuration to run the agent.");
  }
}

function renderAgentResults(result) {
  const container = byId("agent-results");
  container.replaceChildren();
  result.patients.forEach((patient) => {
    const card = document.createElement("button");
    card.type = "button";
    card.className = `agent-card ${patient.correct ? "correct" : "incorrect"}`;
    const name = document.createElement("strong");
    name.textContent = patient.patient_name;
    const expected = document.createElement("small");
    expected.textContent = `Expected: ${patient.expected_diagnosis || "unavailable"}`;
    const outcome = document.createElement("div");
    outcome.className = "agent-outcome";
    outcome.textContent = patient.error ? "Run failed" : `Agent: ${patient.diagnosis}`;
    const coverage = document.createElement("div");
    coverage.className = "agent-coverage";
    coverage.textContent = `${patient.records_found} / ${patient.total_records} relevant records found`;
    card.append(name, expected, outcome, coverage);
    card.addEventListener("click", () => openAgentReport(patient));
    container.append(card);
  });
}

function renderAgentRecordGroups(container, records) {
  container.replaceChildren();
  if (!records.length) {
    const empty = document.createElement("p");
    empty.textContent = "None";
    container.append(empty);
    return;
  }
  const grouped = new Map();
  records.forEach((record) => {
    if (!grouped.has(record.entity)) grouped.set(record.entity, []);
    grouped.get(record.entity).push(record);
  });
  [...grouped.entries()].sort(([a], [b]) => a.localeCompare(b)).forEach(([entity, items]) => {
    const group = document.createElement("details");
    group.className = "agent-record-group";
    const summary = document.createElement("summary");
    summary.textContent = `${entity.replaceAll("_", " ")} (${items.length})`;
    const list = document.createElement("ul");
    items.forEach((record) => {
      const item = document.createElement("li");
      item.textContent = `${record.description} — ${record.record_id}`;
      list.append(item);
    });
    group.append(summary, list);
    container.append(group);
  });
}

function openAgentReport(patient) {
  byId("agent-reader-title").textContent = patient.patient_name;
  byId("agent-reader-subtitle").textContent = patient.patient_id;
  const diagnosis = byId("agent-reader-diagnosis");
  diagnosis.className = `agent-diagnosis${patient.correct ? "" : " incorrect"}`;
  diagnosis.replaceChildren();
  const outcome = document.createElement("strong");
  outcome.textContent = patient.error
    ? "Agent run failed"
    : `${patient.diagnosis} · ${patient.correct ? "correct" : "incorrect"}`;
  const explanation = document.createElement("p");
  explanation.textContent = patient.error || patient.explanation || "No explanation returned.";
  diagnosis.append(outcome, explanation);
  byId("found-records-title").textContent = `Relevant records found (${patient.records_found})`;
  byId("missed-records-title").textContent = `Relevant records missed (${patient.total_records - patient.records_found})`;
  renderAgentRecordGroups(byId("agent-found-records"), patient.found_records || []);
  renderAgentRecordGroups(byId("agent-missed-records"), patient.missed_records || []);
  byId("agent-reader").showModal();
}

function appendAgentActivity(message, kind = "") {
  const activity = byId("agent-activity");
  const line = document.createElement("div");
  line.className = kind;
  line.textContent = message;
  activity.append(line);
  while (activity.children.length > 200) activity.firstChild.remove();
  activity.scrollTop = activity.scrollHeight;
}

function handleAgentProgressEvent(event, partialResults) {
  if (event.type === "patient_started") {
    byId("agent-progress-label").textContent = `Evaluating ${event.patient_name}`;
    byId("agent-progress-count").textContent = `${event.patient_number - 1} / ${event.patient_total} patients`;
    appendAgentActivity(`Patient ${event.patient_number}/${event.patient_total}: ${event.patient_name} started`);
  } else if (event.type === "tool_completed") {
    appendAgentActivity(`${event.tool_name} → ${event.records_returned} records`);
  } else if (event.type === "tool_error") {
    appendAgentActivity(`${event.tool_name} failed: ${event.message}`, "error");
  } else if (event.type === "patient_completed") {
    partialResults.push(event.result);
    byId("agent-progress-bar").value = event.patient_number;
    byId("agent-progress-count").textContent = `${event.patient_number} / ${event.patient_total} patients`;
    appendAgentActivity(
      `${event.result.patient_name} complete: ${event.result.error ? "run failed" : `diagnosis ${event.result.diagnosis}`}`,
      event.result.error ? "error" : "",
    );
    renderAgentResults({ patients: partialResults });
  }
}

function metricCard(value, label) {
  const card = document.createElement("div");
  card.className = "metric-card";
  const number = document.createElement("strong");
  number.textContent = value;
  const text = document.createElement("span");
  text.textContent = label;
  card.append(number, text);
  return card;
}

function percent(numerator, denominator) {
  return denominator ? `${Math.round((numerator / denominator) * 100)}%` : "—";
}

function filteredSummaryPatients() {
  const value = byId("summary-patient-filter").value;
  const patients = state.agentResults?.patients || [];
  if (value === "positive") return patients.filter((patient) => patient.expected_diagnosis === "present");
  if (value === "negative") return patients.filter((patient) => patient.expected_diagnosis === "absent");
  if (value.startsWith("patient:")) return patients.filter((patient) => patient.patient_id === value.slice(8));
  return patients;
}

function renderBar(container, label, found, total) {
  const row = document.createElement("div");
  const header = document.createElement("div");
  header.className = "bar-row-header";
  const name = document.createElement("strong");
  name.textContent = label;
  const value = document.createElement("span");
  value.textContent = `${found} / ${total} · ${percent(found, total)}`;
  header.append(name, value);
  const track = document.createElement("div");
  track.className = "bar-track";
  const fill = document.createElement("div");
  fill.className = `bar-fill${total && found / total < .5 ? " low" : ""}`;
  fill.style.width = total ? `${(found / total) * 100}%` : "0%";
  track.append(fill);
  row.append(header, track);
  container.append(row);
}

function longestCommonSubsequence(first, second) {
  const rows = Array.from({ length: first.length + 1 }, () => Array(second.length + 1).fill(0));
  for (let i = 1; i <= first.length; i += 1) {
    for (let j = 1; j <= second.length; j += 1) {
      rows[i][j] = first[i - 1] === second[j - 1]
        ? rows[i - 1][j - 1] + 1
        : Math.max(rows[i - 1][j], rows[i][j - 1]);
    }
  }
  return rows[first.length][second.length];
}

function svgElement(name, attributes = {}) {
  const element = document.createElementNS("http://www.w3.org/2000/svg", name);
  Object.entries(attributes).forEach(([key, value]) => element.setAttribute(key, String(value)));
  return element;
}

function mostCommonTransition(toolName, transitions, direction) {
  const candidates = [];
  transitions.forEach((count, key) => {
    const [from, to] = key.split("\u0000");
    if (direction === "preceding" && to === toolName) candidates.push({ name: from, count });
    if (direction === "subsequent" && from === toolName) candidates.push({ name: to, count });
  });
  candidates.sort((first, second) => second.count - first.count || first.name.localeCompare(second.name));
  return candidates[0] || null;
}

function toolNodeStat(label, value, detail) {
  const stat = document.createElement("div");
  stat.className = "tool-node-stat";
  const heading = document.createElement("span");
  heading.textContent = label;
  const main = document.createElement("strong");
  main.textContent = value;
  const caption = document.createElement("small");
  caption.textContent = detail;
  stat.append(heading, main, caption);
  return stat;
}

function openToolNodeReport(toolName, callCounts, transitions) {
  const preceding = mostCommonTransition(toolName, transitions, "preceding");
  const subsequent = mostCommonTransition(toolName, transitions, "subsequent");
  byId("tool-node-title").textContent = toolName;
  byId("tool-node-filter").textContent = `Current filter: ${byId("summary-patient-filter").selectedOptions[0]?.textContent || "All patients"}`;
  byId("tool-node-metrics").replaceChildren(
    toolNodeStat("Total calls", String(callCounts.get(toolName) || 0), "Times this tool was called"),
    toolNodeStat(
      "Most common preceding tool",
      preceding?.name || "None",
      preceding ? `${preceding.count} preceding transition${preceding.count === 1 ? "" : "s"}` : "This tool had no recorded predecessor",
    ),
    toolNodeStat(
      "Most common subsequent tool",
      subsequent?.name || "None",
      subsequent ? `${subsequent.count} subsequent transition${subsequent.count === 1 ? "" : "s"}` : "This tool had no recorded successor",
    ),
  );
  byId("tool-node-reader").showModal();
}

function toolNodeLabelLines(name) {
  const words = name.split(/[_-]+/).filter(Boolean).map((word) => (
    word.length > 11 ? `${word.slice(0, 10)}…` : word
  ));
  const lines = [];
  words.forEach((word) => {
    const current = lines[lines.length - 1];
    if (current && `${current} ${word}`.length <= 11) lines[lines.length - 1] = `${current} ${word}`;
    else lines.push(word);
  });
  if (lines.length > 2) return [lines[0], `${lines.slice(1).join(" ").slice(0, 10)}…`];
  return lines.length ? lines : ["Unnamed"];
}

function renderToolMap(patients) {
  const svg = byId("tool-call-map");
  svg.replaceChildren();
  const definitions = svgElement("defs");
  const marker = svgElement("marker", { id: "map-arrow", viewBox: "0 0 10 10", refX: 9, refY: 5, markerWidth: 6, markerHeight: 6, orient: "auto-start-reverse" });
  marker.append(svgElement("path", { d: "M 0 0 L 10 5 L 0 10 z", fill: "#7950b5" }));
  definitions.append(marker);
  svg.append(definitions);
  const names = state.tools.map((tool) => tool.name);
  if (!names.length) return;
  const callCounts = new Map(names.map((name) => [name, 0]));
  const transitions = new Map();
  patients.forEach((patient) => {
    const sequence = (patient.tool_calls || []).map((call) => call.tool_name).filter((name) => callCounts.has(name));
    sequence.forEach((name) => callCounts.set(name, callCounts.get(name) + 1));
    sequence.slice(1).forEach((name, index) => {
      const key = `${sequence[index]}\u0000${name}`;
      transitions.set(key, (transitions.get(key) || 0) + 1);
    });
  });
  const maxCalls = Math.max(1, ...callCounts.values());
  const maxTransitions = Math.max(1, ...transitions.values());
  const center = { x: 350, y: 260 };
  const radius = Math.min(205, 46 + names.length * 13);
  const positions = new Map(names.map((name, index) => {
    const angle = -Math.PI / 2 + (index * Math.PI * 2) / names.length;
    return [name, { x: center.x + radius * Math.cos(angle), y: center.y + radius * Math.sin(angle) }];
  }));
  transitions.forEach((count, key) => {
    const [from, to] = key.split("\u0000");
    const start = positions.get(from);
    const end = positions.get(to);
    if (!start || !end) return;
    let pathData;
    if (from === to) {
      pathData = `M ${start.x - 17} ${start.y - 20} C ${start.x - 62} ${start.y - 75}, ${start.x + 62} ${start.y - 75}, ${start.x + 17} ${start.y - 20}`;
    } else {
      const dx = end.x - start.x;
      const dy = end.y - start.y;
      const distance = Math.hypot(dx, dy);
      const ux = dx / distance;
      const uy = dy / distance;
      const sx = start.x + ux * 34;
      const sy = start.y + uy * 34;
      const ex = end.x - ux * 37;
      const ey = end.y - uy * 37;
      const bend = from.localeCompare(to) < 0 ? 12 : -12;
      const mx = (sx + ex) / 2 - uy * bend;
      const my = (sy + ey) / 2 + ux * bend;
      pathData = `M ${sx} ${sy} Q ${mx} ${my} ${ex} ${ey}`;
    }
    const path = svgElement("path", {
      d: pathData,
      class: "map-edge",
      "stroke-width": 1.5 + (count / maxTransitions) * 6,
      "marker-end": "url(#map-arrow)",
    });
    const title = svgElement("title");
    title.textContent = `${from} → ${to}: ${count}`;
    path.append(title);
    svg.append(path);
  });
  names.forEach((name) => {
    const position = positions.get(name);
    const count = callCounts.get(name);
    const group = svgElement("g", {
      class: "map-node-button",
      role: "button",
      tabindex: 0,
      "aria-label": `Open statistics for ${name}`,
    });
    const node = svgElement("circle", {
      cx: position.x, cy: position.y, r: 32, class: "map-node",
      fill: `rgba(18, 107, 85, ${0.1 + (count / maxCalls) * 0.78})`,
    });
    const title = svgElement("title");
    title.textContent = `${name}: ${count} calls`;
    node.append(title);
    const nameLines = toolNodeLabelLines(name);
    const label = svgElement("text", { x: position.x, y: position.y - (nameLines.length === 2 ? 9 : 4), class: "map-node-label" });
    nameLines.forEach((line, index) => {
      const textLine = svgElement("tspan", { x: position.x, dy: index === 0 ? 0 : 10 });
      textLine.textContent = line;
      label.append(textLine);
    });
    const callLine = svgElement("tspan", { x: position.x, dy: 11 });
    callLine.textContent = `${count} call${count === 1 ? "" : "s"}`;
    label.append(callLine);
    group.append(node, label);
    group.addEventListener("click", () => openToolNodeReport(name, callCounts, transitions));
    group.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        openToolNodeReport(name, callCounts, transitions);
      }
    });
    svg.append(group);
  });
}

function renderSummary() {
  if (!state.agentResults) return;
  const patients = filteredSummaryPatients();
  const correct = patients.filter((patient) => patient.correct).length;
  const found = patients.reduce((sum, patient) => sum + patient.records_found, 0);
  const total = patients.reduce((sum, patient) => sum + patient.total_records, 0);
  const accuracy = byId("accuracy-metrics");
  accuracy.replaceChildren(
    metricCard(`${correct} / ${patients.length}`, "Correct diagnoses"),
    metricCard(percent(correct, patients.length), "Accuracy"),
  );
  const patientResults = byId("summary-patient-results");
  patientResults.replaceChildren();
  patients.forEach((patient) => {
    const chip = document.createElement("span");
    chip.className = `summary-patient-chip${patient.correct ? "" : " incorrect"}`;
    chip.textContent = `${patient.patient_name}: ${patient.diagnosis || "error"}`;
    patientResults.append(chip);
  });
  byId("evidence-metrics").replaceChildren(
    metricCard(`${found} / ${total}`, "Relevant records found"),
    metricCard(percent(found, total), "Weighted evidence coverage"),
    metricCard(percent(patients.reduce((sum, patient) => sum + percentValue(patient.records_found, patient.total_records), 0), patients.length * 100), "Average patient coverage"),
  );
  const entities = new Map();
  patients.forEach((patient) => {
    (patient.found_records || []).forEach((record) => {
      const counts = entities.get(record.entity) || { found: 0, total: 0 };
      counts.found += 1; counts.total += 1; entities.set(record.entity, counts);
    });
    (patient.missed_records || []).forEach((record) => {
      const counts = entities.get(record.entity) || { found: 0, total: 0 };
      counts.total += 1; entities.set(record.entity, counts);
    });
  });
  const entityCoverage = byId("entity-coverage");
  entityCoverage.replaceChildren();
  [...entities.entries()].sort(([a], [b]) => a.localeCompare(b)).forEach(([entity, counts]) => renderBar(entityCoverage, entity, counts.found, counts.total));
  const outcomeCoverage = byId("outcome-coverage");
  outcomeCoverage.replaceChildren();
  [true, false].forEach((isCorrect) => {
    const group = patients.filter((patient) => patient.correct === isCorrect);
    const groupFound = group.reduce((sum, patient) => sum + patient.records_found, 0);
    const groupTotal = group.reduce((sum, patient) => sum + patient.total_records, 0);
    renderBar(outcomeCoverage, isCorrect ? "Correct diagnoses" : "Incorrect diagnoses", groupFound, groupTotal);
  });
  const calls = patients.flatMap((patient) => patient.tool_calls || []);
  const frequency = new Map();
  calls.forEach((call) => frequency.set(call.tool_name, (frequency.get(call.tool_name) || 0) + 1));
  const mostUsed = [...frequency.entries()].sort((a, b) => b[1] - a[1])[0];
  const tokens = patients.reduce((sum, patient) => sum + (patient.usage?.total_tokens || 0), 0);
  const elapsed = patients.reduce((sum, patient) => sum + (patient.elapsed_ms || 0), 0);
  const behaviorMetrics = [
    metricCard(String(calls.length), "Total tool calls"),
    metricCard(mostUsed ? `${mostUsed[0]} (${mostUsed[1]})` : "None", "Most-used tool"),
    metricCard(tokens.toLocaleString(), "Total tokens"),
    metricCard(patients.length ? Math.round(tokens / patients.length).toLocaleString() : "—", "Average tokens per patient"),
    metricCard(`${(elapsed / 1000).toFixed(1)}s`, "Combined patient runtime"),
  ];
  const idealNames = (state.task.ideal_workflow || []).map((step) => state.tools.find((tool) => tool.id === step.tool_id)?.name).filter(Boolean);
  if (idealNames.length) {
    const adherence = patients.reduce((sum, patient) => {
      const actual = (patient.tool_calls || []).map((call) => call.tool_name);
      return sum + longestCommonSubsequence(idealNames, actual) / idealNames.length;
    }, 0);
    behaviorMetrics.push(metricCard(percent(adherence, patients.length), "Average workflow coverage"));
  }
  byId("behavior-metrics").replaceChildren(...behaviorMetrics);
  renderToolMap(patients);
  const sequences = byId("tool-call-sequences");
  sequences.replaceChildren();
  patients.forEach((patient) => {
    const item = document.createElement("div");
    item.className = "sequence-item";
    const name = document.createElement("strong");
    name.textContent = patient.patient_name;
    const path = document.createElement("p");
    const names = (patient.tool_calls || []).map((call) => call.tool_name);
    path.textContent = names.length ? names.join(" → ") : "No tool calls";
    item.append(name, path);
    sequences.append(item);
  });
}

function percentValue(numerator, denominator) {
  return denominator ? (numerator / denominator) * 100 : 0;
}

function initializeSummary(result) {
  const filter = byId("summary-patient-filter");
  filter.replaceChildren();
  [["all", "All patients"], ["positive", "Diabetes present"], ["negative", "Diabetes absent"]].forEach(([value, label]) => {
    const option = document.createElement("option"); option.value = value; option.textContent = label; filter.append(option);
  });
  result.patients.forEach((patient) => {
    const option = document.createElement("option");
    option.value = `patient:${patient.patient_id}`;
    option.textContent = patient.patient_name;
    filter.append(option);
  });
  filter.disabled = false;
  byId("summary-empty").hidden = true;
  byId("summary-dashboard").hidden = false;
  renderSummary();
}

async function runAgent() {
  if (!(state.finalized && state.taskFinalized && state.noiseFinalized)) return;
  invalidateAgentResults();
  byId("run-agent").disabled = true;
  byId("agent-progress").hidden = false;
  byId("agent-progress-bar").value = 0;
  byId("agent-progress-count").textContent = "0 / 10 patients";
  byId("agent-progress-label").textContent = "Preparing agent run…";
  byId("agent-activity").replaceChildren();
  setStatus(byId("agent-status"), "Running ten independent patient evaluations. This may take several minutes…");
  try {
    const response = await fetch("/api/agent/run-stream", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        toolset: { tools: state.tools },
        task: state.task,
        noise: state.noise,
      }),
    });
    if (!response.ok) {
      const payload = await response.json().catch(() => ({}));
      throw new Error(payload.detail || `Agent run failed (${response.status})`);
    }
    if (!response.body) throw new Error("This browser does not support streamed responses.");
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    const partialResults = [];
    let buffer = "";
    let result = null;
    let streamError = null;
    while (true) {
      const { value, done } = await reader.read();
      buffer += decoder.decode(value || new Uint8Array(), { stream: !done });
      const lines = buffer.split("\n");
      buffer = lines.pop() || "";
      for (const line of lines) {
        if (!line.trim()) continue;
        const event = JSON.parse(line);
        handleAgentProgressEvent(event, partialResults);
        if (event.type === "run_completed") result = event.result;
        if (event.type === "run_error") streamError = event.message;
      }
      if (done) break;
    }
    if (buffer.trim()) {
      const event = JSON.parse(buffer);
      handleAgentProgressEvent(event, partialResults);
      if (event.type === "run_completed") result = event.result;
      if (event.type === "run_error") streamError = event.message;
    }
    if (streamError) throw new Error(streamError);
    if (!result) throw new Error("The agent stream ended before returning final results.");
    state.agentResults = result;
    renderAgentResults(result);
    initializeSummary(result);
    byId("agent-progress-label").textContent = "Agent run complete";
    setStatus(
      byId("agent-status"),
      `${result.summary.correct} / ${result.summary.total} patients diagnosed correctly · ${result.summary.total_tokens} tokens · model ${result.model}${result.summary.errors ? ` · ${result.summary.errors} run errors` : ""}.`,
      result.summary.correct === result.summary.total ? "success" : "error",
    );
  } catch (error) {
    setStatus(byId("agent-status"), error.message, "error");
  } finally {
    renderAgentState();
  }
}

async function initialize() {
  try {
    const [patients, catalog, defaults, taskDefaults, noiseDefaults] = await Promise.all([
      api("/api/patients"), api("/api/tool-design/catalog"), api("/api/tool-design/defaults"), api("/api/task-design/defaults"), api("/api/noise/defaults"),
    ]);
    state.patients = patients;
    state.catalog = catalog;
    state.selectedPatientId = patients[0]?.patient_id || null;
    const saved = loadSavedTools();
    state.tools = saved?.tools || defaults.tools;
    state.finalized = Boolean(saved?.finalized);
    state.argumentVocabularies = saved?.argumentVocabularies || {};
    if (state.finalized && !Object.keys(state.argumentVocabularies).length) {
      const migrated = await api("/api/tool-design/validate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ tools: state.tools }),
      });
      state.argumentVocabularies = migrated.argument_vocabularies;
    }
    const savedTask = loadSavedTask();
    state.task = savedTask?.task || taskDefaults;
    state.task.ideal_workflow = (state.task.ideal_workflow || []).map((step) => ({ tool_id: step.tool_id }));
    state.taskFinalized = Boolean(savedTask?.finalized && state.finalized);
    const savedNoise = loadSavedNoise();
    state.noise = savedNoise?.configuration || noiseDefaults.configuration;
    state.noiseSources = noiseDefaults.sources;
    state.noiseFinalized = Boolean(savedNoise?.finalized && state.taskFinalized);
    renderPatients();
    renderTools();
    renderTask();
    renderNoise();
    byId("preview-tool").addEventListener("change", syncPreviewArgument);
    byId("add-tool").addEventListener("click", () => { state.tools.push(newTool()); renderTools(); });
    byId("finalize-tools").addEventListener("click", finalizeTools);
    byId("edit-tools").addEventListener("click", editTools);
    byId("reset-tools").addEventListener("click", resetDefaults);
    byId("run-preview").addEventListener("click", previewTool);
    byId("close-reader").addEventListener("click", () => byId("patient-reader").close());
    byId("open-raw-json").addEventListener("click", openRawJson);
    byId("add-workflow-step").addEventListener("click", addWorkflowStep);
    byId("finalize-task").addEventListener("click", finalizeTask);
    byId("edit-task").addEventListener("click", editTask);
    byId("toggle-noise").addEventListener("click", toggleNoise);
    byId("finalize-noise").addEventListener("click", finalizeNoise);
    byId("edit-noise").addEventListener("click", editNoise);
    byId("run-verification").addEventListener("click", runVerification);
    byId("run-agent").addEventListener("click", runAgent);
    byId("summary-patient-filter").addEventListener("change", renderSummary);
    byId("close-verification-reader").addEventListener("click", () => byId("verification-reader").close());
    byId("verification-reader").addEventListener("click", (event) => {
      if (event.target === byId("verification-reader")) byId("verification-reader").close();
    });
    byId("close-agent-reader").addEventListener("click", () => byId("agent-reader").close());
    byId("agent-reader").addEventListener("click", (event) => {
      if (event.target === byId("agent-reader")) byId("agent-reader").close();
    });
    byId("close-tool-node-reader").addEventListener("click", () => byId("tool-node-reader").close());
    byId("tool-node-reader").addEventListener("click", (event) => {
      if (event.target === byId("tool-node-reader")) byId("tool-node-reader").close();
    });
    byId("patient-reader").addEventListener("click", (event) => {
      if (event.target === byId("patient-reader")) byId("patient-reader").close();
    });
  } catch (error) {
    setStatus(byId("population-status"), error.message, "error");
  }
}

initialize();
