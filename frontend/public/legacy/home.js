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

const dialogs = document.querySelectorAll("dialog");

const routes = {
  "#dashboard": "/",
  "#capture": "/capture",
};

const icons = {
  "#dashboard": '<svg class="nav-icon" viewBox="0 0 24 24" aria-hidden="true"><path d="m3 10 9-7 9 7v10a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1z"/><path d="M9 21v-7h6v7"/></svg>',
  "#capture": '<svg class="nav-icon" viewBox="0 0 24 24" aria-hidden="true"><rect x="3" y="5" width="18" height="14" rx="3"/><circle cx="12" cy="12" r="3"/><path d="M8 5 9.5 3h5L16 5"/></svg>',
};

const navigationCopy = {
  th: { "#dashboard": "ภาพรวม", "#capture": "วิเคราะห์ภาพ" },
  en: { "#dashboard": "Overview", "#capture": "Analyze image" },
};
function renderNavigation(language) {
  Object.entries(navigationCopy[language]).forEach(([hash, label]) => {
    document.querySelectorAll(`a.nav-link[href="${hash}"], .mobile-nav a[href="${hash}"]`).forEach((link) => {
      link.innerHTML = link.closest(".mobile-nav") ? `${icons[hash]}<span>${label}</span>` : `${icons[hash]}${label}`;
    });
  });
}

document.querySelectorAll("a[href^='#']").forEach((link) => {
  link.addEventListener("click", (event) => {
    const route = routes[link.getAttribute("href")];
    if (!route || route === "/") return;
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

const languageToggle = document.createElement("button");
languageToggle.type = "button";
languageToggle.className = "language-toggle";
const languageCopy = {
  th: {
    date: "ภาพล่าสุด · 20 ก.ย. 2026", greeting: "สวัสดี, Ink", notice: "ผลนี้ใช้สำหรับติดตามลักษณะผิว ไม่ใช่การวินิจฉัยโรคหรือยืนยันสาเหตุ",
    severity: "ปานกลาง", scoreMeta: "confidence 0.86 · Model v0.1", regions: "ดูผลรายบริเวณ →", next: "ติดตามครั้งต่อไป", captureTitle: "พร้อมบันทึกภาพใหม่ไหม?", captureText: "หน้าสด · หน้าตรง · แสงกระจาย เพื่อให้เทียบผลได้ดีขึ้น", captureButton: "ถ่ายภาพใหม่ →",
    latest: "สิ่งที่ตรวจพบจากภาพ", detail: "ดูรายละเอียด →", eye: "รอบดวงตา", forehead: "หน้าผาก", mild: "เล็กน้อย", quality: "คุณภาพภาพ", passed: "ผ่าน", usable: "ภาพผ่านเกณฑ์", rules: "คำแนะนำจากกฎ", barrier: "ดูแลเกราะป้องกันผิว", rationale: "แสดงจากข้อมูลที่คุณรายงานร่วมกับผลภาพที่ confidence ผ่านเกณฑ์", safety: "ดูเหตุผลและ safety check →", language: "EN",
  },
  en: {
    date: "Latest image · Sep 20, 2026", greeting: "Hello, Ink", notice: "This result supports skin tracking; it is not a diagnosis or confirmation of cause.",
    severity: "Moderate", scoreMeta: "confidence 0.86 · Model v0.1", regions: "View regional results →", next: "NEXT CHECK-IN", captureTitle: "Ready to record a new image?", captureText: "Bare face · forward-facing · diffused light for a more comparable result", captureButton: "Capture new image →",
    latest: "Detected from image", detail: "View details →", eye: "Periocular area", forehead: "Forehead", mild: "Mild", quality: "Image quality", passed: "Passed", usable: "Quality check passed", rules: "Rule-based guidance", barrier: "Support your skin barrier", rationale: "Uses your reported information together with image signals that passed the confidence threshold.", safety: "View rationale & safety check →", language: "TH",
  },
};
function setText(selector, value, index = 0) {
  const elements = document.querySelectorAll(selector);
  if (elements[index]) elements[index].textContent = value;
}
function applyLanguage(language) {
  const copy = languageCopy[language];
  document.documentElement.lang = language;
  localStorage.setItem("aphrodize-language", language);
  renderNavigation(language);
  setText(".topbar .eyebrow", copy.date); setText(".topbar h1", copy.greeting); setText(".notice p", copy.notice);
  setText(".score-card .status", copy.severity); setText(".score-card .metadata", copy.scoreMeta); setText(".score-card .text-button", copy.regions);
  setText(".capture-card .eyebrow", copy.next); setText(".capture-card h2", copy.captureTitle); setText(".capture-card p:not(.eyebrow)", copy.captureText); setText(".capture-card .primary-button", copy.captureButton);
  setText(".section-heading h2", copy.latest); setText(".section-heading .text-button", copy.detail); setText(".result-card .eyebrow", copy.eye, 0); setText(".result-card h3", copy.severity, 0); setText(".result-card .eyebrow", copy.forehead, 1); setText(".result-card h3", copy.mild, 1); setText(".result-card .eyebrow", copy.quality, 2); setText(".result-card h3", copy.passed, 2); setText(".result-card .metadata", copy.usable, 2);
  setText(".sources-grid article .eyebrow", copy.rules); setText(".sources-grid article h2", copy.barrier); setText(".sources-grid article p:not(.eyebrow)", copy.rationale); setText(".sources-grid article .text-button", copy.safety);
  languageToggle.textContent = copy.language;
  languageToggle.setAttribute("aria-label", language === "th" ? "Change language to English" : "เปลี่ยนภาษาเป็นไทย");
}
languageToggle.addEventListener("click", () => applyLanguage(document.documentElement.lang === "th" ? "en" : "th"));
const topbarControls = document.createElement("div");
topbarControls.className = "topbar-controls";
const homeButton = document.createElement("button");
homeButton.type = "button";
homeButton.className = "home-button";
homeButton.innerHTML = '<img src="/assets/home.svg" alt="" />';
homeButton.setAttribute("aria-label", "หน้าแรก");
homeButton.title = "หน้าแรก";
homeButton.addEventListener("click", () => window.location.assign("/"));
const profileButton = topbar.querySelector(".avatar");
profileButton.setAttribute("aria-label", "เข้าสู่ระบบ");
profileButton.title = "เข้าสู่ระบบ";
profileButton.addEventListener("click", () => window.location.assign("/login"));
topbarControls.append(homeButton, languageToggle, themeToggle, profileButton);
topbar?.append(topbarControls);
applyLanguage(localStorage.getItem("aphrodize-language") || "th");

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
sidebar.querySelector(".sidebar-close")?.addEventListener("click", () => {
  sidebar.classList.remove("mobile-open");
  menuButton.setAttribute("aria-expanded", "false");
  menuButton.setAttribute("aria-label", "เปิดเมนู");
});
topbar?.prepend(menuButton);
profileButton.innerHTML = '<img src="/assets/profile-login.svg" alt="" />';

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
