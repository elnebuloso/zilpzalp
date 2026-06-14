/* ZilpZalp — Theme, Toast-Auto-Dismiss und Prüfungs-Interaktion (live Namensvorschau).
   Vanilla-Port aus den 5a-Mockups. Polling läuft über HTMX-Attribute. */
(function () {
  // ---------- Theme ----------
  function applyTheme(theme) {
    document.documentElement.setAttribute("data-theme", theme);
    try { localStorage.setItem("zz-theme", theme); } catch (e) {}
  }
  function initTheme() {
    var theme;
    try { theme = localStorage.getItem("zz-theme"); } catch (e) {}
    if (!theme) {
      theme = "dark";  // Default: Dark, unabhängig von der OS-Einstellung
    }
    applyTheme(theme);
  }
  initTheme();

  document.addEventListener("click", function (e) {
    var toggle = e.target.closest("[data-theme-toggle]");
    if (toggle) {
      var current = document.documentElement.getAttribute("data-theme");
      applyTheme(current === "dark" ? "light" : "dark");
      return;
    }
    var close = e.target.closest("[data-toast-close]");
    if (close) { close.closest(".toast").remove(); }
  });

  // ---------- Toast-Auto-Dismiss ----------
  function armToasts(root) {
    (root || document).querySelectorAll(".toast:not([data-armed])").forEach(function (t) {
      t.setAttribute("data-armed", "1");
      setTimeout(function () { t.classList.add("out"); }, 3600);
      setTimeout(function () { t.remove(); }, 3950);
    });
  }
  armToasts(document);
  document.body.addEventListener("htmx:afterSwap", function (e) { armToasts(e.target); });

  // ---------- Filename helpers (mirror web/naming.py) ----------
  function slug(s) {
    return (s || "").trim().replace(/\s+/g, "-").replace(/[\/\\:*?"<>|]/g, "");
  }
  function buildName(template, parts, ext) {
    return template
      .replace("{date}", parts.date || "")
      .replace("{sender}", slug(parts.sender) || "Unbekannt")
      .replace("{doctype}", slug(parts.doctype) || "Dokument")
      .replace("{description}", slug(parts.description)) + ext;
  }

  // ---------- Review interaction ----------
  function initReview(root) {
    var form = (root || document).querySelector("#review-form");
    if (!form || form.getAttribute("data-init")) return;
    form.setAttribute("data-init", "1");

    var ext = form.getAttribute("data-ext") || ".pdf";
    var dateKind = form.querySelector("input[name=date_kind]");
    var dateValue = form.querySelector("input[name=date_value]");
    var manualInput = form.querySelector("#manual-date");
    var confirmBtn = form.querySelector("#confirm-btn");
    var preview = form.querySelector("#np-final");
    var hint = form.querySelector("#confirm-hint");

    function currentDate() {
      if (dateKind.value === "manual") return manualInput ? manualInput.value : "";
      return dateValue.getAttribute("data-selected-date") || "";
    }
    function selectedPattern() {
      var sel = form.querySelector("select[name=pattern]");
      var opt = sel.options[sel.selectedIndex];
      return { template: opt.getAttribute("data-template") };
    }
    function targetCount() {
      return form.querySelectorAll("input[name=targets]:checked").length;
    }
    function refresh() {
      var date = currentDate();
      dateValue.value = date;
      var parts = {
        date: date,
        sender: form.querySelector("input[name=sender]").value,
        doctype: form.querySelector("input[name=doctype]").value,
        description: form.querySelector("textarea[name=description]").value,
      };
      preview.textContent = buildName(selectedPattern().template, parts, ext);
      var ok = !!date && targetCount() > 0;
      confirmBtn.disabled = !ok;
      if (hint) {
        hint.textContent = !date ? "Bitte ein Datum wählen."
          : targetCount() === 0 ? "Mindestens einen Zielordner wählen." : "";
      }
    }

    // date option click
    form.querySelectorAll(".date-opt").forEach(function (opt) {
      opt.addEventListener("click", function () {
        form.querySelectorAll(".date-opt").forEach(function (o) { o.classList.remove("sel"); });
        var manual = form.querySelector(".manual-date");
        if (manual) manual.classList.remove("sel");
        opt.classList.add("sel");
        dateKind.value = "candidate";
        dateValue.setAttribute("data-selected-date", opt.getAttribute("data-date"));
        refresh();
      });
    });
    var manualRow = form.querySelector(".manual-date");
    if (manualRow) {
      manualRow.addEventListener("click", function (e) {
        form.querySelectorAll(".date-opt").forEach(function (o) { o.classList.remove("sel"); });
        manualRow.classList.add("sel");
        dateKind.value = "manual";
        refresh();
      });
    }
    if (manualInput) manualInput.addEventListener("input", refresh);

    // folder chips toggle a hidden checkbox
    form.querySelectorAll(".folder-chip").forEach(function (chip) {
      chip.addEventListener("click", function () {
        var box = form.querySelector("input[name=targets][value='" + chip.getAttribute("data-path") + "']");
        box.checked = !box.checked;
        chip.classList.toggle("on", box.checked);
        var mark = chip.querySelector(".fk-box");
        mark.innerHTML = box.checked
          ? '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" style="width:12px;height:12px"><path d="M5 12.5l4.5 4.5L19 7"/></svg>'
          : "";
        refresh();
      });
    });

    form.querySelectorAll("input[name=sender], input[name=doctype], textarea[name=description], select[name=pattern]")
      .forEach(function (el) { el.addEventListener("input", refresh); });

    refresh();
  }
  initReview(document);
  document.body.addEventListener("htmx:afterSwap", function (e) { initReview(e.target); });
})();
