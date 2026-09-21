const dialogs = document.querySelectorAll("dialog");

const routes = {
  "#dashboard": "index.html",
  "#capture": "capture.html",
  "#trend": "trend.html",
  "#profile": "profile.html",
  "#privacy": "profile.html#privacy",
};

document.querySelectorAll("a[href^='#']").forEach((link) => {
  link.addEventListener("click", (event) => {
    const route = routes[link.getAttribute("href")];
    if (!route || route === "index.html") return;
    event.preventDefault();
    window.location.assign(route);
  });
});

const themeToggle = document.createElement("button");
themeToggle.type = "button";
themeToggle.className = "theme-toggle top-theme-toggle";
function updateThemeLabel() {
  const isBlack = window.AphrodizeTheme.current() === "black";
  themeToggle.textContent = isBlack ? "☀ Pastel" : "☾ Black";
  themeToggle.setAttribute("aria-label", isBlack ? "เปลี่ยนเป็น Pastel theme" : "เปลี่ยนเป็น Black theme");
  themeToggle.title = themeToggle.getAttribute("aria-label");
}
themeToggle.addEventListener("click", () => {
  window.AphrodizeTheme.setTheme(window.AphrodizeTheme.current() === "black" ? "pastel" : "black");
  updateThemeLabel();
});
const topbar = document.querySelector(".topbar");
topbar?.insertBefore(themeToggle, topbar.querySelector(".avatar"));
updateThemeLabel();

const sidebar = document.querySelector(".sidebar");
const menuButton = document.createElement("button");
menuButton.type = "button";
menuButton.className = "mobile-menu-button";
menuButton.innerHTML = "<span></span><span></span><span></span>";
menuButton.setAttribute("aria-label", "เปิดเมนู");
menuButton.setAttribute("aria-expanded", "false");
menuButton.addEventListener("click", () => {
  const isOpen = sidebar.classList.toggle("mobile-open");
  menuButton.setAttribute("aria-expanded", String(isOpen));
  menuButton.setAttribute("aria-label", isOpen ? "ปิดเมนู" : "เปิดเมนู");
});
topbar?.prepend(menuButton);

function openDialog(id) {
  const target = document.getElementById(id);
  if (target) target.showModal();
}

document.querySelectorAll("[data-open]").forEach((button) => {
  button.addEventListener("click", () => {
    const current = button.closest("dialog");
    if (current) current.close();
    openDialog(button.dataset.open);
  });
});

document.querySelectorAll("[data-close]").forEach((button) => {
  button.addEventListener("click", () => button.closest("dialog").close());
});

dialogs.forEach((dialog) => dialog.addEventListener("click", (event) => {
  if (event.target === dialog) dialog.close();
}));
