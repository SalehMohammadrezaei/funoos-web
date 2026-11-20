"""Build the static site from the finished runs.

    python tools/build_site.py <runs directory> <output directory> [--media-base URL]

Writes index.html, experiments/<id>.html, about.html, data/<id>.json, assets/, media/posters,
media/plots and (for a local preview) media/video. With --media-base the pages load the clips
from that URL prefix (the GitHub release) instead of media/video/.
"""
import argparse, html, json, re, shutil, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import cases  # noqa: E402
from flowzoo import catalog, engine  # noqa: E402

SITE = HERE.parent / "site"
APP_VERSION = re.search(r'^version\s*=\s*"([^"]+)"', (cases.FUNOOS / "pyproject.toml").read_text(), re.M).group(1)
RELEASES = "https://github.com/SalehMohammadrezaei/Funoos/releases"
REPO = "https://github.com/SalehMohammadrezaei/Funoos"
WEB_REPO = "https://github.com/SalehMohammadrezaei/funoos-web"
KATEX = "0.16.11"
READOUTS = [
    ("cl_circulation", "Lift C_l", "", 1.0), ("cd_wake_approx", "Drag C_d (wake estimate)", "", 1.0), ("strouhal", "Strouhal St", "", 1.0),
    ("permeability_cells2", "Permeability k", "cells²", 1.0), ("porosity", "Porosity φ", "", 1.0), ("porosity_requested", "Porosity asked for", "", 1.0),
    ("pore_reynolds", "Pore Reynolds number", "", 1.0), ("peclet", "Péclet number", "", 1.0), ("arrival_time_t50", "Arrival time t50", "steps", 1.0),
    ("dispersion_cells2_per_step", "Dispersion", "cells²/step", 1.0), ("dispersion_over_molecular", "Dispersion / molecular", "", 1.0),
    ("tracer_mass_balance", "Mass balance error", "", 1.0), ("fraction_left_the_sample", "Fraction left", "", 1.0), ("pore_volume_crossings", "Pore volumes crossed", "", 1.0),
    ("nusselt", "Nusselt Nu", "", 1.0), ("mixing_width_final_frac", "Mixing width (end)", "of height", 1.0),
    ("shock_radius_final_cells", "Shock radius (end)", "cells", 1.0),
    ("sod_err_rho", "Density error vs exact", "", 1.0), ("sod_err_u", "Velocity error vs exact", "", 1.0),
    ("ke_peak", "Peak kinetic energy", "", 1.0), ("ke_final", "Kinetic energy (end)", "", 1.0), ("ke_initial", "Kinetic energy (start)", "", 1.0),
    ("ke_drift_rel", "Energy change", "%", 100.0), ("enstrophy_final", "Enstrophy (end)", "", 1.0), ("pattern_coverage_pct", "Pattern coverage", "%", 1.0),
    ("dye_variance_final", "Dye variance (end)", "", 1.0), ("dye_variance_initial", "Dye variance (start)", "", 1.0), ("particles_final", "Particles", "", 1.0),
    ("speed_limiter_events", "Speed-limiter events", "", 1.0), ("fastest_motion_requested", "Fastest motion asked", "", 1.0), ("speed_limiter_suppressed_to", "Limited to", "", 1.0),
    ("shedding_frequency_per_step", "Shedding frequency", "per step", 1.0), ("norm_drift", "Norm drift", "", 1.0),
]
ACC = {"Lattice–Boltzmann": "#5b86f0", "Incompressible Navier–Stokes": "#e0a23a", "Compressible Euler": "#e35d6a",
       "Smoothed-Particle Hydrodynamics": "#56c5e8", "Pseudo-spectral": "#9b8cff", "Reaction–Diffusion": "#9be25a"}
SHORT = {"Incompressible Navier–Stokes": "Navier–Stokes", "Smoothed-Particle Hydrodynamics": "SPH"}
STATUS_SHORT = {"analytical": "Analytical", "numerical": "Numerical", "qualitative": "Qualitative"}
START_HERE = ["cylinder_wake", "dam_break", "kelvin_helmholtz", "rising_smoke", "gray_scott"]
# The view a page opens on (and its poster), where the app's first view hides the differences
# between cases: vorticity of a body on the ground is dominated by its boundary layer, and the
# Schlieren lines of a blast among buildings are faint; speed shows the wake and the shock.
DEFAULT_VIEW = {"car_silhouette": "Speed", "cycling_drafting": "Speed", "blast_obstacles": "Speed"}
E = html.escape


