// Theme-Umschalter (Mockup). In 5b sinngemäß als kleine Vanilla-JS-Datei neben HTMX.
// Standard folgt prefers-color-scheme; die Wahl wird in localStorage gemerkt.
(function () {
  var KEY = "zz-theme";
  var root = document.documentElement;

  function systemDark() {
    return window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches;
  }
  function effective() {
    var saved = localStorage.getItem(KEY);
    return saved || (systemDark() ? "dark" : "light");
  }
  function apply(theme) {
    root.setAttribute("data-theme", theme);
    document.querySelectorAll(".theme-toggle").forEach(function (b) {
      b.classList.toggle("is-dark", theme === "dark");
      b.setAttribute("aria-label", theme === "dark" ? "Zu hellem Thema wechseln" : "Zu dunklem Thema wechseln");
    });
  }

  // beim Laden anwenden (verhindert Flackern, da app.js im <head> mit defer steht)
  apply(effective());

  window.toggleTheme = function () {
    var next = effective() === "dark" ? "light" : "dark";
    localStorage.setItem(KEY, next);
    apply(next);
  };
})();
