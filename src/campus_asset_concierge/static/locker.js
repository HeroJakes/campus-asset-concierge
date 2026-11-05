const errorBox = document.getElementById("action-error");

async function send(url, body, control) {
  errorBox.hidden = true;
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
  errorBox.textContent = message;
  errorBox.hidden = false;
  errorBox.scrollIntoView({ block: "nearest" });
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
