const passwordToggle = document.querySelector(".password-toggle");
const passwordInput = document.getElementById("password");

if (passwordToggle && passwordInput) {
  passwordToggle.hidden = false;
  passwordToggle.addEventListener("click", () => {
    const reveal = passwordInput.type === "password";
    passwordInput.type = reveal ? "text" : "password";
    passwordToggle.setAttribute("aria-pressed", String(reveal));
    passwordToggle.setAttribute("aria-label", reveal ? "Hide password" : "Show password");
  });
}
