// Borrower booking assistant chat. History stays in this browser per account; the
// Confirm button posts straight to the reservation endpoint, never through the model.
const log = document.getElementById("assistant-log");
const form = document.getElementById("assistant-form");
const input = document.getElementById("assistant-input");
const sendButton = document.getElementById("assistant-send");

const messages = []; // {role: "user"|"model", text}
const history = [];
const historyKey = `campus-assistant-v1:${log.dataset.username}`;
const historyStatus = document.getElementById("assistant-history-status");

function saveHistory() {
  try {
    localStorage.setItem(historyKey, JSON.stringify(history.slice(-100)));
  } catch {
    historyStatus.textContent = "Chat history could not be saved in this browser.";
  }
}

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function addRow(side) {
  const row = el("div", `assistant-row assistant-row--${side}`);
  const avatar = el("span", "assistant-avatar");
  avatar.appendChild(document.getElementById(`assistant-${side}-icon`).content.cloneNode(true));
  row.appendChild(avatar);
  const message = el("div", "assistant-message");
  const bubble = el("div", "assistant-bubble");
  message.appendChild(bubble);
  const clock = document.querySelector(".borrower-clock time");
  const stamp = el("time", "message-time", clock.textContent.trim().split("·").pop().trim());
  stamp.dateTime = clock.dateTime;
  message.appendChild(stamp);
  row.appendChild(message);
  log.appendChild(row);
  log.scrollTop = log.scrollHeight;
  return bubble;
}

function addMessage(side, text) {
  const paragraph = el("p");
  // Render only bold markers; model text is never interpreted as HTML.
  for (const [index, part] of text.split(/\*\*([^*]+)\*\*/g).entries()) {
    paragraph.appendChild(el(side === "bot" && index % 2 ? "strong" : "span", null,
      side === "user" && index % 2 ? `**${part}**` : part));
  }
  addRow(side).appendChild(paragraph);
  log.scrollTop = log.scrollHeight;
}

function timePart(value) {
  return typeof value === "string" && value.length >= 16 ? value.slice(0, 10) + " " + value.slice(11, 16) : value || "";
}

function requirementsText(offer) {
  const needs = [];
  if (offer.require_hdmi) needs.push("HDMI");
  if (offer.require_built_in_speakers) needs.push("built-in speakers");
  return needs.length ? needs.join(", ") : "No extra requirements";
}

