(function () {
  const storageKey = "aphrodize-theme";
  const root = document.documentElement;

  function setTheme(theme) {
    root.dataset.theme = theme;
    localStorage.setItem(storageKey, theme);
  }

  setTheme(localStorage.getItem(storageKey) || "pastel");
  window.AphrodizeTheme = { setTheme, current: () => root.dataset.theme };
}());

const loginForm = document.querySelector("#login-form");
const password = document.querySelector("#password");
const togglePassword = document.querySelector("#toggle-password");
const message = document.querySelector("#form-message");

togglePassword.addEventListener("click", () => {
  const isHidden = password.type === "password";
  password.type = isHidden ? "text" : "password";
  togglePassword.textContent = isHidden ? "ซ่อน" : "แสดง";
  togglePassword.setAttribute("aria-label", isHidden ? "ซ่อนรหัสผ่าน" : "แสดงรหัสผ่าน");
});

loginForm.addEventListener("submit", (event) => {
  event.preventDefault();
  if (!loginForm.checkValidity()) {
    message.textContent = "กรอกอีเมลที่ถูกต้องและรหัสผ่านอย่างน้อย 8 ตัวอักษร";
    loginForm.reportValidity();
    return;
  }
  message.textContent = "";
  window.location.assign("/");
});
