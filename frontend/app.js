const dialogs = document.querySelectorAll("dialog");

const routes = {
  "#dashboard": "index.html",
  "#capture": "capture.html",
  "#trend": "trend.html",
  "#profile": "profile.html",
  "#privacy": "profile.html#privacy",
};

const icons = {
  "#dashboard": '<svg class="nav-icon" viewBox="0 0 24 24" aria-hidden="true"><path d="m3 10 9-7 9 7v10a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1z"/><path d="M9 21v-7h6v7"/></svg>',
  "#capture": '<svg class="nav-icon" viewBox="0 0 24 24" aria-hidden="true"><rect x="3" y="5" width="18" height="14" rx="3"/><circle cx="12" cy="12" r="3"/><path d="M8 5 9.5 3h5L16 5"/></svg>',
  "#trend": '<svg class="nav-icon" viewBox="0 0 24 24" aria-hidden="true"><path d="M3 20V5"/><path d="M3 20h18"/><path d="m6 16 4-5 3 3 5-7"/></svg>',
  "#profile": '<svg class="nav-icon" viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="8" r="3.5"/><path d="M5 21c.8-4 3.1-6 7-6s6.2 2 7 6"/></svg>',
};

const navLabels = { "#dashboard": "ภาพรวม", "#capture": "วิเคราะห์ภาพ", "#trend": "แนวโน้ม", "#profile": "Skin profile" };
Object.entries(navLabels).forEach(([hash, label]) => {
  document.querySelectorAll(`a[href="${hash}"]`).forEach((link) => {
    link.innerHTML = link.closest(".mobile-nav") ? `${icons[hash]}<span>${label}</span>` : `${icons[hash]}${label}`;
  });
});

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
document.querySelector(".avatar").textContent = "";

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
