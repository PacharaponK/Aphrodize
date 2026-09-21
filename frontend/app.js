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
themeToggle.className = "theme-toggle";
function updateThemeLabel() {
  themeToggle.innerHTML = window.AphrodizeTheme.current() === "black" ? "☾ Black theme <span>เปลี่ยนเป็น Pastel</span>" : "✦ Pastel theme <span>เปลี่ยนเป็น Black</span>";
}
themeToggle.addEventListener("click", () => {
  window.AphrodizeTheme.setTheme(window.AphrodizeTheme.current() === "black" ? "pastel" : "black");
  updateThemeLabel();
});
document.querySelector(".sidebar nav")?.after(themeToggle);
updateThemeLabel();

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
