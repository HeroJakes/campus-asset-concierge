const errorBox = document.getElementById("action-error");

function actionErrorBox() {
  return document.querySelector("dialog[open] [data-dialog-error]") || errorBox;
}

async function send(url, body, control) {
  actionErrorBox().hidden = true;
  control.disabled = true;
  try {
    const response = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: body ? JSON.stringify(body) : undefined,
    });
    if (response.ok) {
      location.reload();
      return;
    }
    const failure = await response.json().catch(() => ({}));
    showError(typeof failure.detail === "string" ? failure.detail : "That didn't work. Please try again.");
  } catch {
    showError("Couldn't reach the server. Please try again.");
  }
  control.disabled = false;
}

function showError(message) {
  const target = actionErrorBox();
  target.textContent = message;
  target.hidden = false;
  target.scrollIntoView({ block: "nearest" });
}

document.querySelectorAll("[data-post]").forEach((button) => {
  button.addEventListener("click", () =>
    send(button.dataset.post, button.dataset.body ? JSON.parse(button.dataset.body) : null, button),
  );
});

document.querySelectorAll("[data-unlock]").forEach((form) => {
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    send(form.dataset.unlock, { code: form.elements.code.value.trim() }, form.querySelector("button"));
  });
});

document.querySelectorAll("[data-open-dialog]").forEach((button) => {
  button.addEventListener("click", () => {
    const dialog = document.getElementById(button.dataset.openDialog);
    dialog.querySelector("[data-dialog-error]").hidden = true;
    dialog.showModal();
  });
});

const sidebarToggle = document.getElementById("sidebar-toggle");
if (sidebarToggle) {
  function setSidebar(collapsed) {
    document.body.classList.toggle("sidebar-collapsed", collapsed);
    sidebarToggle.setAttribute("aria-expanded", String(!collapsed));
    const label = collapsed ? "Expand sidebar" : "Collapse sidebar";
    sidebarToggle.setAttribute("aria-label", label);
    sidebarToggle.title = label;
  }
  let collapsed = window.matchMedia("(max-width: 760px)").matches;
  try {
    const saved = localStorage.getItem("locker-sidebar-collapsed");
    if (saved !== null) collapsed = saved === "true";
  } catch { /* Sidebar still works when browser storage is unavailable. */ }
  setSidebar(collapsed);
  sidebarToggle.addEventListener("click", () => {
    const next = !document.body.classList.contains("sidebar-collapsed");
    setSidebar(next);
    try { localStorage.setItem("locker-sidebar-collapsed", String(next)); } catch { /* Keep the current page state. */ }
  });
  const links = [...document.querySelectorAll(".sidebar-link")];
  links.forEach((link) => link.addEventListener("click", () => {
    if (window.matchMedia("(max-width: 760px)").matches) setSidebar(true);
  }));
  function updateNavigation() {
    const current = window.location.pathname + (window.location.hash || "");
    links.forEach((link) => {
      const selected = link.getAttribute("href") === current;
      link.classList.toggle("is-current", selected);
      if (selected) link.setAttribute("aria-current", "location");
      else link.removeAttribute("aria-current");
    });
  }
  window.addEventListener("hashchange", updateNavigation);
  updateNavigation();
}
