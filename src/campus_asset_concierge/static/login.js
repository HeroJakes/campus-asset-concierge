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

document.querySelectorAll(".account-fill").forEach((button) => {
  button.hidden = false;
  button.addEventListener("click", () => {
    document.getElementById("username").value = button.dataset.username;
    passwordInput.value = button.dataset.password;
    document.querySelector(`input[name="role"][value="${button.dataset.role}"]`).checked = true;
    document.querySelector(".login-submit").focus();
  });
});
