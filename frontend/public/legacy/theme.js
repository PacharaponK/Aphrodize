(function () {
  const storageKey = "aphrodize-theme";
  const root = document.documentElement;

  function applyTheme(theme) {
    const resolvedTheme = theme === "black" || theme === "dark" ? "black" : "pastel";
    root.dataset.theme = resolvedTheme;
    root.classList.toggle("dark", resolvedTheme === "black");
    root.style.colorScheme = resolvedTheme === "black" ? "dark" : "light";
    window.dispatchEvent(new Event("aphrodize-theme-change"));
    return resolvedTheme;
  }

  function setTheme(theme) {
    const resolvedTheme = applyTheme(theme);
    try {
      localStorage.setItem(storageKey, resolvedTheme);
    } catch {
      // Keep the in-memory choice even when browser storage is unavailable.
    }
  }

  window.addEventListener("storage", (event) => {
    if (event.key === storageKey && event.newValue) applyTheme(event.newValue);
  });

  let savedTheme = "pastel";
  try {
    const storedTheme = localStorage.getItem(storageKey);
    savedTheme = storedTheme === "black" || storedTheme === "dark" ? "black" : "pastel";
  } catch {
    // Light mode is the default when browser storage is unavailable.
  }
  applyTheme(savedTheme);
  window.AphrodizeTheme = { setTheme, current: () => root.dataset.theme };
}());
