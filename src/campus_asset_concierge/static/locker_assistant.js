// Borrower booking assistant chat. History lives here (stateless server); the
// Confirm button posts straight to the reservation endpoint, never through the model.
const log = document.getElementById("assistant-log");
const form = document.getElementById("assistant-form");
const input = document.getElementById("assistant-input");
const sendButton = document.getElementById("assistant-send");

const messages = []; // {role: "user"|"model", text}

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function addRow(side) {
  const row = el("div", `assistant-row assistant-row--${side}`);
  if (side === "bot") {
    const avatar = el("span", "assistant-avatar");
    avatar.textContent = "AI";
    row.appendChild(avatar);
  }
  const bubble = el("div", "assistant-bubble");
  row.appendChild(bubble);
  log.appendChild(row);
  log.scrollTop = log.scrollHeight;
  return bubble;
}

function addMessage(side, text) {
  addRow(side).appendChild(el("p", null, text));
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

function addOfferCard(offer) {
  const bubble = addRow("bot");
  const card = el("div", "offer-card");
  card.appendChild(el("h3", null, (offer.asset_id || "").replace(/-/g, " ")));
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
  card.appendChild(meta);

  const confirm = el("button", "button button--success", "Confirm booking");
  const status = el("p", "offer-status");
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
      status.className = "offer-status offer-status--ok";
      status.textContent = "";
      status.appendChild(el("span", null, "Booked ✓ "));
      const link = el("a", null, "View in My Locker");
      link.href = "/locker";
      status.appendChild(link);
    } catch {
      status.textContent = "Network error — please try again.";
      confirm.disabled = false;
    }
  });
  card.appendChild(confirm);
  card.appendChild(status);
  bubble.appendChild(card);
  log.scrollTop = log.scrollHeight;
}

async function send(text) {
  messages.push({ role: "user", text });
  addMessage("user", text);
  const typing = addRow("bot");
  typing.appendChild(el("p", "assistant-typing", "…"));
  sendButton.disabled = true;
  try {
    const res = await fetch("/assistant/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ messages }),
    });
    typing.parentElement.remove();
    const data = res.ok ? await res.json() : { reply: "The assistant hit an error. Please try again.", offer: null };
    const reply = data.reply || "";
    if (reply) {
      messages.push({ role: "model", text: reply });
      addMessage("bot", reply);
    }
    if (data.offer) addOfferCard(data.offer);
  } catch {
    typing.parentElement.remove();
    addMessage("bot", "Network error — please try again.");
  } finally {
    sendButton.disabled = false;
    input.focus();
  }
}

form.addEventListener("submit", (event) => {
  event.preventDefault();
  const text = input.value.trim();
  if (!text) return;
  input.value = "";
  input.style.height = "auto";
  send(text);
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
