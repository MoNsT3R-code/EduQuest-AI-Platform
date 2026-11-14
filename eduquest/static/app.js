// Small enhancements on top of pages that already work without JavaScript.
(function () {
  "use strict";

  // Picture password: a 3×3 pad that fills the three rows in order
  document.querySelectorAll("[data-picture-form]").forEach(function (form) {
    var rows = Array.prototype.slice.call(form.querySelectorAll(".pic-row"));
    if (!rows.length) return;
    var wrap = form.querySelector(".picture-password");
    var pad = document.createElement("div");
    pad.className = "pic-pad";
    var slotsEl = document.createElement("div");
    slotsEl.className = "pic-slots";
    slotsEl.setAttribute("aria-live", "polite");
    var slots = rows.map(function (_, i) {
      var s = document.createElement("span");
      s.className = "pic-slot";
      s.textContent = i + 1;
      slotsEl.appendChild(s);
      return s;
    });
    var clear = document.createElement("button");
    clear.type = "button";
    clear.className = "btn btn-small btn-ghost";
    clear.textContent = "Clear";
    slotsEl.appendChild(clear);

    function chosen() {
      return rows.map(function (row) { return row.querySelector("input:checked"); });
    }
    function render() {
      chosen().forEach(function (input, i) {
        var label = input && row(i).querySelector('label[for="' + input.id + '"] span');
        slots[i].textContent = label ? label.textContent : i + 1;
        slots[i].classList.toggle("filled", !!input);
      });
    }
    function row(i) { return rows[i]; }

    rows[0].querySelectorAll("label.pic").forEach(function (label) {
      var b = document.createElement("button");
      b.type = "button";
      b.className = "pic";
      b.innerHTML = label.innerHTML;
      var value = document.getElementById(label.htmlFor).value;
      b.addEventListener("click", function () {
        var next = chosen().indexOf(null);
        if (next === -1) return;
        rows[next].querySelector('input[value="' + value + '"]').checked = true;
        render();
      });
      pad.appendChild(b);
    });
    clear.addEventListener("click", function () {
      rows.forEach(function (r) { r.querySelectorAll("input").forEach(function (i) { i.checked = false; }); });
      render();
    });
    rows.forEach(function (r) { r.hidden = true; });
    wrap.appendChild(slotsEl);
    wrap.appendChild(pad);
    render();
  });

  // Login: the submit label follows "new" or "returning"
  document.querySelectorAll(".login-form").forEach(function (form) {
    var btn = form.querySelector("[data-submit-label-new]");
    function update() {
      var isNew = form.querySelector("#mode-new").checked;
      btn.textContent = isNew ? btn.dataset.submitLabelNew : btn.dataset.submitLabelReturn;
      form.querySelectorAll("[data-new-only]").forEach(function (el) { el.hidden = !isNew; });
    }
    form.querySelectorAll("input[name=mode]").forEach(function (r) { r.addEventListener("change", update); });
    update();
  });

  // Quest timer, counting up from the server's start time
  document.querySelectorAll("[data-timer]").forEach(function (el) {
    var start = Date.now() - Number(el.dataset.start) * 1000;
    var text = el.querySelector("[data-timer-text]");
    setInterval(function () {
      var s = Math.floor((Date.now() - start) / 1000);
      text.textContent = Math.floor(s / 60) + ":" + String(s % 60).padStart(2, "0");
    }, 1000);
  });

  // Number keys 1-4 pick an answer
  var answers = document.querySelector("[data-answers]");
  if (answers) {
    document.addEventListener("keydown", function (e) {
      if (e.altKey || e.ctrlKey || e.metaKey || /input|textarea|select/i.test(e.target.tagName)) return;
      var b = answers.querySelector('button[value="' + (Number(e.key) - 1) + '"]');
      if (b && !b.disabled) b.click();
    });
    // Stop a double-click from sending two answers
    answers.addEventListener("submit", function () {
      setTimeout(function () { answers.querySelectorAll("button").forEach(function (b) { b.disabled = true; }); }, 0);
    });
  }

  // After an answer, Enter (or Space) anywhere moves on, so the keyboard flow is 1-4 then Enter
  var next = document.querySelector("[data-autofocus]");
  if (next) {
    next.focus({ preventScroll: true });
    document.addEventListener("keydown", function (e) {
      if ((e.key === "Enter" || e.key === " ") && (e.target === document.body || e.target === document.querySelector("main"))) {
        e.preventDefault();
        next.click();
      }
    });
  }

  // Read the question aloud (helpful for younger readers)
  document.querySelectorAll("[data-read-aloud]").forEach(function (btn) {
    if (!("speechSynthesis" in window)) return;
    btn.hidden = false;
    btn.addEventListener("click", function () {
      var target = document.querySelector(btn.dataset.readAloud);
      var opts = Array.prototype.map.call(document.querySelectorAll(".answer-text"), function (o, i) {
        return (i + 1) + ". " + o.textContent;
      });
      window.speechSynthesis.cancel();
      var u = new SpeechSynthesisUtterance(target.textContent + " " + opts.join(". "));
      u.rate = 0.9;
      window.speechSynthesis.speak(u);
    });
  });

  document.querySelectorAll("[data-confirm]").forEach(function (btn) {
    btn.addEventListener("click", function (e) {
      if (!window.confirm(btn.dataset.confirm)) e.preventDefault();
    });
  });

  // 8-bit sound effects, synthesised with Web Audio (no audio files). Mute is remembered.
  var Sound = (function () {
    var ctx = null;
    var on = true;
    try { on = localStorage.getItem("eq-sound") !== "off"; } catch (e) { /* storage blocked */ }
    var SONGS = {
      correct: [[523, 0], [659, 0.07], [784, 0.14], [1047, 0.21]],
      wrong: [[220, 0, "sawtooth", 0.18], [165, 0.16, "sawtooth", 0.24]],
      oops: [[330, 0, "triangle", 0.12], [262, 0.12, "triangle", 0.16]],
      hint: [[1319, 0, "triangle"], [1760, 0.08, "triangle"], [2093, 0.16, "triangle"]],
      start: [[392, 0], [392, 0.12], [523, 0.24, "square", 0.25]],
      coin: [[988, 0], [1319, 0.07, "square", 0.2]],
      click: [[660, 0, "square", 0.035]],
      victory: [[523, 0], [659, 0.12], [784, 0.24], [1047, 0.36, "square", 0.18], [784, 0.54], [1047, 0.66, "square", 0.4]],
      escape: [[392, 0, "triangle"], [330, 0.15, "triangle"], [262, 0.3, "triangle", 0.3]],
      levelup: [[523, 0], [659, 0.1], [784, 0.2], [1047, 0.3], [1319, 0.42, "square", 0.18], [1568, 0.6, "square", 0.45]]
    };
    function audio() {
      if (!ctx) {
        var AC = window.AudioContext || window.webkitAudioContext;
        if (!AC) return null;
        ctx = new AC();
      }
      if (ctx.state === "suspended") ctx.resume();
      return ctx;
    }
    function play(name) {
      var song = SONGS[name];
      if (!on || !song) return;
      var a = audio();
      if (!a) return;
      song.forEach(function (n) {
        var t = a.currentTime + n[1], len = n[3] || 0.1;
        var osc = a.createOscillator(), gain = a.createGain();
        osc.type = n[2] || "square";
        osc.frequency.setValueAtTime(n[0], t);
        gain.gain.setValueAtTime(0.0001, t);
        gain.gain.exponentialRampToValueAtTime(0.06, t + 0.01);
        gain.gain.exponentialRampToValueAtTime(0.0001, t + len);
        osc.connect(gain).connect(a.destination);
        osc.start(t);
        osc.stop(t + len + 0.02);
      });
    }
    function setOn(value) {
      on = value;
      try { localStorage.setItem("eq-sound", on ? "on" : "off"); } catch (e) { /* storage blocked */ }
    }
    return { play: play, setOn: setOn, isOn: function () { return on; } };
  })();

  document.querySelectorAll("[data-sound-toggle]").forEach(function (btn) {
    btn.hidden = false;
    function show() {
      btn.textContent = Sound.isOn() ? "🔊" : "🔇";
      btn.setAttribute("aria-pressed", String(Sound.isOn()));
      btn.setAttribute("aria-label", Sound.isOn() ? "Sound effects on" : "Sound effects off");
    }
    btn.addEventListener("click", function () { Sound.setOn(!Sound.isOn()); show(); Sound.play("click"); });
    show();
  });

  // The page says which sound fits what just happened (a hit, a miss, a victory…)
  var cue = document.body.dataset.sound;
  if (cue) setTimeout(function () { Sound.play(cue); }, 250);
  document.addEventListener("click", function (e) {
    if (e.target.closest("button.answer, .btn, .buddy-option")) Sound.play("click");
  });

  // A short burst of pixel confetti for a level up or new badge
  var party = document.querySelector("[data-celebrate]");
  if (party && !window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
    var colors = ["#ffd700", "#2ecc71", "#e74c3c", "#5c94fc", "#e07c24"];
    for (var i = 0; i < 40; i++) {
      var c = document.createElement("span");
      c.className = "confetti";
      c.style.setProperty("--x", Math.random() * 100 + "%");
      c.style.setProperty("--d", (0.8 + Math.random() * 1.4).toFixed(2) + "s");
      c.style.setProperty("--c", colors[i % colors.length]);
      party.appendChild(c);
    }
  }
})();
