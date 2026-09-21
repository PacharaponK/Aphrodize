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