def shell(title, body, depth=0, active="", extra_head=""):
    r = "../" * depth
    nav = [("index.html", "⌂", "Home", "home"), ("index.html#gallery", "▦", "Experiments", "gallery"), ("about.html", "ⓘ", "About", "about")]
    rail = "".join(f'<a class="railbtn{" on" if active == k else ""}" href="{r}{href}" aria-label="{lbl}">{ic}<span class="lbl">{lbl}</span></a>' for href, ic, lbl, k in nav)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{E(title)}</title>
<meta name="description" content="Funoos on the web: pre-run fluid simulations of {len(catalog.EXPERIMENTS)} experiments, with the app's measurements, plots and explanations.">
<link rel="icon" href="{r}assets/favicon.svg" type="image/svg+xml">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Figtree:wght@400;600;700;800&display=swap">
<link rel="stylesheet" href="{r}assets/app.css">
<link rel="stylesheet" href="{r}assets/web.css">
<script>try{{if((localStorage.getItem('funoos.web.theme')||(matchMedia('(prefers-color-scheme: light)').matches?'light':'dark'))==='light')document.documentElement.setAttribute('data-theme','light')}}catch(e){{}}</script>
<script src="{r}assets/config.js"></script>
{extra_head}
</head>
<body>
<div id="bg"></div>
<div id="app">
  <nav id="rail" aria-label="Site">
    <a class="logo" href="{r}index.html" aria-label="Funoos home">F</a>
    {rail}
    <div class="railspace"></div>
    <button class="railbtn themebtn" id="themebtn" type="button" aria-label="Switch theme">☀<span class="lbl">Theme</span></button>
    <a class="railbtn" href="{REPO}" target="_blank" rel="noopener" aria-label="GitHub">⎇<span class="lbl">GitHub</span></a>
  </nav>
  <div id="content"><main>{body}</main></div>