function addOfferCard(offer, entry = null, restored = false) {
  const bubble = addRow("bot");
  const card = el("div", "offer-card");
  card.appendChild(el("p", null, "Here's your equipment offer:"));
  const summary = el("div", "offer-summary");
  const art = document.getElementById((offer.asset_id || "").includes("raspberry") ? "assistant-kit-art" : "assistant-projector-art");
  summary.appendChild(art.content.cloneNode(true));
  const details = el("div");
  details.appendChild(el("h3", null, (offer.asset_id || "").replace(/-/g, " ")));
  const meta = el("dl", "offer-meta");
  const rows = [
    ["Location", offer.pickup_location],
    ["Pickup", timePart(offer.pickup_at)],
    ["Return by", timePart(offer.due_at)],
    ["Requirements", requirementsText(offer)],
  ];
  for (const [label, value] of rows) {
    meta.appendChild(el("dt", null, label));
    meta.appendChild(el("dd", null, value || "—"));
  }
  details.appendChild(meta);
  summary.appendChild(details);
  card.appendChild(summary);
  card.appendChild(el("p", null, "Would you like to confirm this booking?"));

  const actions = el("div", "offer-actions");
  const confirm = el("button", "button button--primary", "✓ Confirm booking");
  const change = el("button", "button button--quiet", "Change request");
  change.type = "button";
  change.addEventListener("click", () => {
    input.value = "I'd like to change my request: ";
    input.focus();
  });
  const status = el("p", "offer-status");
  status.setAttribute("role", "status");
  confirm.addEventListener("click", async () => {
    confirm.disabled = true;
    status.textContent = "Booking…";
    try {
      const res = await fetch(`/reservation-offers/${encodeURIComponent(offer.id)}/confirm`, {
        method: "POST",
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        status.textContent = body.detail || "Could not confirm — the offer may have expired. Try asking again.";
        confirm.disabled = false;
        return;
      }
      confirm.remove();
      change.remove();
      status.className = "offer-status offer-status--ok";
      status.textContent = "";
      status.appendChild(el("span", null, "Booked ✓ "));
      const link = el("a", null, "View in My Locker");
      link.href = "/locker";
      status.appendChild(link);
      if (entry) {
        entry.confirmed = true;
        saveHistory();
      }
    } catch {
      status.textContent = "Network error — please try again.";
      confirm.disabled = false;
    }
  });
  actions.appendChild(confirm);
  actions.appendChild(change);
  card.appendChild(actions);
  card.appendChild(status);
  bubble.appendChild(card);
  if (restored) {
    confirm.remove();
    change.remove();
    status.textContent = entry?.confirmed ? "Booked ✓ — view the current status in My Locker." : "Saved offer. Ask for a fresh offer before confirming.";
  }
  log.scrollTop = log.scrollHeight;
}

async function send(text) {
  messages.push({ role: "user", text });
  history.push({ role: "user", text });
  saveHistory();
  addMessage("user", text);
  const typing = addRow("bot");
  const dots = el("p", "assistant-typing");
  dots.setAttribute("role", "status");
  dots.setAttribute("aria-label", "MiMi is thinking");
  for (let i = 0; i < 3; i++) {
    const dot = el("span", null, ".");
    dot.setAttribute("aria-hidden", "true");
    dots.appendChild(dot);
  }
  typing.appendChild(dots);
  sendButton.disabled = true;
  try {
    const recent = messages.slice(-40);
    if (recent[0]?.role === "model") recent.shift();
    const res = await fetch("/assistant/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ messages: recent.map(message => ({ ...message, text: message.text.slice(0, 2000) })) }),
    });
    const data = res.ok ? await res.json() : { reply: "MiMi hit an error. Please try again.", offer: null };
    const reply = data.reply || "";
    const entry = { role: "model", text: reply, offer: data.offer || null };
    history.push(entry);
    saveHistory();
    if (reply) {
      messages.push({ role: "model", text: reply });
      addMessage("bot", reply);
    }
    if (data.offer) addOfferCard(data.offer, entry);
  } catch {
    addMessage("bot", "Network error — please try again.");
  } finally {
    typing.closest(".assistant-row").remove();
    sendButton.disabled = false;
    input.focus();
  }
}

form.addEventListener("submit", (event) => {
  event.preventDefault();
  if (sendButton.disabled) return;
  const text = input.value.trim();
  if (!text) return;
  input.value = "";
  input.style.height = "auto";
  send(text);
});

document.querySelectorAll("[data-prompt]").forEach((button) => {
  button.addEventListener("click", () => {
    input.value = button.dataset.prompt;
    input.focus();
  });
});

try {
  const saved = JSON.parse(localStorage.getItem(historyKey) || "[]");
  if (Array.isArray(saved)) {
    for (const entry of saved.slice(-100)) {
      if (!entry || !["user", "model"].includes(entry.role) || typeof entry.text !== "string") continue;
      history.push(entry);
      if (entry.text) {
        messages.push({ role: entry.role, text: entry.text });
        addMessage(entry.role === "user" ? "user" : "bot", entry.text);
      }
      if (entry.role === "model" && entry.offer && typeof entry.offer.id === "string") addOfferCard(entry.offer, entry, true);
    }
  }
} catch {
  historyStatus.textContent = "Chat history could not be loaded in this browser.";
}

document.getElementById("assistant-clear").addEventListener("click", () => {
  if (sendButton.disabled) return;
  history.length = 0;
  messages.length = 0;
  saveHistory();
  log.querySelectorAll(".assistant-row:not([data-greeting])").forEach(row => row.remove());
});

input.addEventListener("input", () => {
  input.style.height = "auto";
  input.style.height = Math.min(input.scrollHeight, 160) + "px";
});

input.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    form.requestSubmit();
  }
});
