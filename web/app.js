const form = document.querySelector("#issue-form");
const input = document.querySelector("#issue-url");
const status = document.querySelector("#status");
const result = document.querySelector("#result");
const button = form.querySelector("button");

const setText = (selector, value) => {
  document.querySelector(selector).textContent = value;
};

const addListItems = (selector, items, renderer) => {
  const list = document.querySelector(selector);
  list.replaceChildren(...items.map(renderer));
};

const renderResult = (data) => {
  setText("#repo-name", `${data.repository.full_name} · ISSUE #${data.issue.number}`);
  setText("#issue-title", data.issue.title);
  setText("#confidence", `${data.plan.confidence} confidence`);
  setText("#hypothesis", data.plan.root_cause_hypothesis);
  setText("#notice", data.notice);

  const tracePanel = document.querySelector("#trace-panel");
  if (data.agent_trace.length) {
    addListItems("#agent-trace", data.agent_trace, (step) => {
      const li = document.createElement("li");
      const heading = document.createElement("div");
      heading.className = "trace-heading";
      heading.textContent = `Round ${step.round} / ${step.tool}`;
      const args = document.createElement("code");
      args.textContent = JSON.stringify(step.arguments);
      const summary = document.createElement("p");
      summary.textContent = step.result_summary;
      li.append(heading, args, summary);
      return li;
    });
    tracePanel.classList.remove("hidden");
  } else {
    tracePanel.classList.add("hidden");
  }

  addListItems("#files", data.relevant_files, (file) => {
    const li = document.createElement("li");
    const path = document.createElement("span");
    path.className = "file-path";
    path.textContent = file.path;
    const reason = document.createElement("span");
    reason.className = "file-reason";
    reason.textContent = file.reasons.join(" · ");
    li.append(path, reason);
    return li;
  });

  addListItems("#verification", data.plan.verification, (text) => {
    const li = document.createElement("li");
    li.textContent = text;
    return li;
  });

  addListItems("#steps", data.plan.steps, (step) => {
    const li = document.createElement("li");
    const content = document.createElement("div");
    const title = document.createElement("p");
    title.className = "step-title";
    title.textContent = step.title;
    const detail = document.createElement("p");
    detail.className = "step-detail";
    detail.textContent = step.details;
    content.append(title, detail);
    if (step.files.length) {
      const files = document.createElement("div");
      files.className = "step-files";
      files.textContent = step.files.join(" · ");
      content.append(files);
    }
    li.append(content);
    return li;
  });

  result.classList.remove("hidden");
  result.scrollIntoView({ behavior: "smooth", block: "start" });
};

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  status.className = "status";
  status.textContent = "Inspecting issue and repository tree…";
  button.disabled = true;
  result.classList.add("hidden");

  try {
    const response = await fetch("/api/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ issue_url: input.value.trim() }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "Analysis failed.");
    renderResult(data);
    status.textContent = `Plan ready · ${data.relevant_files.length} candidate files inspected`;
  } catch (error) {
    status.className = "status error";
    status.textContent = error.message;
  } finally {
    button.disabled = false;
  }
});