</div>
<script src="{r}assets/web.js"></script>
</body>
</html>"""


def footer():
    return (f'<div class="footer"><span>Funoos {APP_VERSION} · created by Saleh Mohammadrezaei · MIT licence</span>'
            f'<a href="{REPO}" target="_blank" rel="noopener">source code</a><a href="{RELEASES}" target="_blank" rel="noopener">download the app</a>'
            f'<a href="{WEB_REPO}" target="_blank" rel="noopener">this site</a></div>')


def load_runs(runs):
    out = {}
    for m in sorted(Path(runs).glob("*/meta.json")):
        d = json.loads(m.read_text())
        if d.get("ok"):
            d["_dir"] = m.parent; out[d["case"]["id"]] = d
    return out


def param_spec(ex):
    spec = {}
    for q in engine.EXHIBITS[ex]["params"]:
        spec[q["name"]] = {"label": q.get("label", q["name"]), "units": q.get("units", ""), "help": q.get("help", ""), "fixed": q.get("fixed", "")}
    return spec


def fixed_text(ex, names):
    spec = param_spec(ex)
    return "; ".join(f"{spec[n]['label']}: {spec[n]['fixed']}" for n in names if spec.get(n, {}).get("fixed"))


def experiment_manifest(e, lib, runs, out, media_base):
    """data/<id>.json plus the copied posters and plots. Returns the manifest (or None when nothing ran)."""
    exp_cases = [c for c in lib if c["experiment"] == e["id"] and c["id"] in runs]
    if not exp_cases:
        return None
    ex = exp_cases[0]["exhibit"]
    (out / "media" / "posters").mkdir(parents=True, exist_ok=True)
    recs, sweeps = [], {}
    for c in exp_cases:
        m = runs[c["id"]]; d = m["_dir"]
        views = []
        for v in m["views"]:
            slug = Path(v["mp4"]).stem
            shutil.copy2(d / v["poster"], out / "media" / "posters" / f"{c['id']}__{slug}.webp")
            if not media_base:
                (out / "media" / "video").mkdir(parents=True, exist_ok=True)
                shutil.copy2(d / v["mp4"], out / "media" / "video" / f"{c['id']}__{slug}.mp4")
            views.append({"view": v["view"], "slug": slug, "width": v["width"], "height": v["height"], "frames": v["frames"], "seconds": v["seconds"]})
        pdir = out / "media" / "plots" / c["id"]; pdir.mkdir(parents=True, exist_ok=True)
        for p in m["plots"]:
            shutil.copy2(d / p["file"], pdir / p["file"])
        s = catalog.scene(c["scene"])
        values = dict(c["overrides"]) if c["sweep"] != "Presets of the app" else {}
        rec = {"id": c["id"], "scene": c["scene"], "sweep": c["sweep"], "label": c["label"], "overrides": c["overrides"], "values": values,
               "params": m["params"], "metrics": m["metrics"], "derived": m["derived"], "quality": m["quality"], "views": views,
               "plots": [{"title": p["title"], "file": p["file"], "explain": p["explain"]} for p in m["plots"]],
               "result": {"shape": m["result"].get("shape"), "frames": m["result"].get("frames"), "time_unit": m["result"].get("time_unit")},
               "status": s["status"], "status_label": catalog.STATUS_LABEL[s["status"]], "checks": m["checks"]["all"],
               "fixed_text": fixed_text(ex, list(c["overrides"]))}
        if c["sweep"] == "Presets of the app":
            rec["label"] = f"{c['label']} ({s['name']})"
        recs.append(rec)
        sw = sweeps.setdefault(c["sweep"], {"name": c["sweep"], "params": [], "cases": []})
        if c["sweep"] != "Presets of the app":
            sw["params"] = list(dict.fromkeys(sw["params"] + list(c["overrides"])))
        sw["cases"].append({"id": c["id"], "label": rec["label"], "values": values})
        for al in c["aliases"]:                                  # one run listed in every place it belongs
            if al["sweep"] == "Presets of the app":              # a sweep point that equals a preset
                asc = catalog.scene(al["scene"])
                sweeps.setdefault("Presets of the app", {"name": "Presets of the app", "params": [], "cases": []})["cases"].append(
                    {"id": c["id"], "label": f"{al['label']} ({asc['name']})", "values": {}})
            else:                                                # a preset that equals a sweep point
                sw2 = sweeps.setdefault(al["sweep"], {"name": al["sweep"], "params": [], "cases": []})
                sw2["params"] = list(dict.fromkeys(sw2["params"] + list(al["overrides"])))
                sw2["cases"].append({"id": c["id"], "label": al["label"], "values": dict(al["overrides"])})
    grid = {name: (names, values) for name, names, values in cases.SWEEPS.get(e["id"], [])}
    for name, sw in sweeps.items():                              # grid order, so the dropdowns read in order
        if name in grid:
            names, values = grid[name]
            idx = {tuple(v): i for i, v in enumerate(values)}
            sw["cases"].sort(key=lambda k: idx.get(tuple(k["values"].get(n) for n in names), len(idx)))
        sw["fixed_text"] = fixed_text(ex, sw["params"])
    # presets first, in the app's order
    order = {k: i for i, (k, _l) in enumerate(e["presets"])}
    pre = sweeps.get("Presets of the app")
    if pre:
        seen = set(); uniq = []
        for k in pre["cases"]:
            if k["id"] not in seen:
                seen.add(k["id"]); uniq.append(k)
        pre["cases"] = sorted(uniq, key=lambda k: order.get(next((c["scene"] for c in exp_cases if c["id"] == k["id"]), ""), 99))
    sweep_list = ([pre] if pre else []) + sorted((s for n, s in sweeps.items() if n != "Presets of the app"),
                                                 key=lambda s: list(grid).index(s["name"]) if s["name"] in grid else len(grid))
    rep_id = next((c["id"] for c in exp_cases if c["scene"] == e["representative"] and c["sweep"] == "Presets of the app"), exp_cases[0]["id"])
    scenes = {}
    for c in exp_cases:
        if c["scene"] not in scenes:
            L = catalog.scene_layers(c["scene"])
            for lay in L["layers"]:
                if lay["id"] == "model":
                    lay["eq"] = engine.META.get(ex, {}).get("eq")
            scenes[c["scene"]] = L
    rep = catalog.scene(e["representative"])
    man = {"id": e["id"], "name": e["name"], "question": e["question"], "exhibit": ex, "phenomenon": rep["phenomenon"], "method": rep["method"],
           "method_label": engine.META.get(ex, {}).get("method", ""), "representative": rep_id, "default_view": DEFAULT_VIEW.get(e["id"]),
           "cases": recs, "sweeps": sweep_list,
           "scenes": scenes, "param_spec": param_spec(ex), "readouts": READOUTS,
           "compare": [{"a": _case_for_scene(exp_cases, a), "b": _case_for_scene(exp_cases, b) if b else None, "text": t} for a, b, t in e.get("compare", [])],
           "poster_base": "../media/posters/", "plot_base": "../media/plots/", "video_base": media_base or "../media/video/",
           "app_version": APP_VERSION}
    (out / "data").mkdir(exist_ok=True)
    (out / "data" / f"{e['id']}.json").write_text(json.dumps(man, ensure_ascii=False))
    return man


def opening_view(case, man):
    return next((v for v in case["views"] if v["view"] == man.get("default_view")), case["views"][0])


def _case_for_scene(exp_cases, scene_key):
    for c in exp_cases:
        if c["scene"] == scene_key and c["sweep"] == "Presets of the app":
            return c["id"]
        if any(al["scene"] == scene_key for al in c["aliases"]):
            return c["id"]
    return None


def experiment_page(man, out):
    e = man; acc = ACC.get(e["method"], "#5b86f0")
    rep = next(c for c in e["cases"] if c["id"] == e["representative"]); v0 = opening_view(rep, e)
    head = (f'<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/KaTeX/{KATEX}/katex.min.css">'
            f'<script defer src="https://cdnjs.cloudflare.com/ajax/libs/KaTeX/{KATEX}/katex.min.js" onload="window.dispatchEvent(new Event(\'katex-ready\'))"></script>')
    body = f"""
