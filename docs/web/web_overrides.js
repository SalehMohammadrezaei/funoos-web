/* Funoos on the web: the changes the desktop interface (web/app.js, loaded before this file and
   unchanged) needs for a pre-run library. app.js keeps its state in global bindings and calls its
   functions by name, so each change below replaces or wraps one of them:

   - Studio controls offer the pre-run values of each parameter. Every value of the experiment can
     be picked; when that value was run with different settings of the other controls, those move
     to the nearest pre-run combination, and the result loads at once.
   - A scene opens on its pre-run preset (the library's resolution, duration 1.8) and plays it.
   - Comparison shows the two clips side by side (each with its own colour scale), the parameter
     sweep runs over the pre-run values, exports that need raw fields point to the desktop app.
   - The address bar follows the page (#gallery, #e/<scene>, #c/<case>), so links can be shared.

   Finally the bridge is published (window.pywebview) and the app boots. */
"use strict";
(function () {
  const W = window.FunoosWeb;
  let CASES = [];                                    // the case index (data/cases.json)
  const same = W.same;
  const num = v => typeof v === "number";

  // ---- the cases the Studio can show: same experiment and exhibit as the scene on screen
  function studioCases() {
    const exp = S2E[CUR_SCENE];
    return CASES.filter(c => c.exhibit === CUR_EXH && (!exp || c.experiment === exp));
  }
  function caseOf(state) { return studioCases().find(c => Object.keys(c.params).every(k => !(k in state) || same(c.params[k], state[k]))) || null; }
  function sceneCase() { return CASES.find(c => c.preset && c.scene === CUR_SCENE) || null; }
  function valuesOf(name, list) {
    const vals = [];
    for (const c of list) { const v = c.params[name]; if (v !== undefined && !vals.some(x => same(x, v))) vals.push(v); }
    const q = SPEC && SPEC.find(x => x.name === name);
    if (q && q.type === "choice") vals.sort((a, b) => q.choices.indexOf(a) - q.choices.indexOf(b));
    else if (vals.every(num)) vals.sort((a, b) => a - b);
    return vals;
  }
  function labelOf(name) { const q = SPEC.find(x => x.name === name); return q ? (q.label || name) : name; }

  // the nearest pre-run case with name = value: fewest other controls changed, then smallest change
  function pick(name, value) {
    let best = null, score = Infinity;
    for (const c of studioCases()) {
      if (!same(c.params[name], value)) continue;
      let n = 0, d = 0;
      for (const k in c.params) {
        if (k === name || !(k in PSTATE) || same(c.params[k], PSTATE[k])) continue;
        n++; d += num(c.params[k]) && num(PSTATE[k]) ? Math.abs(Math.log((Math.abs(c.params[k]) + 1e-12) / (Math.abs(PSTATE[k]) + 1e-12))) : 1;
      }
      if (n * 1000 + d < score) { score = n * 1000 + d; best = c; }
    }
    if (!best) return;
    const moved = Object.keys(best.params).filter(k => k !== name && k in PSTATE && !same(best.params[k], PSTATE[k]) && SPEC.some(q => q.name === k && visible(q)));
    pushUndo(); PSTATE = { ...PSTATE, ...best.params };
    renderParams(); refreshEstimate();
    if (moved.length) toast("Pre-run combination: " + moved.map(k => labelOf(k) + " → " + fmtNum(best.params[k])).join(", "), "");
    runSim();
  }

  // ---- controls: a list of the pre-run values; a control with one value shows it, fixed
  let VARY = new Set();
  renderParams = function () {
    const list = studioCases();
    VARY = new Set(SPEC.filter(q => valuesOf(q.name, list).length > 1).map(q => q.name));
    const root = $("#s-params"); root.innerHTML = ""; const groups = {};
    for (const q of SPEC) { if (!visible(q) || (q.advanced && !ADV && !VARY.has(q.name))) continue; (groups[q.group] || (groups[q.group] = [])).push(q); }
    for (const g of ["Geometry", "Physics", "Render"]) {
      if (!groups[g]) continue;
      const blk = el("div", "pgroup"), head = elt("div", "kicker", g);
      if (groups[g].some(q => VARY.has(q.name))) {
        const rst = elt("button", "linkbtn", "reset"); rst.type = "button"; rst.title = "Reset this group to the preset values";
        rst.setAttribute("aria-label", "Reset " + g + " parameters"); rst.onclick = () => resetGroup(g); head.append(rst);
      }
      blk.append(head);
      for (const q of groups[g]) blk.append(field(q)); root.append(blk);
    }
    const advb = $("#s-adv");
    if (advb) { advb.textContent = ADV ? "Fewer controls" : "All controls"; advb.title = ADV ? "Show only the controls that have pre-run values" : "Also show the advanced controls, fixed at their pre-run values"; advb.setAttribute("aria-pressed", ADV ? "true" : "false"); }
    validateAll();
  };
  field = function (q) {
    const f = el("div", "field" + (VARY.has(q.name) ? "" : " webfixed")); f.dataset.name = q.name;
    const id = "p-" + q.name, vals = valuesOf(q.name, studioCases());
    const lab = elt("label", null, q.label || q.name); lab.htmlFor = id;
    if (q.units) lab.append(" ", elt("span", "units", "(" + q.units + ")"));
    lab.append(elt("span", "rng", vals.length > 1 ? "  " + vals.length + " pre-run values" : "  fixed"));
    f.append(lab);
    const sel = el("select"); sel.id = id;
    const cur = PSTATE[q.name];
    if (!vals.some(v => same(v, cur))) vals.push(cur);
    for (const v of vals) { const o = elt("option", null, String(fmtNum(v))); o.value = JSON.stringify(v); if (same(v, cur)) o.selected = true; sel.append(o); }
    if (vals.length < 2) sel.disabled = true;
    sel.onchange = () => pick(q.name, JSON.parse(sel.value));
    f.append(sel, helpFor(q, id, f)); sel.setAttribute("aria-describedby", id + "-help");
    f.append(elt("div", "verr", ""));
    return f;
  };
  // resolution and duration of the library, not the scene defaults
  const _sceneDefaults = sceneDefaults;
  sceneDefaults = function () { const c = sceneCase(); return c ? { ..._sceneDefaults(), ...c.params } : _sceneDefaults(); };
  const _openStudio = openStudio;
  openStudio = function (d) {
    _openStudio(d);
    if (!caseOf(PSTATE)) { const c = sceneCase(); if (c) PSTATE = { ...PSTATE, ...c.params }; }
    renderParams(); refreshEstimate(); runSim();
  };
  // results load at once: a change made while one loads is applied right after it
  const _runSim = runSim; let again = false;
  runSim = async function () {
    if (JOB) { again = true; return; }
    await _runSim();
    if (again) { again = false; await runSim(); }
  };
  // every change of the setup shows its result: undo, redo, reset, a saved setup
  for (const name of ["undoParams", "redoParams", "resetGroup", "resetAll", "presetAction"]) {
    const orig = window[name];
    window[name] = function (...args) { const before = JSON.stringify(PSTATE); const r = orig.apply(this, args); if (JSON.stringify(PSTATE) !== before && caseOf(PSTATE)) runSim(); return r; };
  }
  const _refreshJobUI = refreshJobUI;
  refreshJobUI = function () { _refreshJobUI(); const b = $("#s-run"); if (b && !JOB) b.textContent = "▶  Play the pre-run result"; };
  let _estT = null;
  refreshEstimate = function () {
    clearTimeout(_estT);
    _estT = setTimeout(async () => {
      const e_ = $("#s-estimate"), c = CUR_EXH && caseOf(PSTATE);
      if (!c) { if (e_) e_.textContent = ""; renderDerived([]); return; }
      const d = await W.detail(c.id);
      const s = d.solve_s, t = s == null ? "" : s < 90 ? Math.round(s) + " s" : s < 5400 ? Math.round(s / 60) + " min" : (s / 3600).toFixed(1) + " h";
      if (e_) e_.textContent = `pre-run · ${d.grid} grid · ${d.meta.frames} frames` + (t ? ` · solved in ${t} on ${d.threads} threads` : "");
      renderDerived(d.derived || []);
    }, 40);
  };
  // the library's clips are encoded at 24 frames per second (the app's own at 26)
  const _setVideo = setVideo;
  // The clips have no sound track. A browser starts a video by itself (a link straight into the
  // Studio, before any click) only when it is muted; the desktop app's window has no such rule.
  setVideo = function (src, keep) { FPS = 24; document.getElementById("s-video").muted = true; return _setVideo(src, keep); };
  const QUIET = [/^Done — open/];
  const _toast = toast;
  toast = function (msg, kind) { if (QUIET.some(r => r.test(msg))) return; return _toast(msg, kind); };

  // ---- comparison: the two clips side by side, played together
  let CMPV = null;
  compareWith = async function (rid, again_) {
    if (!RUN) { toast("Open a result first", "err"); return; }
    if (rid === RUN.run_id && !again_) { toast("Pick a different run to compare with", "err"); return; }
    const t = nextReq("cmp"), cur = RUN.run_id;
    try {
      const a = await call("run_info", rid), va = await call("render_view", rid, RUN.view, null, 24, t);
      if (!isCurrent("cmp", t) || !RUN || RUN.run_id !== cur) return;
      leaveCompare();
      const sc = $("#s-screen"), v = $("#s-video");
      CMPV = el("video"); CMPV.id = "w-cmpa"; CMPV.muted = CMPV.loop = true; CMPV.playsInline = true; CMPV.src = va.video;
      sc.insertBefore(CMPV, v); sc.classList.add("webcmp");
      const la = elt("div", "wtag left", "A · " + a.info), lb = elt("div", "wtag right", "B · " + RUN.info);
      la.id = "w-taga"; lb.id = "w-tagb"; sc.append(la, lb);
      const sync = () => { if (!CMPV) return; if (Math.abs(CMPV.currentTime - v.currentTime) > 0.08) CMPV.currentTime = v.currentTime; CMPV.playbackRate = v.playbackRate; if (v.paused) CMPV.pause(); else CMPV.play().catch(() => {}); };
      for (const ev of ["play", "pause", "seeked", "ratechange"]) v.addEventListener(ev, sync);
      v.addEventListener("timeupdate", sync); CMPV.addEventListener("loadeddata", sync, { once: true });
      CMP = { a: rid, b: cur, view: va.view, times: RUN.meta && RUN.meta.times, unit: RUN.meta && RUN.meta.time_unit, label_a: a.info, label_b: RUN.info, cmap: va.cmap, sync };
      $("#s-status").textContent = `⇄ comparison · left: ${a.info} · right: ${RUN.info}`;
      const ci = $("#s-cmpinfo"); if (ci) { ci.style.display = "block"; ci.textContent = `Left: ${a.info}. Right: ${RUN.info}. View ${va.view}; each clip keeps its own colour scale. Switch a view or open another result to leave the comparison.`; }
      setTab("field");
    } catch (e) { if (isCurrent("cmp", t)) toast(errText(e), "err"); }
  };
  const _leaveCompare = leaveCompare;
  leaveCompare = function () {
    if (CMP && CMP.sync) { const v = $("#s-video"); for (const ev of ["play", "pause", "seeked", "ratechange", "timeupdate"]) v.removeEventListener(ev, CMP.sync); }
    if (CMPV) { CMPV.pause(); CMPV.remove(); CMPV = null; }
    for (const id of ["#w-taga", "#w-tagb"]) { const x = $(id); if (x) x.remove(); }
    const sc = $("#s-screen"); if (sc) sc.classList.remove("webcmp");
    _leaveCompare();
  };

  // ---- parameter sweep over the pre-run values
  openSweep = function () {
    const box = $("#s-sweep"); if (!box) return;
    if (box.style.display === "block") { box.style.display = "none"; return; }
    const sel = $("#s-sweep-param"); sel.innerHTML = "";
    const list = studioCases(), opts = {};
    for (const q of SPEC) {
      if (!visible(q) || (q.type !== "float" && q.type !== "int")) continue;
      const others = list.filter(c => Object.keys(c.params).every(k => k === q.name || !(k in PSTATE) || same(c.params[k], PSTATE[k])));
      const vals = valuesOf(q.name, others); if (vals.length > 1) opts[q.name] = vals;
    }
    for (const n of Object.keys(opts)) { const o = elt("option", null, labelOf(n)); o.value = n; sel.append(o); }
    const inp = $("#s-sweep-values"); inp.readOnly = true;
    sel.onchange = () => { inp.value = (opts[sel.value] || []).map(v => fmtNum(v)).join(", "); };
    if (!sel.options.length) { const o = elt("option", null, "no pre-run sweep from this setup"); o.value = ""; sel.append(o); }
    sel.onchange(); box.style.display = "block"; sel.focus();
  };
  const _runSweep = runSweep;
  runSweep = async function () {
    const name = $("#s-sweep-param").value; if (!name) return;
    const inp = $("#s-sweep-values"), shown = inp.value.split(/,\s*/);
    // the read-only field shows rounded numbers; the sweep gets the exact pre-run values
    inp.value = valuesOf(name, studioCases()).filter(v => shown.includes(String(fmtNum(v)))).join(", ");
    return _runSweep();
  };

  // ---- exports: the clip and the plots exist; everything built from raw fields needs the app
  exportAction = async function (sel) {
    const what = typeof sel === "string" ? sel : sel.value; if (typeof sel !== "string") sel.value = "";
    if (!RUN) { toast("Open a result first", "err"); return; }
    if (what === "mp4") { const r = await call("render_view", RUN.run_id, RUN.view); window.open(r.video, "_blank", "noopener"); toast("The MP4 clip downloads from the release", "ok"); return; }
    if (what === "svg") {
      const d = await call("diagnostics", RUN.run_id);
      for (const p of d.plots) { const a = el("a"); a.href = p.img; a.download = p.img.split("/").pop(); document.body.append(a); a.click(); a.remove(); }
      toast(d.plots.length + " plot" + (d.plots.length === 1 ? "" : "s") + " saved", "ok"); return;
    }
    if (what === "options") { const b = $("#x-opts"); b.style.display = b.style.display === "block" ? "none" : "block"; return; }
    toast(W.DESKTOP, "err");
  };
  openUrl = async function (u) { if (/^https?:\/\//.test(u)) window.open(u, "_blank", "noopener"); };
  saveProject = async function () { toast(W.DESKTOP, "err"); };
  loadProject = async function () { toast(W.DESKTOP, "err"); };
  toggleProbe = function () { toast("Probes read the raw fields: they work in the desktop app.", "err"); };

  // ---- counts, texts
  const _fillCounts = fillCounts;
  fillCounts = function (c) {
    _fillCounts(c);
    const sub = $("#gal-sub"); if (sub && c.cases) sub.textContent = `${c.experiments} experiments with ${c.presets} presets across ${c.methods} numerical methods · ${c.cases} pre-run cases.`;
  };

  // ---- the address bar follows the page: #gallery, #about, #studio, #e/<scene>, #c/<case>
  let ROUTING = false, LAST_DETAIL = null;
  function setHash(h) { if (ROUTING) return; const want = h ? "#" + h : location.pathname + location.search; if (location.hash !== (h ? "#" + h : "")) history.pushState(null, "", want); }
  const _show = show;
  show = function (v) {
    _show(v);
    if (v === "intro") setHash(""); else if (v === "gallery" || v === "about") setHash(v);
    else if (v === "detail" && LAST_DETAIL) setHash("e/" + LAST_DETAIL);
    else if (v === "studio") setHash("studio");        // a result replaces it with #c/<case>, so Back returns to the page before
  };
  const _openDetail = openDetail;
  openDetail = async function (key) { LAST_DETAIL = key; return _openDetail(key); };
  const _renderKPIs = renderKPIs;
  renderKPIs = function (s) {
    _renderKPIs(s);
    if (CUR === "studio" && RUN && !ROUTING) { const c = caseOf(RUN.params || {}); if (c) history.replaceState(null, "", "#c/" + c.id); }
  };
  async function route() {
    const h = decodeURIComponent(location.hash.slice(1)); ROUTING = true;
    try {
      if (!h) _show("intro");
      else if (h === "gallery" || h === "about") _show(h);
      else if (h === "studio") _show("studio");
      else if (h.startsWith("e/")) await openDetail(h.slice(2));
      else if (h.startsWith("c/")) {
        const c = CASES.find(x => x.id === h.slice(2));
        if (c) {
          const d = await call("scene_detail", c.scene, nextReq("detail"));
          _openStudio(d); PSTATE = { ...PSTATE, ...c.params }; renderParams(); refreshEstimate(); await runSim();
        } else _show("gallery");
      }
    } catch (e) { _show("gallery"); }
    ROUTING = false;
  }
  window.addEventListener("popstate", route);

  // ---- boot: the case index first, then the app with this bridge
  $("#s-hint").innerHTML = "Pick an experiment on the left: its pre-run result plays here.<br>Switch views, tabs and pre-run values while it plays.";
  W.cases().then(list => {
    CASES = list;
    window.pywebview = { api: W.api };
    buildGallery().then(fillStudioPicker).then(() => { if (location.hash) route(); });
    initStage(); if (!location.hash) _show("intro");
  }).catch(e => {
    document.body.insertAdjacentHTML("beforeend", '<div class="webfail">The pre-run library could not be loaded (' + String(e.message || e) + '). Reload the page to try again.</div>');
  });
})();
