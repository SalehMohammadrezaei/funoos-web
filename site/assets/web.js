/* Funoos web version: page behaviour. No framework; one JSON manifest per experiment. */
"use strict";
const $ = s => document.querySelector(s);
const el = (t, c, txt) => { const e = document.createElement(t); if (c) e.className = c; if (txt != null) e.textContent = txt; return e; };
const REDUCED = matchMedia("(prefers-reduced-motion: reduce)").matches;
const ACC = { "Lattice–Boltzmann": "#5b86f0", "Incompressible Navier–Stokes": "#e0a23a", "Compressible Euler": "#e35d6a",
  "Smoothed-Particle Hydrodynamics": "#56c5e8", "Pseudo-spectral": "#9b8cff", "Reaction–Diffusion": "#9be25a" };
const SHORT = { "Incompressible Navier–Stokes": "Navier–Stokes", "Smoothed-Particle Hydrodynamics": "SPH" };
const STATUS_SHORT = { analytical: "Analytical", numerical: "Numerical", qualitative: "Qualitative" };

/* theme: the app is dark; a stored choice wins, then the system setting */
function applyTheme(t) { if (t === "light") document.documentElement.setAttribute("data-theme", "light"); else document.documentElement.removeAttribute("data-theme"); try { localStorage.setItem("funoos.web.theme", t); } catch (e) {} const b = $("#themebtn"); if (b) { b.textContent = t === "light" ? "☾" : "☀"; b.setAttribute("aria-label", t === "light" ? "Switch to the dark theme" : "Switch to the light theme"); } }
function initTheme() { let t = null; try { t = localStorage.getItem("funoos.web.theme"); } catch (e) {} if (!t) t = matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark"; applyTheme(t); const b = $("#themebtn"); if (b) b.onclick = () => applyTheme(document.documentElement.getAttribute("data-theme") === "light" ? "dark" : "light"); }

function fmt(v) {
  if (v == null || Number.isNaN(v)) return "n/a";
  if (typeof v !== "number") return String(v);
  const a = Math.abs(v);
  if (a === 0) return "0";
  if (a >= 1e5 || a < 1e-3) return v.toExponential(2);
  if (a >= 100) return v.toFixed(1);
  if (a >= 10) return v.toFixed(2);
  return v.toPrecision(3);
}
function videoUrl(caseId, slug) { return (window.FUNOOS_MEDIA_BASE || (D && D.video_base) || "media/video/") + caseId + "__" + slug + ".mp4"; }

/* ───────── home: gallery filter and hover clips ───────── */
function initHome() {
  const cards = [...document.querySelectorAll(".gcard")], chips = [...document.querySelectorAll(".phenchips .chipbtn")], q = $("#g-search");
  const groups = [...document.querySelectorAll(".ghead[data-group]")];
  let phen = "";
  function apply() {
    const s = (q ? q.value : "").trim().toLowerCase(); let n = 0; const shownGroups = new Set();
    for (const c of cards) {
      const ok = (!phen || c.dataset.phen === phen) && (!s || c.dataset.hay.includes(s));
      c.hidden = !ok; if (ok) { n++; shownGroups.add(c.dataset.phen); }
    }
    for (const g of groups) g.hidden = !shownGroups.has(g.dataset.group);
    const start = $("#gallery-start"); if (start) start.hidden = !!(s || phen);
    const none = $("#g-none"); if (none) none.hidden = n > 0;
  }
  for (const b of chips) b.onclick = () => { phen = b.dataset.value || ""; chips.forEach(x => x.setAttribute("aria-pressed", String(x === b))); apply(); };
  if (q) q.oninput = apply;
  // hover or focus plays the clip; at most a few at once
  if (!REDUCED) for (const c of cards) {
    const v = c.querySelector("video"); if (!v) continue;
    const on = () => { if (!v.getAttribute("src")) v.src = v.dataset.src; v.play().catch(() => {}); v.classList.add("ready"); };
    const off = () => { v.pause(); v.classList.remove("ready"); };
    c.addEventListener("mouseenter", on); c.addEventListener("mouseleave", off); c.addEventListener("focus", on); c.addEventListener("blur", off);
  }
  // counters
  document.querySelectorAll(".stat .n").forEach(n => { const target = +n.dataset.count; if (REDUCED) { n.textContent = target; return; } const t0 = performance.now(); const tick = now => { const p = Math.min(1, (now - t0) / 1100); n.textContent = Math.round(target * (1 - Math.pow(1 - p, 3))); if (p < 1) requestAnimationFrame(tick); }; requestAnimationFrame(tick); });
  document.querySelectorAll(".reveal").forEach((e, i) => setTimeout(() => e.classList.add("in"), REDUCED ? 0 : 80 + i * 90));
}

/* ───────── experiment page ───────── */
let D = null, CUR = null, CMP = null, VIEW = null, RATE = 1;
function caseById(id) { return D.cases.find(c => c.id === id); }

function initExperiment() {
  const root = $("#exp"); if (!root) return;
  fetch(root.dataset.manifest).then(r => r.json()).then(d => { D = d; buildControls(); const start = location.hash.slice(1); selectCase(caseById(start) ? start : D.representative, true); initTransport(); initTabs(); })
    .catch(e => { $("#s-status").textContent = "The case data could not be loaded (" + e + ")."; });
}

function sweepOf(c) { return D.sweeps.find(s => s.name === c.sweep); }
function buildControls() {
  const box = $("#ctrl"); box.innerHTML = "";
  const f = el("div", "field"); const lab = el("label", null, "Explore"); lab.htmlFor = "c-sweep"; f.append(lab);
  const sel = el("select"); sel.id = "c-sweep";
  for (const s of D.sweeps) { const o = el("option", null, s.name); o.value = s.name; sel.append(o); }
  sel.onchange = () => { const s = D.sweeps.find(x => x.name === sel.value); selectCase(s.cases[0].id); };
  f.append(sel); box.append(f);
  const pbox = el("div", "ctrlgrid"); pbox.id = "c-params"; box.append(pbox);
}
function buildParamSelects(c) {
  const s = sweepOf(c), pbox = $("#c-params"); pbox.innerHTML = ""; $("#c-sweep").value = s.name;
  if (!s.params.length) {                                     // presets: one dropdown with the labels
    const f = el("div", "field"); const lab = el("label", null, "Preset"); lab.htmlFor = "c-preset"; f.append(lab);
    const sel = el("select"); sel.id = "c-preset";
    for (const k of s.cases) { const o = el("option", null, k.label); o.value = k.id; if (k.id === c.id) o.selected = true; sel.append(o); }
    sel.onchange = () => selectCase(sel.value); f.append(sel); pbox.append(f); return;
  }
  for (const p of s.params) {
    const spec = D.param_spec[p] || { label: p };
    const f = el("div", "field"); const lab = el("label", null, spec.label || p); lab.htmlFor = "c-" + p;
    if (spec.units) lab.append(el("span", "units", spec.units)); f.append(lab);
    const sel = el("select"); sel.id = "c-" + p;
    const vals = [...new Set(s.cases.map(k => JSON.stringify(k.values[p])))].map(x => JSON.parse(x));
    for (const v of vals) { const o = el("option", null, String(v)); o.value = JSON.stringify(v); if (JSON.stringify(c.values[p]) === o.value) o.selected = true; sel.append(o); }
    sel.onchange = () => {
      const want = {}; for (const q of s.params) want[q] = JSON.parse($("#c-" + q).value);
      let hit = s.cases.find(k => s.params.every(q => JSON.stringify(k.values[q]) === JSON.stringify(want[q])));
      if (!hit) hit = s.cases.find(k => JSON.stringify(k.values[p]) === JSON.stringify(want[p]));   // grid hole: nearest on this axis
      selectCase(hit.id);
    };
    f.append(sel); if (spec.help) { const h = el("div", "help small muted", spec.help); f.append(h); } pbox.append(f);
  }
}

function selectCase(id, first) {
  const c = caseById(id); if (!c) return; CUR = c;
  buildParamSelects(c);
  const held = $("#c-held"); held.innerHTML = ""; const s = sweepOf(c);
  if (s.params.length && c.fixed_text) held.append(el("span", null, "Held fixed: " + c.fixed_text));
  $("#c-case").innerHTML = ""; $("#c-case").append(el("span", null, "Showing: "), el("b", null, c.label));
  if (!first) history.replaceState(null, "", "#" + c.id);
  if (!VIEW || !c.views.some(v => v.view === VIEW)) VIEW = c.views[0].view;
  buildViews(c); loadVideo(c, $("#s-video"), $("#s-poster")); fillReadouts(c); fillQuality(c); fillDerived(c); fillParams(c); fillPlots(c); fillLayers(c);
  if (CMP) updateCompare();
}
function buildViews(c) {
  const box = $("#s-views"); box.innerHTML = "";
  for (const v of c.views) { const b = el("button", v.view === VIEW ? "on" : "", v.view); b.type = "button"; b.onclick = () => { VIEW = v.view; buildViews(CUR); loadVideo(CUR, $("#s-video"), $("#s-poster")); if (CMP) updateCompare(); }; box.append(b); }
}
function viewRec(c) { return c.views.find(v => v.view === VIEW) || c.views[0]; }
function loadVideo(c, vid, posterImg) {
  const v = viewRec(c); const t = vid.currentTime || 0, paused = vid.paused && !vid.autoplay;
  vid.poster = D.poster_base + c.id + "__" + v.slug + ".webp"; vid.src = videoUrl(c.id, v.slug);
  const scr = vid.closest(".screen") || vid.parentElement; if (scr) scr.style.setProperty("--ar", v.width + "/" + v.height);
  vid.playbackRate = RATE;
  vid.addEventListener("loadedmetadata", () => { if (t) vid.currentTime = Math.min(t, vid.duration || t); }, { once: true });
  if (!REDUCED && !paused) vid.play().catch(() => {});
  const cap = $("#s-caption"); if (cap) cap.textContent = v.view + " · " + v.frames + " frames · " + v.seconds + " s clip · " + v.width + "×" + v.height;
}
function fillReadouts(c) {
  const box = $("#s-kpis"); box.innerHTML = "";
  const m = c.metrics || {}; let n = 0;
  for (const [key, label, unit, scale] of D.readouts) {
    if (!(key in m) || m[key] == null) continue;
    const k = el("div", "kpi" + (n === 0 ? " accent" : "")); k.append(el("div", "l", label)); const v = el("div", "v", fmt(m[key] * scale)); if (unit) v.append(el("small", null, " " + unit)); k.append(v); box.append(k); n++;
  }
  for (const key in m) { if (D.readouts.some(r => r[0] === key)) continue; const k = el("div", "kpi"); k.append(el("div", "l", key.replace(/_/g, " "))); k.append(el("div", "v", fmt(m[key]))); box.append(k); n++; }
  if (!n) box.append(el("div", "muted rhint", "No scalar measurement is defined for this experiment; see the plots."));
}
function fillQuality(c) {
  const q = $("#s-quality"); q.innerHTML = "";
  const lvl = c.quality.level; const badge = el("span", "statusbadge status-" + (lvl === "quantitative" ? "numerical" : "qualitative"), lvl === "quantitative" ? "Quantitative run" : (lvl === "qualitative" ? "Read qualitatively" : "Incomplete run"));
  q.append(badge, el("span", null, lvl === "quantitative" ? "The solver's own checks found nothing that limits a quantitative reading of this run." : "The solver reported:"));
  if (c.quality.notes.length) { const ul = el("ul"); for (const n of c.quality.notes) ul.append(el("li", null, n)); q.append(ul); }
  const st = $("#d-status"); if (st) { st.textContent = c.status_label; st.className = "statusbadge status-" + c.status; }
}
function fillDerived(c) {
  const box = $("#s-derived"); box.innerHTML = "";
  for (const d of c.derived || []) { const r = el("div", "drow"); r.append(el("span", "dl", d.label), el("span", "dv", d.value + (d.units ? " " + d.units : ""))); if (d.note) r.append(el("span", "dn", d.note)); box.append(r); }
  if (!(c.derived || []).length) box.append(el("div", "muted small", "No derived quantities for this experiment."));
}
function fillParams(c) {
  const t = $("#s-params"); t.innerHTML = "";
  for (const [k, v] of Object.entries(c.params)) { const spec = D.param_spec[k] || {}; const tr = el("tr"); tr.append(el("td", null, (spec.label || k) + (spec.units ? " (" + spec.units + ")" : "")), el("td", null, String(v))); t.append(tr); }
  const r = c.result || {}; const tr = el("tr"); tr.append(el("td", null, "grid / frames"), el("td", null, (r.shape ? r.shape.slice().reverse().join(" × ") : "") + " / " + r.frames)); t.append(tr);
}
function fillPlots(c) {
  const box = $("#s-plots"); box.innerHTML = "";
  for (const p of c.plots) { const d = el("div", "plot"); d.append(el("div", "ptitle", p.title)); const w = el("div", "svgwrap"); const img = el("img"); img.src = D.plot_base + c.id + "/" + p.file; img.alt = p.title; img.loading = "lazy"; w.append(img); d.append(w); d.append(el("div", "explain", p.explain)); box.append(d); }
  if (!c.plots.length) box.append(el("div", "muted", "No diagnostic plot for this case."));
}
function fillLayers(c) {
  const box = $("#s-layers"); box.innerHTML = "";
  const L = D.scenes[c.scene]; if (!L) return;
  for (const lay of L.layers) {
    const sec = el("details", "layer"); sec.open = ["question", "see", "try", "observe", "numerics"].includes(lay.id);
    const sum = el("summary"); sum.append(el("span", "kicker", lay.title)); if (lay.id === "numerics" && lay.status) sum.append(el("span", "statusbadge status-" + L.status, lay.status)); sec.append(sum);
    if (lay.text) sec.append(el("div", "read body" + (lay.id === "model" ? " terms" : ""), lay.text));
    if (lay.items && lay.items.length) { const ul = el("ul", "tries"); for (const it of lay.items) ul.append(typeof it === "string" ? el("li", null, it) : refItem(it)); sec.append(ul); }
    if (lay.id === "observe") {
      if (lay.fixed && lay.fixed.length) { sec.append(el("div", "kicker small", "held fixed")); const ul = el("ul", "tries"); for (const f of lay.fixed) ul.append(el("li", null, f)); sec.append(ul); }
      if (lay.more && lay.more.length) { sec.append(el("div", "kicker small", "further experiments (in the app)")); const ul = el("ul", "tries"); for (const it of lay.more) ul.append(el("li", null, it)); sec.append(ul); }
    }
    if (lay.id === "model" && lay.eq) { const b = el("div", "eqbox"); sec.insertBefore(b, sec.children[1] || null); renderEq(b, lay.eq); sec.append(el("div", "muted small", "The symbols are read out term by term above; units and conventions are in the numerical-method layer.")); }
    if (lay.id === "setup") {
      const s = el("div", "setup"); if (lay.ic) s.append(sline("Initial", lay.ic)); if (lay.bc) s.append(sline("Boundary", lay.bc));
      const ov = Object.entries(c.overrides || {}); const pre = Object.entries(lay.preset || {}).map(([k, v]) => k + " = " + v).join(", ") || "exhibit defaults";
      s.append(sline("Preset", pre)); if (ov.length) s.append(sline("This case", ov.map(([k, v]) => k + " = " + v).join(", "))); sec.append(s);
    }
    if (lay.id === "numerics" && lay.checks) { sec.append(el("div", "kicker small", "checks and limitations")); sec.append(el("div", "read body", lay.checks)); }
    box.append(sec);
  }
}
function refItem(r) { const li = el("li"); if (typeof r === "object") { li.textContent = r.text || r.title || JSON.stringify(r); if (r.url) { li.append(" "); const a = el("a", null, "link"); a.href = r.url; a.target = "_blank"; a.rel = "noopener"; li.append(a); } } else li.textContent = String(r); return li; }
function sline(k, v) { const r = el("div", "sline"); r.append(el("b", null, k), el("span", null, v)); return r; }
function renderEq(box, eq) {
  const tex = eq.replace(/^\$+|\$+$/g, "");
  const tryRender = () => { if (window.katex) { try { katex.render(tex, box, { displayMode: true, throwOnError: false }); return true; } catch (e) {} } return false; };
  if (!tryRender()) { box.textContent = tex; window.addEventListener("katex-ready", () => tryRender(), { once: true }); }
}

/* transport */
function initTransport() {
  const v = $("#s-video"), play = $("#s-play"), scrub = $("#s-scrub"), time = $("#s-time"), rate = $("#s-rate");
  const mmss = t => { const s = Math.max(0, t || 0); return (s < 60 ? "0:" : "") + (s < 60 ? String(Math.floor(s)).padStart(2, "0") : Math.floor(s / 60) + ":" + String(Math.floor(s % 60)).padStart(2, "0")) + "." + String(Math.floor((s % 1) * 10)); };
  v.addEventListener("timeupdate", () => { if (v.duration) { scrub.value = Math.round(1000 * v.currentTime / v.duration); time.textContent = mmss(v.currentTime) + " / " + mmss(v.duration); } });
  v.addEventListener("play", () => play.textContent = "❚❚"); v.addEventListener("pause", () => play.textContent = "▶");
  play.onclick = () => { if (v.paused) v.play(); else v.pause(); syncCmp(); };
  scrub.oninput = () => { if (v.duration) { v.currentTime = scrub.value / 1000 * v.duration; syncCmp(true); } };
  $("#s-start").onclick = () => { v.currentTime = 0; syncCmp(true); };
  const frame = () => (viewRec(CUR).seconds / viewRec(CUR).frames) || 1 / 24;
  $("#s-prev").onclick = () => { v.pause(); v.currentTime = Math.max(0, v.currentTime - frame()); syncCmp(true); };
  $("#s-next").onclick = () => { v.pause(); v.currentTime = Math.min(v.duration || 1e9, v.currentTime + frame()); syncCmp(true); };
  const setRate = r => { RATE = Math.min(4, Math.max(0.125, r)); v.playbackRate = RATE; rate.textContent = (RATE < 1 ? RATE.toFixed(2).replace(/0+$/, "") : RATE) + "×"; const c = $("#c-video"); if (c) c.playbackRate = RATE; };
  $("#s-slower").onclick = () => setRate(RATE / 2); $("#s-faster").onclick = () => setRate(RATE * 2);
  v.onclick = () => play.onclick();
  document.addEventListener("keydown", e => { if (e.target.matches("input,select,textarea")) return; if (e.key === " ") { e.preventDefault(); play.onclick(); } if (e.key === "ArrowLeft") $("#s-prev").onclick(); if (e.key === "ArrowRight") $("#s-next").onclick(); });
}
function syncCmp(seek) { const c = $("#c-video"), v = $("#s-video"); if (!c || !CMP) return; if (seek && c.duration) c.currentTime = Math.min(c.duration, v.currentTime / (v.duration || 1) * c.duration); if (v.paused) c.pause(); else c.play().catch(() => {}); }

/* tabs */
function initTabs() {
  const tabs = [...document.querySelectorAll(".tabs [role=tab]")];
  const pick = id => { for (const t of tabs) { const on = t.dataset.tab === id; t.setAttribute("aria-selected", String(on)); const p = $("#tab-" + t.dataset.tab); if (p) p.classList.toggle("on", on); } };
  for (const t of tabs) t.onclick = () => pick(t.dataset.tab);
  pick("explain");
  buildCompare();
}

/* compare: a second case of the same experiment, side by side, playback synchronised */
function buildCompare() {
  const box = $("#cmp-ctl"); box.innerHTML = "";
  const f = el("div", "field"); const lab = el("label", null, "Compare with"); lab.htmlFor = "cmp-sel"; f.append(lab);
  const sel = el("select"); sel.id = "cmp-sel"; const o0 = el("option", null, "nothing (single view)"); o0.value = ""; sel.append(o0);
  for (const s of D.sweeps) { const og = el("optgroup"); og.label = s.name; for (const c of s.cases) { const o = el("option", null, c.label); o.value = c.id; og.append(o); } sel.append(og); }
  sel.onchange = () => setCompare(sel.value || null);
  f.append(sel); box.append(f);
  const g = $("#cmp-guided"); g.innerHTML = "";
  for (const c of D.compare || []) {
    const row = el("div", "gcmp"); row.append(el("div", "read small", c.text));
    if (c.a && c.b) { const b = el("button", "linkbtn", "show both"); b.type = "button"; b.onclick = () => { selectCase(c.a); setCompare(c.b); sel.value = c.b; }; row.append(b); }
    else if (c.a) { const b = el("button", "linkbtn", "open"); b.type = "button"; b.onclick = () => { selectCase(c.a); document.querySelector('.tabs [data-tab="plots"]').click(); }; row.append(b); }
    g.append(row);
  }
  if (!(D.compare || []).length) g.append(el("div", "muted small", "Pick any second case above; the two clips play together and the measurements are listed side by side."));
}
function setCompare(id) {
  CMP = id ? caseById(id) : null; const scr = $("#s-screen"), one = $("#s-single"), two = $("#s-split");
  scr.classList.toggle("split", !!CMP); one.hidden = !!CMP; two.hidden = !CMP;
  if (CMP) { updateCompare(); } else { $("#cmp-table").innerHTML = ""; loadVideo(CUR, $("#s-video"), null); }
}
function updateCompare() {
  const a = $("#a-video"), b = $("#c-video");
  $("#a-tag").textContent = CUR.label; $("#c-tag").textContent = CMP.label;
  // the main transport drives #s-video; in split mode #a-video mirrors it (same source)
  const main = $("#s-video"); const va = viewRec(CUR); a.poster = D.poster_base + CUR.id + "__" + va.slug + ".webp"; a.src = videoUrl(CUR.id, va.slug); a.muted = true; a.playbackRate = RATE;
  main.src = a.src; main.pause();
  const vb = CMP.views.find(v => v.view === VIEW) || CMP.views[0]; b.poster = D.poster_base + CMP.id + "__" + vb.slug + ".webp"; b.src = videoUrl(CMP.id, vb.slug); b.playbackRate = RATE;
  a.closest(".half").style.setProperty("--ar", va.width + "/" + va.height); b.closest(".half").style.setProperty("--ar", vb.width + "/" + vb.height);
  if (!REDUCED) { a.play().catch(() => {}); b.play().catch(() => {}); }
  // the transport controls act on both halves in split mode
  const link = (src, dst) => { src.addEventListener("play", () => dst.play().catch(() => {})); src.addEventListener("pause", () => dst.pause()); src.addEventListener("seeking", () => { if (dst.duration && src.duration) dst.currentTime = src.currentTime / src.duration * dst.duration; }); };
  if (!a.dataset.linked) { link(a, b); a.dataset.linked = "1"; $("#s-play").onclick = () => { const v = $("#s-single").hidden ? a : $("#s-video"); if (v.paused) v.play(); else v.pause(); if (v === a) { if (a.paused) b.pause(); else b.play().catch(() => {}); } }; }
  const t = $("#cmp-table"); t.innerHTML = "";
  const hd = el("tr"); hd.append(el("th", null, "measurement"), el("th", null, "A: " + CUR.label), el("th", null, "B: " + CMP.label)); t.append(hd);
  const keys = [...new Set([...Object.keys(CUR.metrics || {}), ...Object.keys(CMP.metrics || {})])];
  for (const k of keys) { const r = D.readouts.find(x => x[0] === k); const tr = el("tr"); const va_ = CUR.metrics[k], vb_ = CMP.metrics[k]; if (va_ != null && vb_ != null && Math.abs(va_ - vb_) > 1e-9 * Math.max(1, Math.abs(va_))) tr.classList.add("diff"); tr.append(el("td", null, r ? r[1] : k.replace(/_/g, " ")), el("td", null, fmt(va_ == null ? null : va_ * (r ? r[3] : 1))), el("td", null, fmt(vb_ == null ? null : vb_ * (r ? r[3] : 1)))); t.append(tr); }
  const pa = Object.keys(CUR.params).filter(k => JSON.stringify(CUR.params[k]) !== JSON.stringify(CMP.params[k]));
  for (const k of pa) { const tr = el("tr", "diff"); const spec = D.param_spec[k] || {}; tr.append(el("td", null, "parameter: " + (spec.label || k)), el("td", null, String(CUR.params[k])), el("td", null, String(CMP.params[k]))); t.append(tr); }
}

document.addEventListener("DOMContentLoaded", () => { initTheme(); initHome(); initExperiment(); });