<div class="page" id="exp" data-manifest="../data/{e['id']}.json">
  <div class="toprow"><div class="breadcrumbs"><a href="../index.html">Experiments</a> › <a href="../index.html#g-{E(slug(e['phenomenon']))}">{E(e['phenomenon'])}</a></div><span class="spacer"></span><span class="brand"><b>FUN</b>OOS</span></div>
  <header class="exphead">
    <div class="kicker"><span class="dot" style="display:inline-block;width:8px;height:8px;border-radius:50%;background:{acc};margin-right:6px"></span>{E(e['phenomenon'])} · {E(e['method_label'] or e['method'])}</div>
    <h1>{E(e['name'])}</h1>
    <div class="dq"><span class="read">{E(e['question'])}</span> <span id="d-status" class="statusbadge status-{rep['status']}">{E(rep['status_label'])}</span></div>
  </header>
  <div class="xgrid">
    <div class="stagecol">
      <section class="glass controls" aria-label="Case selection">
        <div class="phead"><div class="kicker">pre-run cases</div><span class="muted small">{len(e['cases'])} cases · resolution High</span></div>
        <div class="note" style="margin-bottom:10px">These are <b>pre-run</b> simulations: pick from the values below. To choose any value, change the geometry or run longer, <a href="{RELEASES}" target="_blank" rel="noopener">install Funoos</a> (free, macOS · Windows · Linux).</div>
        <div id="ctrl"></div>
        <div class="held" id="c-held"></div>
        <div class="caselabel" id="c-case"></div>
      </section>
      <div class="viewbar"><div class="seg views" id="s-views" role="group" aria-label="View"></div><span class="spacer"></span><span class="muted small" id="s-caption"></span></div>
      <div class="screen glass" id="s-screen">
        <div id="s-single" style="display:contents">
          <video id="s-video" loop muted playsinline preload="metadata" poster="../media/posters/{rep['id']}__{v0['slug']}.webp" aria-label="{E(e['name'])} clip"></video>
        </div>
        <div id="s-split" hidden style="display:contents">
          <div class="half"><span class="tag" id="a-tag">A</span><video id="a-video" loop muted playsinline preload="metadata"></video></div>
          <div class="half"><span class="tag" id="c-tag">B</span><video id="c-video" loop muted playsinline preload="metadata"></video></div>
        </div>
      </div>
      <div class="glass tile transport" aria-label="Playback">
        <div class="transport">
          <button id="s-start" type="button" aria-label="Go to start">⏮</button><button id="s-prev" type="button" aria-label="Previous frame">◀</button>
          <button id="s-play" type="button" aria-label="Play or pause">▶</button><button id="s-next" type="button" aria-label="Next frame">▶▶</button>
          <input type="range" class="scrub" id="s-scrub" min="0" max="1000" value="0" aria-label="Playback position">
          <span class="tlabel time" id="s-time">0:00.0 / 0:00.0</span>
          <span class="tlabel muted" style="min-width:0">speed</span><button id="s-slower" type="button" aria-label="Slower">–</button><span class="tlabel" id="s-rate" style="min-width:34px">1×</span><button id="s-faster" type="button" aria-label="Faster">+</button>
        </div>
      </div>
      <div class="readouts" id="s-kpis" aria-label="Readouts"></div>
      <div class="quality" id="s-quality"></div>
      <div class="status muted small" id="s-status"></div>
    </div>
    <aside class="glass panelcol" aria-label="Explanation, plots and comparison">
      <div class="panelbody">
        <div class="seg tabs" role="tablist" style="margin-bottom:12px">
          <button role="tab" type="button" data-tab="explain" aria-selected="true">Explain</button>
          <button role="tab" type="button" data-tab="plots" aria-selected="false">Plots</button>
          <button role="tab" type="button" data-tab="compare" aria-selected="false">Compare</button>
          <button role="tab" type="button" data-tab="setup" aria-selected="false">Setup</button>
        </div>
        <div class="tabpanel" id="tab-explain" role="tabpanel"><div id="s-layers"><div class="loading">Loading…</div></div></div>
        <div class="tabpanel" id="tab-plots" role="tabpanel"><div class="muted small" style="margin-bottom:10px">The app's own diagnostics for the case shown on the left.</div><div id="s-plots"></div></div>
        <div class="tabpanel" id="tab-compare" role="tabpanel"><div class="cmpctl"><div id="cmp-ctl"></div><div class="kicker">guided comparisons</div><div class="guided" id="cmp-guided"></div></div><table class="cmp" id="cmp-table"></table></div>
        <div class="tabpanel" id="tab-setup" role="tabpanel"><div class="kicker" style="margin-bottom:6px">derived quantities</div><div class="derived" id="s-derived"></div><div class="kicker" style="margin:14px 0 6px">all parameters of this case</div><table class="params" id="s-params"></table></div>
      </div>
    </aside>
  </div>
  {footer()}
