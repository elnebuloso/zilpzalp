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
    var openBtn = e.target.closest("[data-drawer-open]");
    if (openBtn) {
      var drawer = document.getElementById(openBtn.getAttribute("data-drawer-open"));
      if (drawer) {
        drawer.hidden = false;
        var firstTab = drawer.querySelector("[data-drawer-tab]");
        if (firstTab) firstTab.click();  // lazy-load the default (Markdown) pane
      }
      return;
    }
    var closeBtn = e.target.closest("[data-drawer-close]");
    if (closeBtn) { closeBtn.closest(".drawer-scrim").hidden = true; return; }
    var scrim = e.target.closest(".drawer-scrim");
    if (scrim && e.target === scrim) { scrim.hidden = true; return; }
    var tab = e.target.closest("[data-drawer-tab]");
    if (tab) {
      tab.parentNode.querySelectorAll("[data-drawer-tab]").forEach(function (b) {
        b.classList.remove("active");
      });
      tab.classList.add("active");
      // htmx handles the fetch via the tab's hx-get attributes
    }
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
    var msgDate = form.getAttribute("data-msg-date") || "";
    var msgTarget = form.getAttribute("data-msg-target") || "";
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
        hint.textContent = !date ? msgDate
          : targetCount() === 0 ? msgTarget : "";
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

  // ---------- Sequential PDF uploader ----------
  function initUpload() {
    var zone = document.getElementById("upload-zone");
    var input = document.getElementById("upload-input");
    var list = document.getElementById("upload-list");
    if (!zone || !input || !list) return;

    var L = {
      queued: zone.getAttribute("data-label-queued"),
      uploading: zone.getAttribute("data-label-uploading"),
      done: zone.getAttribute("data-label-done"),
      error: zone.getAttribute("data-label-error"),
    };
    var notPdfMsg = zone.getAttribute("data-msg-not-pdf");
    var pending = [];      // {file, row, bar, state}
    var busy = false;

    function isPdf(file) {
      return /\.pdf$/i.test(file.name) || file.type === "application/pdf";
    }
    function addRow(label, stateText) {
      var row = document.createElement("div");
      row.className = "upload-row";
      row.innerHTML =
        '<div class="ur-head"><span class="ur-name"></span>' +
        '<span class="ur-state"></span></div>' +
        '<div class="ur-bar"><span></span></div>';
      row.querySelector(".ur-name").textContent = label;
      row.querySelector(".ur-state").textContent = stateText;
      list.appendChild(row);
      return row;
    }
    function setState(item, cls, stateText) {
      item.row.className = "upload-row" + (cls ? " " + cls : "");
      item.row.querySelector(".ur-state").textContent = stateText;
    }
    function enqueue(files) {
      list.replaceChildren();
      Array.prototype.forEach.call(files, function (file) {
        if (!isPdf(file)) {
          var row = addRow(file.name, notPdfMsg);
          row.className = "upload-row error";
          return;
        }
        var r = addRow(file.name, L.queued);
        pending.push({ file: file, row: r, bar: r.querySelector(".ur-bar > span") });
      });
      pump();
    }
    function pump() {
      if (busy) return;
      var item = pending.shift();
      if (!item) return;
      busy = true;
      setState(item, "", L.uploading);
      var form = new FormData();
      form.append("file", item.file, item.file.name);
      var xhr = new XMLHttpRequest();
      xhr.open("POST", "/upload");
      xhr.upload.onprogress = function (e) {
        if (e.lengthComputable) {
          item.bar.style.width = Math.round((e.loaded / e.total) * 100) + "%";
        }
      };
      xhr.onload = function () {
        if (xhr.status >= 200 && xhr.status < 300) {
          item.bar.style.width = "100%";
          setState(item, "done", L.done);
        } else {
          var msg = L.error;
          try { msg = JSON.parse(xhr.responseText).error || msg; } catch (e) {}
          setState(item, "error", msg);
        }
        busy = false;
        pump();
      };
      xhr.onerror = function () {
        setState(item, "error", L.error);
        busy = false;
        pump();
      };
      xhr.send(form);
    }

    zone.addEventListener("click", function () { input.click(); });
    input.addEventListener("change", function () {
      if (input.files && input.files.length) enqueue(input.files);
      input.value = "";
    });
    ["dragenter", "dragover"].forEach(function (ev) {
      zone.addEventListener(ev, function (e) {
        e.preventDefault();
        zone.classList.add("drag");
      });
    });
    ["dragleave", "drop"].forEach(function (ev) {
      zone.addEventListener(ev, function (e) {
        e.preventDefault();
        zone.classList.remove("drag");
      });
    });
    zone.addEventListener("drop", function (e) {
      if (e.dataTransfer && e.dataTransfer.files.length) enqueue(e.dataTransfer.files);
    });
  }
  initUpload();
})();
