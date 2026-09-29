const dialogs = document.querySelectorAll("dialog");

const routes = {
  "#dashboard": "/",
  "#capture": "/capture",
};

const navigationCopy = {
  th: { dashboard: "ภาพรวม", capture: "วิเคราะห์ภาพ", clients: "สุขภาพรายวัน", trend: "แนวโน้ม", profile: "Skin profile" },
  en: { dashboard: "Overview", capture: "Analyze image", clients: "Daily health", trend: "Trends", profile: "Skin profile" },
};
function renderNavigation(language) {
  Object.entries(navigationCopy[language]).forEach(([key, label]) => {
    const navLabel = document.querySelector(`.nav-label[data-nav-label="${key}"]`);
    if (navLabel) navLabel.textContent = label;
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
  const english = document.documentElement.lang === "en";
  themeToggle.textContent = isBlack ? (english ? "☀ Light" : "☀ สว่าง") : (english ? "☾ Dark" : "☾ มืด");
  themeToggle.setAttribute("aria-pressed", String(isBlack));
  themeToggle.setAttribute("aria-label", isBlack ? (english ? "Switch to light theme" : "เปลี่ยนเป็นธีมสว่าง") : (english ? "Switch to dark theme" : "เปลี่ยนเป็นธีมมืด"));
  themeToggle.title = themeToggle.getAttribute("aria-label");
}
themeToggle.addEventListener("click", () => {
  window.AphrodizeTheme.setTheme(window.AphrodizeTheme.current() === "black" ? "pastel" : "black");
  updateThemeLabel();
});
window.addEventListener("aphrodize-theme-change", updateThemeLabel);
const topbar = document.querySelector(".topbar");
topbar?.insertBefore(themeToggle, topbar.querySelector(".avatar"));
updateThemeLabel();

const languageToggle = document.createElement("button");
languageToggle.type = "button";
languageToggle.className = "language-toggle";
const languageCopy = {
  th: {
    date: "บันทึกเล็ก ๆ ดูแลตัวเองทุกวัน", greeting: "ภาพรวมของคุณ", notice: "ผลนี้ใช้สำหรับติดตามลักษณะผิว ไม่ใช่การวินิจฉัยโรคหรือยืนยันสาเหตุ",
    severity: "ปานกลาง", scoreMeta: "ตัวเลขตัวอย่าง ไม่ใช่ผลวิเคราะห์ของคุณ", regions: "ดูผลล่าสุด →", next: "ติดตามครั้งต่อไป", captureTitle: "พร้อมบันทึกภาพใหม่ไหม?", captureText: "หน้าสด · หน้าตรง · แสงกระจาย เพื่อให้เทียบผลได้ดีขึ้น", captureButton: "ถ่ายภาพใหม่ →",
    overviewTitle: "ภาพรวมผลล่าสุด", overviewEyebrow: "SKIN OVERVIEW", scoreLabel: "ตัวอย่าง UI · WRINKLE SCORE", motionLabel: "วิดีโอภาพเคลื่อนไหวประกอบภาพรวมผิว", detailEyebrow: "ผลภาพล่าสุด", latest: "สิ่งที่ตรวจพบจากภาพ", detail: "ดูรายละเอียดทั้งหมด →", eye: "รอบดวงตา", forehead: "หน้าผาก", mild: "เล็กน้อย", quality: "คุณภาพภาพ", passed: "ผ่าน", usable: "ภาพผ่านเกณฑ์", rules: "คำแนะนำจากกฎ", barrier: "ดูแลเกราะป้องกันผิว", rationale: "แสดงจากข้อมูลที่คุณรายงานร่วมกับผลภาพที่ confidence ผ่านเกณฑ์", safety: "ดูเหตุผลและ safety check →", language: "EN",
  },
  en: {
    date: "Your skin, sleep and hydration in one place.", greeting: "Your daily overview", notice: "This result supports skin tracking; it is not a diagnosis or confirmation of cause.",
    severity: "Moderate", scoreMeta: "Sample score—not your personal analysis", regions: "View latest result →", next: "NEXT CHECK-IN", captureTitle: "Ready to record a new image?", captureText: "Bare face · forward-facing · diffused light for a more comparable result", captureButton: "Capture new image →",
    overviewTitle: "Latest overview", overviewEyebrow: "SKIN OVERVIEW", scoreLabel: "SAMPLE UI · WRINKLE SCORE", motionLabel: "Motion video accompanying the skin overview", detailEyebrow: "LATEST IMAGE", latest: "Detected from image", detail: "View all details →", eye: "Periocular area", forehead: "Forehead", mild: "Mild", quality: "Image quality", passed: "Passed", usable: "Quality check passed", rules: "Rule-based guidance", barrier: "Support your skin barrier", rationale: "Uses your reported information together with image signals that passed the confidence threshold.", safety: "View rationale & safety check →", language: "TH",
  },
};
function setText(selector, value, index = 0) {
  const elements = document.querySelectorAll(selector);
  if (elements[index]) elements[index].textContent = value;
}
function applyLanguage(language) {
  const copy = languageCopy[language];
  document.documentElement.lang = language;
  document.querySelector(".home-dashboard-shell")?.setAttribute("lang", language);
  localStorage.setItem("aphrodize-language", language);
  renderNavigation(language);
  setText(".home-intro", copy.date); setText(".topbar h1", copy.greeting); setText(".notice p", copy.notice);
  setText(".home-overview-heading h2", copy.overviewTitle); setText(".home-overview-heading .eyebrow", copy.overviewEyebrow);
  setText(".home-overview-score > .eyebrow", copy.scoreLabel);
  setText(".home-overview-score h2", language === "th" ? "รู้จักผิวของคุณในทุกวัน" : "Know your skin. Day by day.");
  setText(".home-overview-score > p", language === "th" ? "ติดตามผลจากภาพใบหน้า พร้อมดูพฤติกรรมการนอนและการดื่มน้ำของคุณ" : "Track your skin images alongside your sleep and hydration habits.");
  setText(".home-overview-score .primary-button span", language === "th" ? "วิเคราะห์ภาพผิว" : "Analyze skin");
  setText(".home-media-label", language === "th" ? "วิดีโอประกอบ · ไม่ใช่ผลวิเคราะห์" : "Background video, not an analysis result");
  setText(".home-log-action span", language === "th" ? "บันทึกวันนี้" : "Log today");
  setText(".home-safety-note", language === "th" ? "คะแนนและสัญญาณใช้เพื่อติดตามข้อมูลส่วนบุคคล ไม่ใช่การวินิจฉัยโรค" : "Scores and signals support personal tracking; they are not a medical diagnosis.");
  setText(".home-detail-card .section-heading .eyebrow", copy.detailEyebrow);
  document.querySelector(".home-motion-video")?.setAttribute("aria-label", copy.motionLabel);
  setText(".capture-card .eyebrow", copy.next); setText(".capture-card h2", copy.captureTitle); setText(".capture-card p:not(.eyebrow)", copy.captureText); setText(".capture-card .primary-button", copy.captureButton);
  setText(".section-heading h2", copy.latest); setText(".section-heading .text-button", copy.detail); setText(".result-card .eyebrow", copy.eye, 0); setText(".result-card h3", copy.severity, 0); setText(".result-card .eyebrow", copy.forehead, 1); setText(".result-card h3", copy.mild, 1); setText(".result-card .eyebrow", copy.quality, 2); setText(".result-card h3", copy.passed, 2); setText(".result-card .metadata", copy.usable, 2);
  setText(".sources-grid article .eyebrow", copy.rules); setText(".sources-grid article h2", copy.barrier); setText(".sources-grid article p:not(.eyebrow)", copy.rationale); setText(".sources-grid article .text-button", copy.safety);
  languageToggle.textContent = copy.language;
  languageToggle.setAttribute("aria-label", language === "th" ? "Change language to English" : "Switch to Thai");
  homeButton.setAttribute("aria-label", language === "th" ? "หน้าแรก" : "Home");
  homeButton.title = homeButton.getAttribute("aria-label");
  profileButton.setAttribute("aria-label", language === "th" ? "เข้าสู่ระบบ" : "Sign in");
  profileButton.title = profileButton.getAttribute("aria-label");
  document.querySelector(".app-navigation-links")?.setAttribute("aria-label", language === "th" ? "เมนูหลัก" : "Primary navigation");
  document.querySelector(".home-dashboard-grid")?.setAttribute("aria-label", language === "th" ? "ภาพรวมผิวและสุขภาพรายวัน" : "Skin and daily health overview");
  updateThemeLabel();
  window.dispatchEvent(new CustomEvent("aphrodize-language-change", { detail: language }));
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
applyLanguage(localStorage.getItem("aphrodize-language") === "th" ? "th" : "en");

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