</div>"""
    (out / "experiments").mkdir(exist_ok=True)
    (out / "experiments" / f"{e['id']}.html").write_text(shell(f"{e['name']} · Funoos", body, depth=1, active="gallery", extra_head=head))


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def home(mans, out, n_cases):
    by_phen = {}
    for m in mans:
        by_phen.setdefault(m["phenomenon"], []).append(m)
    exp_of = {m["id"]: m for m in mans}

    def card(m):
        rep = next(c for c in m["cases"] if c["id"] == m["representative"]); v0 = opening_view(rep, m)
        acc = ACC.get(m["method"], "#5b86f0"); method = SHORT.get(m["method"], m["method"])
        hay = E(" ".join([m["name"], m["question"], m["phenomenon"], m["method"], m["method_label"]] + [c["label"] for c in m["cases"]]).lower())
        return (f'<a class="gcard" href="experiments/{m["id"]}.html" data-phen="{E(m["phenomenon"])}" data-hay="{hay}">'
                f'<div class="media"><img class="poster" src="media/posters/{rep["id"]}__{v0["slug"]}.webp" alt="" loading="lazy">'
                f'<video data-src="{(MEDIA_BASE or "media/video/")}{rep["id"]}__{v0["slug"]}.mp4" loop muted playsinline preload="none" poster="media/posters/{rep["id"]}__{v0["slug"]}.webp" aria-hidden="true"></video></div>'
                f'<div class="gbody"><div class="ttl">{E(m["name"])}</div><div class="sub">{E(m["question"])}</div>'
                f'<div class="gmeta"><span class="dot" style="background:{acc}"></span><span>{E(method)}</span><span class="sep">·</span><span class="cases">{len(m["cases"])} cases</span>'
                f'<span class="sep">·</span><span class="st status-{rep["status"]}" title="{E(rep["status_label"])}">{STATUS_SHORT[rep["status"]]}</span></div></div></a>')

    chips = '<button class="chipbtn" type="button" data-value="" aria-pressed="true">All <span class="n">%d</span></button>' % len(mans)
    chips += "".join(f'<button class="chipbtn" type="button" data-value="{E(p)}" aria-pressed="false">{E(p)} <span class="n">{len(v)}</span></button>' for p, v in by_phen.items())
    start = "".join(card(exp_of[i]) for i in START_HERE if i in exp_of)
    groups = ""
    for p, v in by_phen.items():
        groups += f'<div class="ghead" data-group="{E(p)}" id="g-{slug(p)}"><h2>{E(p)}</h2><span class="muted">{len(v)} experiment{"s" if len(v) != 1 else ""}</span></div>'
        groups += "".join(card(m) for m in v)
    methods = sorted({m["method"] for m in mans})
    body = f"""
