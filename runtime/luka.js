/*
 * luka.js – Aufgaben-Runtime für LUKA
 *
 * Aufgaben-HTML muss keine JS-Logik enthalten. Diese Runtime:
 *  - sammelt alle Antwortfelder (input/select/textarea mit name ODER id),
 *  - füllt sie beim Öffnen mit der letzten Abgabe des Schülers vor,
 *  - sendet die Antworten beim Klick auf "Abgeben" (unbegrenzt oft möglich).
 *
 * Unterstützt zwei Formate:
 *  - Fragmente: Felder mit name-Attribut (klassisch)
 *  - Vollformat/Lernpfade: Felder mit id-Attribut (name fehlt → id als Key)
 *
 * Erwartet window.LUKA_TASK = { slug, title }.
 */
(function () {
  "use strict";

  var task = window.LUKA_TASK || {};
  var slug = task.slug;
  var container = document.getElementById("luka-task-body") || document.body;

  // Sammelt alle Antwortfelder: input/select/textarea mit name ODER id.
  // Radio-Buttons ohne name werden übersprungen (nicht auswertbar).
  function collectFields() {
    return Array.prototype.slice.call(
      container.querySelectorAll(
        "input[name], select[name], textarea[name], " +
        "input[id]:not([name]), select[id]:not([name]), textarea[id]:not([name])"
      )
    ).filter(function (el) {
      // Radio/Checkbox ohne name sind einzeln nicht sinnvoll auswertbar,
      // aber Checkboxen in Lernpfaden haben oft data-correct statt name.
      // Wir sammeln sie trotzdem über ihre id.
      if ((el.type === "radio" || el.type === "checkbox") && !el.name && !el.id) return false;
      return true;
    });
  }

  // Liefert den Key für ein Feld: name wenn vorhanden, sonst id.
  function fieldKey(el) {
    return el.name || el.id || "";
  }

  function collectAnswers() {
    var answers = {};
    collectFields().forEach(function (el) {
      var key = fieldKey(el);
      if (!key) return;
      if (el.type === "radio") {
        if (el.checked) answers[key] = el.value;
        else if (!(key in answers)) answers[key] = answers[key] || "";
      } else if (el.type === "checkbox") {
        if (!Array.isArray(answers[key])) answers[key] = [];
        if (el.checked) answers[key].push(el.value);
      } else {
        answers[key] = el.value;
      }
    });
    return answers;
  }

  function applyAnswers(answers) {
    if (!answers) return;
    collectFields().forEach(function (el) {
      var key = fieldKey(el);
      if (!(key in answers)) return;
      var value = answers[key];
      if (el.type === "radio") {
        el.checked = el.value === value;
      } else if (el.type === "checkbox") {
        el.checked = Array.isArray(value) && value.indexOf(el.value) !== -1;
      } else {
        el.value = value;
      }
    });
  }

  function buildBar() {
    var bar = document.createElement("div");
    bar.className = "luka-bar";
    bar.style.cssText = "position:fixed;bottom:0;left:0;right:0;z-index:9998;background:rgba(255,255,255,.95);border-top:1px solid #dbe3ef;padding:10px 16px;display:flex;align-items:center;gap:1rem;flex-wrap:wrap;font-family:system-ui,sans-serif";

    var btn = document.createElement("button");
    btn.className = "luka-btn";
    btn.type = "button";
    btn.textContent = "Abgeben";
    btn.style.cssText = "border:0;border-radius:999px;padding:10px 20px;font-weight:700;font-size:.95rem;cursor:pointer;background:#2563eb;color:#fff;box-shadow:0 1px 3px rgba(0,0,0,.2)";

    var status = document.createElement("span");
    status.className = "luka-status";
    status.style.cssText = "font-size:.85rem;color:#146c2e";

    bar.appendChild(btn);
    bar.appendChild(status);
    document.body.appendChild(bar);
    return { btn: btn, status: status };
  }

  function setStatus(status, message, isError) {
    status.textContent = message;
    status.className = "luka-status" + (isError ? " error" : "");
  }

  function submit(ui) {
    ui.btn.disabled = true;
    setStatus(ui.status, "Wird gespeichert …", false);
    fetch("/api/submissions", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "same-origin",
      body: JSON.stringify({ slug: slug, answers: collectAnswers() }),
    })
      .then(function (res) {
        if (!res.ok) throw new Error("HTTP " + res.status);
        return res.json();
      })
      .then(function () {
        setStatus(ui.status, "Gespeichert ✓ (jederzeit korrigierbar)", false);
      })
      .catch(function () {
        setStatus(ui.status, "Speichern fehlgeschlagen. Bist du eingeloggt?", true);
      })
      .finally(function () {
        ui.btn.disabled = false;
      });
  }

  function loadLast() {
    if (!slug) return;
    fetch("/api/submissions/" + encodeURIComponent(slug), {
      credentials: "same-origin",
    })
      .then(function (res) {
        if (!res.ok) return null;
        return res.json();
      })
      .then(function (data) {
        if (data && data.answers) applyAnswers(data.answers);
      })
      .catch(function () {});
  }

  document.addEventListener("DOMContentLoaded", function () {
    if (!slug) return;
    var ui = buildBar();
    ui.btn.addEventListener("click", function () {
      submit(ui);
    });
    loadLast();
  });

  // Stilles Auto-Save: speichert Antworten ohne UI-Feedback.
  // Wird von Lernpfaden nach jedem Schritt aufgerufen.
  var saveTimer = null;
  function autoSave() {
    if (!slug) return;
    if (saveTimer) clearTimeout(saveTimer);
    saveTimer = setTimeout(function () {
      fetch("/api/submissions", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "same-origin",
        body: JSON.stringify({ slug: slug, answers: collectAnswers() }),
      }).catch(function () {});
      saveTimer = null;
    }, 800);
  }

  // Optionale JS-API für Sonderfälle.
  window.LUKA = {
    collectAnswers: collectAnswers,
    applyAnswers: applyAnswers,
    autoSave: autoSave,
  };
})();
