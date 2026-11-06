const bookingForm = document.querySelector(".booking-search");
const bookingSearch = document.getElementById("booking-search");
let searchTimer;
let pendingSearch;

function queueBookingSearch(delay = 250) {
  clearTimeout(searchTimer);
  pendingSearch?.abort();
  const controller = new AbortController();
  pendingSearch = controller;
  searchTimer = setTimeout(() => updateBookingResults(controller), delay);
}

async function updateBookingResults(controller) {
  const results = document.getElementById("booking-results");
  const url = new URL(bookingForm.action);
  url.search = new URLSearchParams(new FormData(bookingForm));
  results.setAttribute("aria-busy", "true");
  errorBox.hidden = true;
  try {
    const response = await fetch(url, { signal: controller.signal });
    if (!response.ok) throw new Error("Search failed");
    const html = await response.text();
    if (controller.signal.aborted) return;
    const page = new DOMParser().parseFromString(html, "text/html");
    const nextResults = page.getElementById("booking-results");
    const title = page.getElementById("booking-list-title");
    const stats = page.querySelector(".booking-stats");
    if (!nextResults || !title || !stats) throw new Error("Missing search results");
    results.replaceWith(nextResults);
    document.getElementById("booking-list-title").replaceWith(title);
    document.querySelector(".booking-stats").replaceWith(stats);
    document.querySelector(".refresh-button").href = url;
    document.getElementById("booking-search-feedback").textContent = title.textContent;
    history.replaceState(null, "", url);
  } catch {
    if (!controller.signal.aborted) showError("Couldn't update bookings. Please try searching again.");
  } finally {
    if (pendingSearch === controller) {
      document.getElementById("booking-results").removeAttribute("aria-busy");
    }
  }
}

bookingSearch.addEventListener("input", (event) => {
  if (!event.isComposing) queueBookingSearch();
});
bookingSearch.addEventListener("compositionend", () => queueBookingSearch());
document.getElementById("booking-status").addEventListener("change", () => queueBookingSearch(0));
bookingForm.addEventListener("submit", (event) => {
  event.preventDefault();
  queueBookingSearch(0);
});