<div class="page">
  <section class="hero">
    <div class="wordmark reveal"><span class="fun">FUN</span><span class="oos">OOS</span></div>
    <div class="tagline reveal">Explore fluid motion through simulation.</div>
    <div class="subtitle reveal">The Funoos laboratory in your browser: {n_cases} simulations from {len(mans)} experiments, pre-run at the app's highest gallery quality.<br>Choose an experiment, pick a case, and inspect the fields, measurements and explanations. Nothing to install.</div>
    <div class="statrow reveal">
      <div class="stat"><div class="n" data-count="{len(mans)}">0</div><div class="l">experiments</div></div>
      <div class="stat"><div class="n" data-count="{n_cases}">0</div><div class="l">pre-run cases</div></div>
      <div class="stat"><div class="n" data-count="{len(methods)}">0</div><div class="l">methods</div></div>
      <div class="stat"><div class="n" data-count="{len(by_phen)}">0</div><div class="l">phenomena</div></div>
    </div>
    <div class="introchips reveal">{"".join(f'<span class="chip">{E(SHORT.get(m, m))}</span>' for m in methods)}</div>
    <div class="ctas reveal"><a class="btn btn-primary cta" href="#gallery">Explore the simulations →</a><a class="btn btn-ghost cta" href="{RELEASES}" target="_blank" rel="noopener">Install the app for any value</a></div>
  </section>
  <section id="gallery">
    <div class="gal-head">
      <div class="gal-titles"><div class="kicker">experiments</div><h1>Explore the simulations</h1><div class="gal-sub">{len(mans)} experiments with {n_cases} pre-run cases, organised by phenomenon. Every page carries the app's own explanation, equations, diagnostics and a side-by-side comparison.</div></div>
      <div class="galtools" role="search"><label class="sr" for="g-search">Search experiments</label><input id="g-search" type="search" placeholder="Search experiments, questions, methods"></div>
      <nav class="phenchips" aria-label="Show one phenomenon">{chips}</nav>
    </div>
    <div id="gallery-start"><div class="ghead"><h2>Start here</h2><span class="muted">one experiment from each kind of flow</span></div><div class="startrow">{start}</div></div>
    <div class="cargrid" id="gallery-grid">{groups}</div>
    <div class="muted" id="g-none" hidden>No experiments match this filter.</div>
  </section>
  {footer()}
</div>"""
    (out / "index.html").write_text(shell("Funoos", body, depth=0, active="home"))


def about(mans, out, n_cases, runs):
    total_s = sum(runs[c["id"]]["timing"]["total_s"] for m in mans for c in m["cases"])
    rows = "".join(f'<tr><td><a href="experiments/{m["id"]}.html">{E(m["name"])}</a></td><td>{E(m["phenomenon"])}</td><td>{E(SHORT.get(m["method"], m["method"]))}</td><td>{len(m["cases"])}</td><td>{E("; ".join(s["name"] for s in m["sweeps"] if s["name"] != "Presets of the app") or "the app's presets")}</td></tr>' for m in mans)
    body = f"""
