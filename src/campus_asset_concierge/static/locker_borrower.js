document.querySelectorAll("[data-code-input]").forEach((input) => {
  const entry = input.closest(".code-entry");
  const cells = entry.querySelector(".code-cells");
  cells.hidden = false;
  entry.classList.add("is-enhanced");
  function renderCode() {
    input.value = input.value.replace(/[^0-9]/g, "").slice(0, 6);
    [...cells.children].forEach((cell, index) => {
      cell.textContent = input.value[index] || "–";
      cell.classList.toggle("is-current", index === Math.min(input.selectionStart ?? input.value.length, 5));
    });
  }
  input.addEventListener("input", renderCode);
  input.addEventListener("focus", renderCode);
  input.addEventListener("keyup", renderCode);
  input.addEventListener("click", renderCode);
  input.addEventListener("paste", (event) => {
    const text = event.clipboardData?.getData("text");
    if (text) {
      event.preventDefault();
      input.value = text.replace(/[^0-9]/g, "").slice(0, 6);
      renderCode();
    }
  });
  renderCode();
});
