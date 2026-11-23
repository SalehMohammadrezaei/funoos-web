/* Funoos on the web: the desktop app's backend (window.pywebview.api) answered from the pre-run
   library in data/ instead of the Python solver. Every method returns the envelope the app
   expects ({ok: true, ...} or {ok: false, error}). Methods that need the raw simulation fields
   (probes, profiles, array and report exports, setup files) answer with a pointer to the desktop
   app. The object is published as window.pywebview by web_overrides.js, after it has adjusted
   the interface. */
"use strict";
(function () {
  const MEDIA = window.FUNOOS_MEDIA_BASE || "media/video/";
  const DESKTOP = "This needs the desktop app: it works on the raw simulation data, which the web version does not include.";
  const memo = {};
  function getJSON(p) {
    if (!memo[p]) memo[p] = fetch(p).then(r => { if (!r.ok) throw new Error("could not load " + p + " (" + r.status + ")"); return r.json(); })
      .catch(e => { delete memo[p]; throw e; });
    return memo[p];
  }
  const ok = o => Object.assign({ ok: true }, o);
  let INDEX = null;
  async function cases() { if (!INDEX) INDEX = (await getJSON("data/cases.json")).cases; return INDEX; }
  const detail = id => getJSON("data/case/" + id + ".json");
  const same = (a, b) => (typeof a === "number" && typeof b === "number")
    ? Math.abs(a - b) <= 1e-9 * Math.max(1, Math.abs(a), Math.abs(b)) : a === b;
  // The resolution and duration of a scene's defaults are not those of the library:
  // a setup built from defaults (guided comparisons) matches on the physics alone, and where
  // several resolutions of it exist (the Sod tube) the library's own is preferred.
  const RENDER = new Set(["resolution", "duration"]), LIBRARY_RES = window.FUNOOS_RESOLUTION || "High";
  function matches(c, params, skip) {
    for (const k in c.params) if (k in params && !(skip && RENDER.has(k)) && !same(c.params[k], params[k])) return false;
    return true;
  }
  async function findCase(exhibit, params) {
    const all = (await cases()).filter(c => c.exhibit === exhibit);
    return all.find(c => matches(c, params, false))
      || all.filter(c => matches(c, params, true)).sort((a, b) => (b.params.resolution === LIBRARY_RES) - (a.params.resolution === LIBRARY_RES))[0] || null;
  }
  const clip = (id, slug) => MEDIA + id + "__" + slug + ".mp4";
  const viewOf = (d, view) => d.views.find(v => v.view === view) || d.views.find(v => v.view === d.default_view) || d.views[0];

  // run history (the app's RunStore): the newest MAX_RUNS results, pinned ones kept
  const RUNS = new Map(), MAX_RUNS = 12; let seq = 0;
  function remember(rid, c, d, view) {
    RUNS.delete(rid); RUNS.set(rid, { c, d, view, pinned: false });
    const evicted = [];
    for (const [k, r] of RUNS) { if (RUNS.size <= MAX_RUNS) break; if (!r.pinned && k !== rid) { RUNS.delete(k); evicted.push(k); } }
    return evicted;
  }
  const runOrErr = rid => RUNS.get(rid) || null;
  function envelope(rid, r) {
    const v = viewOf(r.d, r.view);
    return { run_id: rid, info: r.d.info, views: r.d.views.map(x => x.view), view: v.view, cmaps: [r.d.cmap], defcmap: r.d.cmap,
             stats: r.d.stats, meta: r.d.meta, params: { ...r.c.params }, exhibit: r.c.exhibit, scene: r.c.scene, case_id: r.c.id,
             derived: r.d.derived, state: "completed", provenance: { source: "pre-run library", case: r.c.id }, parent: null };
  }

  const impl = {
    catalog: () => getJSON("data/catalog.json"),
    exhibits: () => getJSON("data/exhibits.json"),
    about: () => getJSON("data/about.json"),
    async scene_detail(key, req) {
      try { return { ...(await getJSON("data/scene/" + key + ".json")), req }; }
      catch (e) { return { ok: false, error: "unknown scene: " + key, req }; }
    },
    async validate(exhibit, params) { return ok({ exhibit, errors: [], warnings: [], applied: [], params }); },
    async derived(exhibit, params) { const c = await findCase(exhibit, params || {}); return ok({ exhibit, items: c ? (await detail(c.id)).derived : [] }); },
    async estimate(exhibit, params) {
      const c = await findCase(exhibit, params || {}); if (!c) return { ok: false, error: "not in the pre-run library" };
      const d = await detail(c.id), g = (d.grid || "0×0").split("×").map(Number);
      return ok({ grid: g, frames: d.meta.frames, mb: 0, seconds: d.solve_s || 0, threads: +d.threads || 1, pre_run: true });
    },
    async run(exhibit, params, view, cmap, fps, job_id) {
      const c = await findCase(exhibit, params || {});
      if (!c) return { ok: false, job_id, state: "failed", error: "This setup is not in the pre-run library. Pick one of the values the controls offer, or install Funoos to run any value." };
      const d = await detail(c.id), rid = job_id || ("w" + (++seq)), v = viewOf(d, view);
      const evicted = remember(rid, c, d, v.view);
      return ok({ ...envelope(rid, RUNS.get(rid)), job_id: rid, video: clip(c.id, v.slug), evicted,
                  validation: { ok: true, errors: [], warnings: [], applied: [] }, store: { runs: RUNS.size, bytes: 0 } });
    },
    async cancel(id) { return ok({ job_id: id, state: "completed", cancel_requested: false }); },
    async job(rid) { const r = runOrErr(rid); return r ? ok({ job_id: rid, exhibit: r.c.exhibit, params: { ...r.c.params }, state: "completed" }) : { ok: false, error: "unknown job" }; },
    async run_info(rid) { const r = runOrErr(rid); return r ? ok(envelope(rid, r)) : { ok: false, error: "run expired" }; },
    async render_view(rid, view, cmap, fps, req) {
      const r = runOrErr(rid); if (!r) return { ok: false, error: "run expired", run_id: rid, req };
      const v = viewOf(r.d, view); r.view = v.view;
      return ok({ run_id: rid, req, view: v.view, cmap: r.d.cmap, video: clip(r.c.id, v.slug), cached: true, field_rect: null,
                  poster: "media/posters/" + r.c.id + "__" + v.slug + ".webp" });
    },
    async preview_frame(rid, view, cmap, frac, req) {
      const r = runOrErr(rid); if (!r) return { ok: false, error: "run expired", req };
      const v = viewOf(r.d, view); return ok({ run_id: rid, req, view: v.view, cmap: r.d.cmap, index: 0, time: 0, img: "media/posters/" + r.c.id + "__" + v.slug + ".webp" });
    },
    async diagnostics(rid, req) { const r = runOrErr(rid); return r ? ok({ req, plots: r.d.plots }) : { ok: false, error: "run expired", req }; },
    async runs() {
      return ok({ runs: [...RUNS].map(([rid, r]) => ({ run_id: rid, info: r.d.info, pinned: r.pinned, bytes: 0, disk: 0 })),
                  max_runs: MAX_RUNS, max_bytes: 0, bytes: 0, disk_bytes: 0, disk_max: 0 });
    },
    async pin_run(rid, on) { const r = runOrErr(rid); if (r) r.pinned = !!on; return ok({}); },
    // a sweep over the pre-run values: one existing case per value, the others held as they are
    async sweep(exhibit, params, name, values, view, cmap, job_id) {
      const items = [], errors = [];
      for (const val of values) {
        const c = await findCase(exhibit, { ...params, [name]: val });
        if (!c) { errors.push({ value: val, error: "not pre-run" }); continue; }
        const d = await detail(c.id), v = viewOf(d, view), rid = (job_id || "s") + "_" + items.length;
        remember(rid, c, d, v.view);
        const metrics = {}; for (const s of d.stats.slice(0, 3)) if (s.l !== "frames" && s.l !== "simulated time") metrics[s.l] = +s.v;
        items.push({ value: val, run_id: rid, frame: "media/posters/" + c.id + "__" + v.slug + ".webp", metrics });
      }
      return ok({ name, items, errors, plot: null, retained: items.map(() => true), store: null, state: "completed" });
    },
    async settings() { return ok({ threads: 0, cpus: 0 }); },
    async open_url(u) { if (/^https?:\/\//.test(u)) window.open(u, "_blank", "noopener"); return ok({}); },
  };
  // anything else the app may call answers with the pointer to the desktop app
  const api = new Proxy(impl, { get: (t, k) => (k in t ? t[k] : async () => ({ ok: false, error: DESKTOP })) });
  window.FunoosWeb = { api, cases, detail, findCase, same, clip, DESKTOP, RELEASES: "https://github.com/SalehMohammadrezaei/Funoos/releases" };
})();