<div class="page about">
  <div class="kicker">about</div>
  <h1>Funoos on the web</h1>
  <p class="read">Funoos is a free, open-source desktop laboratory for two-dimensional fluid motion and pattern formation, created by Saleh Mohammadrezaei (University of Manchester). This site is the same laboratory with the running already done: every case here was computed with the desktop app, version {APP_VERSION}, at the app's High resolution and 1.8× the reference duration, then rendered with the app's own views, measurements, diagnostic plots and explanations.</p>
  <p class="read">The pages offer fixed choices. If you want a value that is not listed, a different geometry, your own text in the wind tunnel, a longer run or a colour palette change, <a href="{RELEASES}" target="_blank" rel="noopener">install Funoos</a>: it runs on macOS, Windows and Linux and needs no account.</p>
  <h2 style="margin:18px 0 8px">What is here</h2>
  <ul>
    <li>{len(mans)} experiments, {n_cases} pre-run cases. All 51 presets of the app are included unchanged; the extra cases sweep the parameters each experiment is about, at values that pass the app's own validity checks with no warnings.</li>
    <li>Every clip is the app's rendering (H.264, longest side 960 px, 24 frames per second, {len(mans) and sum(len(c["views"]) for m in mans for c in m["cases"])} clips in all).</li>
    <li>Measurements and plots come from the app's diagnostics module; the explanation layers, equations and references are the app's own text.</li>
    <li>Each case records the solver's quality assessment. A case reads "qualitatively" when the solver itself reported a reason, for example a speed limiter that fired or a pore Reynolds number above one.</li>
  </ul>
  <h2 style="margin:18px 0 8px">Experiments and sweeps</h2>
  <table><tr><th>Experiment</th><th>Phenomenon</th><th>Method</th><th>Cases</th><th>Swept</th></tr>{rows}</table>
  <h2 style="margin:18px 0 8px">How the cases were produced</h2>
  <p class="read">A batch script ran every case through the app's engine on one workstation (about {total_s / 3600:.1f} processor-hours of wall time across the jobs), checked that the solver finished, that all fields and frames are finite, that the measurements are finite and that each clip changes over time, and recorded the solver's quality notes. The scripts are in the <a href="{WEB_REPO}" target="_blank" rel="noopener">site repository</a>.</p>
  <h2 style="margin:18px 0 8px">Citation</h2>
  <pre class="cite">Mohammadrezaei, S. (2026). Funoos — fluid simulation laboratory (version {APP_VERSION}) [Computer software]. {REPO}</pre>
  <p class="muted small">Funoos is released under the MIT licence. Built with NumPy, SciPy, Matplotlib, Pillow, pywebview and ffmpeg; this site uses KaTeX for the equations. Solver families follow published methods cited on each experiment page.</p>
  {footer()}
</div>"""
    (out / "about.html").write_text(shell("About · Funoos", body, depth=0, active="about"))


MEDIA_BASE = ""


def main():
    global MEDIA_BASE
    ap = argparse.ArgumentParser(); ap.add_argument("runs"); ap.add_argument("out"); ap.add_argument("--media-base", default="")
    a = ap.parse_args(); MEDIA_BASE = a.media_base
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    # generated folders are rebuilt from scratch, so a case or experiment that left the library
    # does not linger in the site
    for sub in ("data", "experiments", "media/posters", "media/plots", "media/video"):
        shutil.rmtree(out / sub, ignore_errors=True)
    (out / "assets").mkdir(exist_ok=True)
    for f in ("app.css", "web.css", "web.js", "favicon.svg"):
        shutil.copy2(SITE / "assets" / f, out / "assets" / f)
    (out / "assets" / "config.js").write_text(f'window.FUNOOS_MEDIA_BASE = {json.dumps(MEDIA_BASE)};\n')
    (out / ".nojekyll").write_text("")
    runs = load_runs(a.runs); lib = cases.build()
    mans = []
    for e in catalog.EXPERIMENTS:
        m = experiment_manifest(e, lib, runs, out, MEDIA_BASE)
        if m:
            mans.append(m); experiment_page(m, out)
    n_cases = sum(len(m["cases"]) for m in mans)
    home(mans, out, n_cases); about(mans, out, n_cases, runs)
    print(f"site: {len(mans)} experiments, {n_cases} cases -> {out}")


if __name__ == "__main__":
    main()
