// Curious Kids question tester. Plain JS, no build step. State lives in localStorage.
(function () {
  "use strict";

  const CATS = [
    { key: "what-am-i", name: "What Am I?", short: "What Am I?", color: "#6D3FC0", ink: "#fff" },
    { key: "true-false", name: "True or False", short: "True/False", color: "#1F7A4D", ink: "#fff" },
    { key: "more-or-less", name: "More or Less", short: "More/Less", color: "#F28C28", ink: "#1d1203" },
    { key: "this-or-that", name: "This or That", short: "This/That", color: "#C2255C", ink: "#fff" },
    { key: "pick-one", name: "Pick One", short: "Pick One", color: "#F5C518", ink: "#1d1700" },
  ];
  const CAT = Object.fromEntries(CATS.map((c) => [c.key, c]));
  const FLAGS = [
    { key: "bad", label: "Bad question" },
    { key: "hard", label: "Too hard" },
    { key: "great", label: "Great one" },
  ];

  const ICON = {
    speaker: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M11 5 6 9H3v6h3l5 4z"/><path d="M15.5 8.5a5 5 0 0 1 0 7"/><path d="M18.5 5.5a9 9 0 0 1 0 13"/></svg>',
    flag: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M5 21V4"/><path d="M5 4h11l-2 4 2 4H5"/></svg>',
    menu: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round"><path d="M4 7h16M4 12h16M4 17h16"/></svg>',
    star: '<svg viewBox="0 0 24 24" fill="currentColor"><path d="m12 2.8 2.8 5.8 6.3.8-4.6 4.4 1.2 6.3L12 17l-5.7 3.1 1.2-6.3L2.9 9.4l6.3-.8z"/></svg>',
    check: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><path d="m4 12.5 5 5L20 6.5"/></svg>',
    x: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round"><path d="M6 6l12 12M18 6 6 18"/></svg>',
    arrow: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h14M13 6l6 6-6 6"/></svg>',
  };

  // ---------- storage ----------
  const store = {
    get(k, fallback) {
      try { const v = localStorage.getItem("ck." + k); return v ? JSON.parse(v) : fallback; } catch (e) { return fallback; }
    },
    set(k, v) { try { localStorage.setItem("ck." + k, JSON.stringify(v)); } catch (e) { /* private mode */ } },
  };
  const settings = Object.assign({ autoRead: true, skipUnchecked: false, cats: CATS.map((c) => c.key) }, store.get("settings", {}));
  const freshSession = () => ({ started: new Date().toISOString(), answered: 0, correct: 0, byCat: {}, picks: [] });
  let session = store.get("session", null) || freshSession();
  let seen = store.get("seen", {});
  let flags = store.get("flags", {});
  const save = () => { store.set("settings", settings); store.set("session", session); store.set("seen", seen); store.set("flags", flags); };

  // ---------- data ----------
  const data = {};
  async function load() {
    await Promise.all(CATS.map(async (c) => {
      try {
        const r = await fetch("data/" + c.key + ".json", { cache: "no-cache" });
        data[c.key] = r.ok ? await r.json() : [];
      } catch (e) { data[c.key] = []; }
    }));
  }
  const pool = (cat) => {
    const all = data[cat] || [];
    if (!settings.skipUnchecked) return all;
    const ok = all.filter((q) => !q.needsReview);
    return ok.length ? ok : all;
  };
  const activeCats = () => settings.cats.filter((k) => pool(k).length);

  // ---------- helpers ----------
  const $ = (sel, root = document) => root.querySelector(sel);
  const esc = (s) => String(s == null ? "" : s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const rand = (n) => Math.floor(Math.random() * n);
  const shuffle = (a) => { a = a.slice(); for (let i = a.length - 1; i > 0; i--) { const j = rand(i + 1); [a[i], a[j]] = [a[j], a[i]]; } return a; };
  const cap = (s) => (s ? s[0].toUpperCase() + s.slice(1) : s);
  const bare = (s) => String(s || "").trim().replace(/[.!]+$/, "");

  function norm(s) {
    return String(s).toLowerCase()
      .replace(/[’']/g, "")
      .replace(/[^a-z0-9 ]+/g, " ")
      .replace(/^\s*(i am|im|you are|youre|its|it is)\s+/, " ")
      .replace(/^\s*(a|an|the|some)\s+/, " ")
      .replace(/\s+/g, " ").trim();
  }
  function lev(a, b) {
    const m = a.length, n = b.length;
    if (!m) return n; if (!n) return m;
    let prev = Array.from({ length: n + 1 }, (_, j) => j);
    for (let i = 1; i <= m; i++) {
      const cur = [i];
      for (let j = 1; j <= n; j++) cur[j] = Math.min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (a[i - 1] === b[j - 1] ? 0 : 1));
      prev = cur;
    }
    return prev[n];
  }
  function matches(guess, q) {
    const g = norm(guess);
    if (!g) return false;
    const targets = [q.answer].concat(q.accept || []).map(norm).filter(Boolean);
    return targets.some((t) => {
      const strip = (x) => x.replace(/(es|s)$/, "");
      if (g === t || strip(g) === strip(t)) return true;
      const allowed = t.length <= 4 ? 1 : t.length <= 8 ? 1 : 2;
      return lev(g, t) <= allowed || lev(strip(g), strip(t)) <= allowed;
    });
  }

  // ---------- speech ----------
  let voice = null;
  function pickVoice() {
    if (!("speechSynthesis" in window)) return;
    const vs = speechSynthesis.getVoices().filter((v) => /^en[-_]/i.test(v.lang));
    const pref = ["Samantha", "Google US English", "Ava", "Allison", "Karen", "Daniel", "Microsoft Aria"];
    voice = pref.map((n) => vs.find((v) => v.name.includes(n))).find(Boolean) || vs.find((v) => /en[-_]US/i.test(v.lang)) || vs[0] || null;
  }
  if ("speechSynthesis" in window) { pickVoice(); speechSynthesis.onvoiceschanged = pickVoice; }
  function say(text) {
    if (!("speechSynthesis" in window) || !text) return;
    speechSynthesis.cancel();
    const u = new SpeechSynthesisUtterance(text);
    if (voice) u.voice = voice;
    u.rate = 0.92; u.pitch = 1.05;
    const btn = $(".speak");
    if (btn) { btn.classList.add("on"); u.onend = u.onerror = () => btn.classList.remove("on"); }
    speechSynthesis.speak(u);
  }
  const autoSay = (t) => { if (settings.autoRead) say(t); };

  // ---------- picking ----------
  let current = null; // { q, cat, state }
  let lastCat = null;
  function pickQuestion() {
    const cats = activeCats();
    if (!cats.length) return null;
    // Pick a category first so small ones (More or Less) still show up, and avoid the same one twice in a row.
    let choices = cats.length > 1 ? cats.filter((c) => c !== lastCat) : cats;
    const cat = choices[rand(choices.length)];
    const all = pool(cat);
    const seenSet = new Set(seen[cat] || []);
    let fresh = all.filter((q) => !seenSet.has(q.id));
    if (!fresh.length) { seen[cat] = []; fresh = all; }
    const q = fresh[rand(fresh.length)];
    (seen[cat] = seen[cat] || []).push(q.id);
    lastCat = cat;
    save();
    return { q, cat };
  }

  function pickOneChoices(q) {
    let wrong = (q.choices || []).filter(Boolean).slice(0, 2);
    if (wrong.length < 2) {
      // Provisional data has no wrong choices yet: borrow short answers from other Pick One questions.
      const others = shuffle((data["pick-one"] || []).filter((o) => o.id !== q.id && o.answer && o.answer.length <= Math.max(24, q.answer.length * 1.6)));
      for (const o of others) { if (wrong.length >= 2) break; if (norm(o.answer) !== norm(q.answer) && !wrong.includes(o.answer)) wrong.push(o.answer); }
    }
    return shuffle([q.answer].concat(wrong));
  }

  // ---------- rendering ----------
  const app = $("#app");
  function setTheme(cat) {
    const c = CAT[cat];
    document.body.style.setProperty("--cat", c.color);
    document.body.style.setProperty("--on-cat", c.ink);
    document.body.style.setProperty("--on-cat-soft", c.ink === "#fff" ? "rgba(255,255,255,.82)" : "rgba(0,0,0,.66)");
    $('meta[name="theme-color"]').setAttribute("content", c.color);
  }

  function scoreText() { return session.correct + " / " + session.answered; }

  function renderShell() {
    app.innerHTML = `
      <div class="top">
        <div class="chips" id="chips">${CATS.map((c) => `<button class="chip" data-cat="${c.key}" aria-pressed="${settings.cats.includes(c.key)}" style="--c:${c.color}"><i></i>${esc(c.short)}</button>`).join("")}
        <button class="score" id="scoreBtn" aria-label="Score and settings">${ICON.star}<span id="scoreNum">${scoreText()}</span></button></div>
      </div>
      <div class="stage" id="stage"></div>`;
    $("#chips").addEventListener("click", (e) => {
      const b = e.target.closest(".chip"); if (!b) return;
      const k = b.dataset.cat;
      const on = settings.cats.includes(k);
      if (on && settings.cats.length === 1) return; // keep at least one
      settings.cats = on ? settings.cats.filter((x) => x !== k) : settings.cats.concat(k);
      b.setAttribute("aria-pressed", String(!on));
      save();
      if (on && current && current.cat === k) next();
      if (!current) next();
    });
    $("#scoreBtn").addEventListener("click", openStats);
    bindSwipe($("#stage"));
  }

  function next(animate) {
    if ("speechSynthesis" in window) speechSynthesis.cancel();
    const go = () => {
      const pick = pickQuestion();
      const stage = $("#stage");
      if (!pick) { current = null; stage.innerHTML = `<div class="empty">No questions in these categories yet.</div>`; return; }
      current = { q: pick.q, cat: pick.cat, done: false, clue: 0 };
      setTheme(pick.cat);
      renderQuestion();
      if (animate) { stage.classList.remove("swipe-out"); stage.classList.add("swipe-in"); setTimeout(() => stage.classList.remove("swipe-in"), 220); }
    };
    const stage = $("#stage");
    if (animate && stage) { stage.classList.add("swipe-out"); setTimeout(go, 170); } else go();
  }

  function readText() {
    const { q, cat } = current;
    switch (cat) {
      case "true-false": return "True or false? " + q.prompt;
      case "pick-one": {
        const c = (current.choices || []).map(bare);
        return q.prompt + " Is it " + c.slice(0, -1).join(", ") + ", or " + c[c.length - 1] + "?";
      }
      case "what-am-i": {
        const n = current.clue;
        return (n === 0 ? "What am I? " : "") + "Clue " + (n + 1) + ". " + q.clues[n];
      }
      default: return q.prompt;
    }
  }

  function renderQuestion() {
    const { q, cat } = current;
    const c = CAT[cat];
    const stage = $("#stage");
    let body = "";
    let answers = "";

    if (cat === "what-am-i") {
      const shown = q.clues.slice(0, current.clue + 1);
      body = `<ol class="clues">${shown.map((t, i) => `<li class="${i < current.clue ? "old" : ""}">${esc(t)}</li>`).join("")}</ol>
        <div class="clue-count">Clue ${current.clue + 1} of ${q.clues.length}</div>`;
    } else {
      body = `<div class="prompt">${esc(q.prompt)}</div>`;
    }

    if (!current.done) {
      if (cat === "true-false") {
        answers = `<div class="answers two">
          <button class="ans" data-a="true">${ICON.check}True</button>
          <button class="ans" data-a="false">${ICON.x}False</button></div>`;
      } else if (cat === "pick-one") {
        current.choices = current.choices || pickOneChoices(q);
        answers = `<div class="answers">${current.choices.map((t, i) => `<button class="ans" data-i="${i}">${esc(cap(t))}</button>`).join("")}</div>`;
      } else if (cat === "more-or-less" || cat === "this-or-that") {
        const opts = q.options || [];
        answers = `<div class="answers ${opts.length === 2 ? "two" : ""}">${opts.map((t, i) => `<button class="ans" data-i="${i}">${esc(cap(t))}</button>`).join("")}</div>`;
      } else if (cat === "what-am-i") {
        const more = current.clue < q.clues.length - 1;
        answers = `<div class="answers">
          <div class="hint" id="hint"></div>
          <form class="type-row" id="typeForm" autocomplete="off">
            <input id="guess" placeholder="Type it" autocapitalize="off" autocorrect="off" spellcheck="false" enterkeyhint="go">
            <button class="ans" type="submit">Check</button>
          </form>
          <div class="answers ${more ? "two" : ""}" style="padding-top:0;margin-top:0">
            ${more ? `<button class="ans small ghost" id="nextClue">Next clue</button>` : ""}
            <button class="ans small" id="sayIt">Say it out loud</button>
          </div></div>`;
      }
    }

    const flagged = flags[q.id] && flags[q.id].flags.length;
    stage.classList.toggle("done", !!current.done);
    stage.innerHTML = `
      <div class="label-row"><div class="cat-label">${esc(c.name)}</div></div>
      ${body}
      <button class="speak" id="speak">${ICON.speaker}Read it</button>
      ${answers}
      <div id="revealBox"></div>
      <div class="bottom">
        ${current.done ? `<button class="next" id="nextBtn">Next ${ICON.arrow}</button>` : `<button class="skip" id="skipBtn">Skip</button>`}
        <button class="flag-btn ${flagged ? "has" : ""}" id="flagBtn" aria-label="Flag this question">${ICON.flag}</button>
      </div>`;

    $("#speak").onclick = () => say(current.done && current.revealText ? current.revealText : readText());
    $("#flagBtn").onclick = openFlags;
    if (current.done) {
      $("#nextBtn").onclick = () => next(true);
      renderReveal();
      const nb = $("#nextBtn");
      if (nb && nb.getBoundingClientRect().bottom > innerHeight) nb.scrollIntoView({ block: "end", behavior: "smooth" });
    }
    else $("#skipBtn").onclick = () => next(true);

    stage.querySelectorAll(".answers .ans[data-a], .answers .ans[data-i]").forEach((b) => b.addEventListener("click", () => answer(b)));
    if (cat === "what-am-i" && !current.done) bindWhatAmI();
    if (!current.done && !current.readOnce) { current.readOnce = true; autoSay(readText()); }
  }

  function bindWhatAmI() {
    const q = current.q;
    const nc = $("#nextClue");
    if (nc) nc.onclick = () => { current.clue++; current.readOnce = false; renderQuestion(); };
    $("#sayIt").onclick = () => {
      current.done = true; current.mode = "self";
      current.revealText = "It's " + q.answer + "!";
      renderQuestion();
      autoSay(current.revealText);
    };
    $("#typeForm").onsubmit = (e) => {
      e.preventDefault();
      const g = $("#guess").value;
      if (!g.trim()) return;
      if (matches(g, q)) {
        finish(true, "Yes! It's " + q.answer + "!");
      } else {
        const hint = $("#hint");
        hint.textContent = current.clue < q.clues.length - 1 ? "Not yet. Try again or get another clue." : "Not yet. Try again!";
        $("#guess").select();
        autoSay("Not yet. Try again!");
      }
    };
  }

  function record(correct) {
    const { cat } = current;
    const b = (session.byCat[cat] = session.byCat[cat] || { answered: 0, correct: 0 });
    b.answered++; session.answered++;
    if (correct) { b.correct++; session.correct++; }
    save();
    const s = $("#scoreNum"); if (s) s.textContent = scoreText();
  }

  function finish(correct, revealText) {
    current.done = true; current.correct = correct; current.mode = current.mode || "auto";
    current.revealText = revealText;
    record(correct);
    renderQuestion();
    autoSay(revealText);
  }

  function answer(btn) {
    if (current.done) return;
    const { q, cat } = current;
    if (cat === "true-false") {
      const pick = btn.dataset.a === "true";
      current.pick = pick;
      const ok = pick === q.answer;
      finish(ok, (ok ? "Yes! " : "Not quite. ") + "It's " + (q.answer ? "true" : "false") + ". " + (q.explain || ""));
    } else if (cat === "pick-one") {
      const i = +btn.dataset.i; current.pick = i;
      const ok = norm(current.choices[i]) === norm(q.answer);
      finish(ok, (ok ? "Yes! " : "Not quite. The answer is " + bare(q.answer) + ". ") + (q.explain || ""));
    } else if (cat === "more-or-less") {
      const i = +btn.dataset.i; current.pick = i;
      const ok = norm(q.options[i]) === norm(q.answer);
      finish(ok, (ok ? "Yes! " : "Not quite. ") + "It's " + bare(q.answer).toLowerCase() + ". " + (q.explain || ""));
    } else if (cat === "this-or-that") {
      const i = +btn.dataset.i; current.pick = i;
      current.done = true; current.mode = "pick";
      session.picks.push({ id: q.id, prompt: q.prompt, pick: q.options[i], at: new Date().toISOString() });
      const b = (session.byCat[cat] = session.byCat[cat] || { answered: 0, correct: 0 });
      b.answered++;
      save();
      const josh = typeof q.joshPick === "number" && q.options[q.joshPick];
      current.revealText = "You picked " + q.options[i] + "! " + (josh ? (q.joshPick === i ? "Josh picked that one too!" : "Josh picked " + josh + ".") : "");
      renderQuestion();
      autoSay(current.revealText);
    }
  }

  function renderReveal() {
    const { q, cat } = current;
    const box = $("#revealBox");
    const from = `<div class="from">From: ${esc(q.episode)}${q.needsReview ? '<span class="tag">unchecked</span>' : ""}</div>`;
    const verdict = (ok) => `<div class="verdict ${ok ? "good" : "bad"}">${ok ? ICON.check + "Yes!" : ICON.x + "Not quite"}</div>`;
    const explain = q.explain ? `<div class="explain">${esc(q.explain)}</div>` : "";

    // Disable and color the answer buttons.
    if (cat === "this-or-that") {
      const josh = typeof q.joshPick === "number" ? q.joshPick : null;
      const opts = q.options.map((t, i) => `<button class="ans ${i === current.pick ? "picked" : "dim"}" disabled>${esc(cap(t))}</button>`).join("");
      box.innerHTML = `<div class="answers done ${q.options.length === 2 ? "two" : ""}" style="padding-top:0">${opts}</div>
        <div class="reveal"><div class="verdict good">${ICON.star}You picked ${esc(cap(q.options[current.pick]))}!</div>
        ${josh !== null ? `<div class="explain">${josh === current.pick ? "Josh picked that one too!" : "Josh picked " + esc(q.options[josh]) + "."}</div>` : ""}
        ${q.joshSays ? `<div class="explain">"${esc(q.joshSays)}"</div>` : ""}${from}</div>`;
      return;
    }
    if (cat === "what-am-i") {
      if (current.mode === "self" && current.correct === undefined) {
        box.innerHTML = `<div class="reveal"><div class="the-answer">${esc(cap(q.answer))}!</div>${explain}${from}</div>
          <div class="answers two" style="padding-top:12px">
            <button class="ans" id="gotIt">${ICON.check}Got it</button>
            <button class="ans" id="missedIt">${ICON.x}Missed it</button></div>`;
        $(".bottom").style.display = "none";
        $("#gotIt").onclick = () => { $(".bottom").style.display = ""; finish(true, "Nice!"); };
        $("#missedIt").onclick = () => { $(".bottom").style.display = ""; finish(false, "Next time!"); };
        return;
      }
      box.innerHTML = `<div class="reveal">${verdict(current.correct)}<div class="the-answer">${esc(cap(q.answer))}</div>${explain}${from}</div>`;
      return;
    }
    let buttons = "";
    if (cat === "true-false") {
      buttons = `<div class="answers done two" style="padding-top:0">${[true, false].map((v) => `<button class="ans ${v === q.answer ? "right" : v === current.pick ? "wrong" : "dim"}" disabled>${v ? ICON.check + "True" : ICON.x + "False"}</button>`).join("")}</div>`;
    } else {
      const opts = cat === "pick-one" ? current.choices : q.options;
      buttons = `<div class="answers done ${opts.length === 2 ? "two" : ""}" style="padding-top:0">${opts.map((t, i) => {
        const right = norm(t) === norm(q.answer);
        return `<button class="ans ${right ? "right" : i === current.pick ? "wrong" : "dim"}" disabled>${esc(cap(t))}</button>`;
      }).join("")}</div>`;
    }
    const ansText = cat === "true-false" ? (q.answer ? "It's true." : "It's false.") : esc(cap(bare(q.answer)));
    box.innerHTML = `${buttons}<div class="reveal">${verdict(current.correct)}<div class="the-answer">${ansText}</div>${explain}${from}</div>`;
  }

  // ---------- swipe ----------
  function bindSwipe(el) {
    let x0 = null, y0 = null;
    el.addEventListener("touchstart", (e) => {
      if (e.target.closest("input, form")) { x0 = null; return; }
      x0 = e.touches[0].clientX; y0 = e.touches[0].clientY;
    }, { passive: true });
    el.addEventListener("touchend", (e) => {
      if (x0 === null) return;
      const dx = e.changedTouches[0].clientX - x0, dy = e.changedTouches[0].clientY - y0;
      x0 = null;
      if (dx < -70 && Math.abs(dx) > Math.abs(dy) * 1.5 && !$("#scrim").classList.contains("open")) {
        if (current && current.cat === "what-am-i" && current.mode === "self" && current.correct === undefined) return; // finish self-marking first
        next(true);
      }
    }, { passive: true });
  }

  // ---------- sheets ----------
  const scrim = $("#scrim"), sheet = $("#sheet");
  function openSheet(html) { sheet.innerHTML = html; scrim.classList.add("open"); }
  function closeSheet() { scrim.classList.remove("open"); }
  scrim.addEventListener("click", (e) => { if (e.target === scrim) closeSheet(); });

  function summary(q) { return q.prompt || (q.clues || []).join(" / "); }

  function openFlags() {
    const q = current.q;
    const f = flags[q.id] ? flags[q.id].flags : [];
    openSheet(`<h2>Flag this question</h2>
      <div class="flag-opts">${FLAGS.map((o) => `<button class="flag-opt" data-f="${o.key}" aria-pressed="${f.includes(o.key)}"><span class="box">${ICON.check}</span>${o.label}</button>`).join("")}</div>
      <div class="sheet-row"><button class="sheet-btn primary" id="flagDone">Done</button></div>`);
    sheet.querySelectorAll(".flag-opt").forEach((b) => b.addEventListener("click", () => {
      const on = b.getAttribute("aria-pressed") !== "true";
      b.setAttribute("aria-pressed", String(on));
      const keys = [...sheet.querySelectorAll('.flag-opt[aria-pressed="true"]')].map((x) => x.dataset.f);
      if (keys.length) flags[q.id] = { id: q.id, category: current.cat, flags: keys, question: summary(q), answer: q.answer, episode: q.episode, at: new Date().toISOString() };
      else delete flags[q.id];
      save();
      $("#flagBtn").classList.toggle("has", keys.length > 0);
    }));
    $("#flagDone").onclick = closeSheet;
  }

  function openStats() {
    const rows = CATS.map((c) => {
      const b = session.byCat[c.key] || { answered: 0, correct: 0 };
      const right = c.key === "this-or-that" ? "picks" : b.correct + " right";
      return `<tr><td><span class="dot" style="background:${c.color}"></span>${esc(c.name)}</td><td>${b.answered}</td><td>${right}</td></tr>`;
    }).join("");
    const picks = session.picks.slice(-8).reverse();
    const flagCount = Object.keys(flags).length;
    const counts = CATS.map((c) => `${esc(c.short)} ${(data[c.key] || []).length}`).join(", ");
    openSheet(`<h2>This session</h2>
      <p><strong style="color:var(--ink);font-size:22px">${session.correct} right out of ${session.answered}</strong></p>
      <table class="stat-table"><tbody>${rows}</tbody></table>
      ${picks.length ? `<h3>Recent This or That picks</h3><ul class="picks">${picks.map((p) => `<li>${esc(p.pick)}</li>`).join("")}</ul>` : ""}
      <div class="sheet-row"><button class="sheet-btn" id="resetBtn">New session</button></div>
      <h3>Settings</h3>
      <label class="toggle">Read questions out loud<input type="checkbox" id="autoRead" ${settings.autoRead ? "checked" : ""}></label>
      <label class="toggle">Skip unchecked questions<input type="checkbox" id="skipUnchecked" ${settings.skipUnchecked ? "checked" : ""}></label>
      <h3>Flags</h3>
      <p>${flagCount} question${flagCount === 1 ? "" : "s"} flagged.</p>
      <div class="sheet-row"><button class="sheet-btn primary" id="exportBtn" ${flagCount ? "" : "disabled"}>Export flags</button><button class="sheet-btn" id="clearFlags" ${flagCount ? "" : "disabled"}>Clear flags</button></div>
      <p style="font-size:14px;margin-top:18px">Questions: ${counts}.</p>
      <div class="sheet-row"><button class="sheet-btn" id="closeStats">Close</button></div>`);
    $("#autoRead").onchange = (e) => { settings.autoRead = e.target.checked; save(); if (!settings.autoRead && "speechSynthesis" in window) speechSynthesis.cancel(); };
    $("#skipUnchecked").onchange = (e) => { settings.skipUnchecked = e.target.checked; save(); };
    $("#resetBtn").onclick = () => { session = freshSession(); save(); $("#scoreNum").textContent = scoreText(); openStats(); };
    $("#exportBtn").onclick = exportFlags;
    $("#clearFlags").onclick = () => { if (confirm("Clear all flags? Export them first if you need them.")) { flags = {}; save(); openStats(); const fb = $("#flagBtn"); if (fb) fb.classList.remove("has"); } };
    $("#closeStats").onclick = closeSheet;
  }

  function exportFlags() {
    const list = Object.values(flags).sort((a, b) => a.at.localeCompare(b.at));
    const out = { exported: new Date().toISOString(), count: list.length, flags: list, session };
    const blob = new Blob([JSON.stringify(out, null, 2)], { type: "application/json" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = "curious-kids-flags-" + new Date().toISOString().slice(0, 10) + ".json";
    document.body.appendChild(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(a.href), 2000);
  }

  // ---------- boot ----------
  load().then(() => {
    const total = CATS.reduce((n, c) => n + (data[c.key] || []).length, 0);
    $("#loadNote").textContent = total ? total.toLocaleString() + " questions from Curious Kids Every Day." : "Could not load questions.";
    const btn = $("#startBtn");
    btn.disabled = !total;
    btn.onclick = () => {
      // The tap unlocks speech on iOS before the first auto-read.
      if ("speechSynthesis" in window) { const u = new SpeechSynthesisUtterance(""); speechSynthesis.speak(u); }
      renderShell();
      next(false);
    };
  });
})();
