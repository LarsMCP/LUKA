/*
 * luka.js – Aufgaben-Runtime für LUKA
 *
 * Aufgaben-HTML muss keine JS-Logik enthalten. Diese Runtime:
 *  - sammelt alle Antwortfelder (input/select/textarea mit name-Attribut),
 *  - füllt sie beim Öffnen mit der letzten Abgabe des Schülers vor,
 *  - sendet die Antworten beim Klick auf "Abgeben" (unbegrenzt oft möglich).
 *
 * Erwartet window.LUKA_TASK = { slug, title }.
 */
(function () {
  "use strict";

  var task = window.LUKA_TASK || {};
  var slug = task.slug;
  var container = document.getElementById("luka-task-body") || document.body;

  function collectFields() {
    return Array.prototype.slice.call(
      container.querySelectorAll("input[name], select[name], textarea[name]")
    );
  }

  function collectAnswers() {
    var answers = {};
    collectFields().forEach(function (el) {
      var name = el.name;
      if (el.type === "radio") {
        if (el.checked) answers[name] = el.value;
        else if (!(name in answers)) answers[name] = answers[name] || "";
      } else if (el.type === "checkbox") {
        if (!Array.isArray(answers[name])) answers[name] = [];
        if (el.checked) answers[name].push(el.value);
      } else {
        answers[name] = el.value;
      }
    });
    return answers;
  }

  function applyAnswers(answers) {
    if (!answers) return;
    collectFields().forEach(function (el) {
      if (!(el.name in answers)) return;
      var value = answers[el.name];
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

    var btn = document.createElement("button");
    btn.className = "luka-btn";
    btn.type = "button";
    btn.textContent = "Abgeben";

    var status = document.createElement("span");
    status.className = "luka-status";

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

  // Optionale JS-API für Sonderfälle.
  window.LUKA = {
    collectAnswers: collectAnswers,
    applyAnswers: applyAnswers,
  };
})();
