"""Build the static site: the Funoos desktop interface, answered from the pre-run library.

    python tools/build_site.py <runs directory> <output directory> [--media-base URL]

The pages are the desktop app's own interface (index.html, web/app.js, web/app.css, web/logic.js,
copied unchanged from the Funoos source), with two additions from site/:

    web_backend.js    answers the app's backend calls (window.pywebview.api) from data/ instead of
                      the Python solver: catalogue, scenes, runs, views, plots, run history, sweeps
    web_overrides.js  the few changes a pre-run library needs: the Studio offers the pre-run
                      values of each parameter, results load at once, side-by-side comparison of
                      two clips, exports that need raw fields point to the desktop app, links

Written: index.html, web/, data/ (catalog, exhibits, about, scene/<key>.json, cases.json,
case/<id>.json), media/posters, media/plots, results/gallery/thumbs (the app's card thumbnails)
and redirects from older addresses (experiments/<id>.html#<case id>, about.html, preview/). With --media-base the
clips load from that URL prefix (the GitHub release); without it they are copied to media/video/
for a local preview.
"""
import argparse, json, math, shutil, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import cases  # noqa: E402
from flowzoo import catalog  # noqa: E402

FUNOOS = cases.FUNOOS
sys.path.insert(0, str(FUNOOS))
import funoos_app  # noqa: E402

SITE = HERE.parent / "site"
RELEASES = "https://github.com/SalehMohammadrezaei/Funoos/releases"
RES = cases.RESOLUTION.split(" (")[0]          # the library's resolution as the intro names it: High, Ultra
# Readouts under the stage: the app's list (funoos_app._READOUTS) plus the tracer and SPH
# measurements it does not show; the first four available are used, as in the app.
READOUTS = [
    ("cl_circulation", "Lift C_l", "", 1.0), ("cd_wake_approx", "Drag C_d (wake estimate)", "", 1.0), ("strouhal", "Strouhal St", "", 1.0),
    ("permeability_cells2", "Permeability k", "cells²", 1.0), ("porosity", "Porosity φ", "", 1.0),
    ("peclet", "Péclet number", "", 1.0), ("dispersion_over_molecular", "Dispersion / molecular", "", 1.0),
    ("arrival_time_t50", "Arrival time t50", "steps", 1.0), ("tracer_mass_balance", "Mass balance error", "", 1.0),
    ("nusselt", "Nusselt Nu", "", 1.0), ("mixing_width_final_frac", "Mixing width (end)", "of height", 1.0),
    ("shock_radius_final_cells", "Shock radius (end)", "cells", 1.0),
    ("sod_err_rho", "Density error vs exact", "", 1.0), ("sod_err_u", "Velocity error vs exact", "", 1.0),
    ("ke_peak", "Peak kinetic energy", "", 1.0), ("ke_final", "Kinetic energy (end)", "", 1.0), ("ke_drift_rel", "Energy change", "%", 100.0),
    ("enstrophy_final", "Enstrophy (end)", "", 1.0), ("pattern_coverage_pct", "Pattern coverage", "%", 1.0),
    ("dye_variance_final", "Dye variance (end)", "", 1.0), ("particles_final", "Particles", "", 1.0),
    ("speed_limiter_events", "Speed-limiter events", "", 1.0), ("norm_drift", "Norm drift", "", 1.0),
]
# The view a case opens on where the app's first view hides the differences between cases:
# vorticity of a body on the ground is dominated by its boundary layer, and the Schlieren lines
# of a blast among buildings are faint; speed shows the wake and the shock.
DEFAULT_VIEW = {"car_silhouette": "Speed", "cycling_drafting": "Speed", "blast_obstacles": "Speed"}


def stats(metrics, rmeta):
    """The readout strip of the app (funoos_app._stats) from the stored measurements."""
    out = []
    for key, label, unit, scale in READOUTS:
        v = metrics.get(key)
        if not isinstance(v, (int, float)) or isinstance(v, bool) or not math.isfinite(v):
            continue
        val = float(v) * scale
        out.append({"l": label, "v": str(int(round(val))) if key in ("particles_final", "speed_limiter_events") else f"{val:.3g}", "u": unit, "accent": not out})
        if len(out) >= 4:
            break
    times = rmeta.get("times") or []
    if times:
        out.append({"l": "simulated time", "v": f"{times[-1]:.4g}", "u": rmeta.get("time_unit", "")})
    out.append({"l": "frames", "v": str(rmeta.get("frames"))})
    return out


def grid_of(rmeta):
    eff = rmeta.get("effective") or {}
    if eff.get("nx") and eff.get("ny"):
        return f"{eff['nx']}×{eff['ny']}"
    sh = rmeta.get("shape")
    return f"{sh[1]}×{sh[0]}" if isinstance(sh, list) and len(sh) == 2 else ""


def patch_index(html, n_cases, n_exps):
    """The app's index.html with the web scripts and the few lines of text that differ."""
    def sub(old, new):
        nonlocal html
        if old not in html:
            raise SystemExit(f"index.html of Funoos changed; update build_site.patch_index: {old[:60]!r}")
        html = html.replace(old, new, 1)
    sub('<link rel="stylesheet" href="web/app.css">',
        '<meta name="description" content="Funoos in the browser: the desktop fluid-simulation laboratory with '
        f'{n_cases} pre-run simulations of {n_exps} experiments, their measurements, plots and explanations.">\n'
        '<link rel="icon" href="web/favicon.svg" type="image/svg+xml">\n'
        '<link rel="stylesheet" href="web/app.css">\n<link rel="stylesheet" href="web/web.css">')
    sub('A desktop laboratory for two-dimensional fluid motion and pattern formation.<br>Choose an experiment, adjust its setup, and inspect the resulting fields and measurements.',
        f'The Funoos laboratory in your browser: {n_cases} simulations pre-run at {RES} quality.<br>'
        'Choose an experiment, pick its setup from the pre-run values, and inspect the fields and measurements.')
    sub('<div class="stat"><div class="n" id="n-solvers" data-count="5">0</div><div class="l">solvers</div></div>',
        f'<div class="stat"><div class="n" id="n-cases" data-count="{n_cases}">0</div><div class="l">pre-run cases</div></div>')
    sub('''<button class="btn btn-primary cta reveal" onclick="show('gallery')">Explore the simulations →</button>''',
        '''<div class="ctarow reveal"><button class="btn btn-primary cta" onclick="show('gallery')">Explore the simulations →</button>'''
        f'''<button class="btn btn-ghost cta" onclick="openUrl('{RELEASES}')">Install the app for any value</button></div>''')
    sub('A desktop application for exploring two-dimensional fluid motion and pattern formation, created by Saleh Mohammadrezaei. Free and open source under the MIT licence.</p>',
        'A desktop application for exploring two-dimensional fluid motion and pattern formation, created by Saleh Mohammadrezaei. Free and open source under the MIT licence.</p>\n'
        f'        <p class="read" style="margin:0 0 18px">This is its web version: the same interface, with {n_cases} cases solved in advance by the app\'s own engine at {RES} resolution. '
        'The controls offer the pre-run values; for any other value, geometry or duration, '
        f'<a href="{RELEASES}" target="_blank" rel="noopener">install Funoos</a> (free, macOS · Windows · Linux).</p>')
    sub('<script src="web/logic.js"></script>',
        '<script src="web/config.js"></script>\n<script src="web/web_backend.js"></script>\n<script src="web/logic.js"></script>')
    sub('<script src="web/app.js"></script>', '<script src="web/app.js"></script>\n<script src="web/web_overrides.js"></script>')
    return html


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("runs"); ap.add_argument("out"); ap.add_argument("--media-base", default="")
    a = ap.parse_args(); runs, out, media = Path(a.runs), Path(a.out), a.media_base or "media/video/"
    out.mkdir(parents=True, exist_ok=True)
    # everything generated is rebuilt from scratch, so nothing retired lingers
    for sub in ("data", "web", "media", "results", "experiments", "assets", "preview"):
        shutil.rmtree(out / sub, ignore_errors=True)
    (out / "about.html").unlink(missing_ok=True)
    (out / "web").mkdir(parents=True); (out / "data" / "scene").mkdir(parents=True); (out / "data" / "case").mkdir(parents=True)
    for d in ("posters", "plots"):
        (out / "media" / d).mkdir(parents=True)

    lib = cases.build(); api = funoos_app.Api(store=funoos_app.RunStore(max_runs=2), sweep=False)
    exp_of = {e["id"]: e for e in catalog.EXPERIMENTS}
    rep_of = {e["id"]: e["representative"] for e in catalog.EXPERIMENTS}

    # ---- cases: the index the Studio matches against, and one detail file per case
    index, case_of_scene, details, missing = [], {}, {}, []
    for c in lib:
        m = runs / c["id"] / "meta.json"
        d = json.loads(m.read_text()) if m.exists() else {}
        if not d.get("ok"):
            missing.append(c["id"]); continue
        r = d["result"]; views = []
        for v in d["views"]:
            s = Path(v["mp4"]).stem
            shutil.copy2(runs / c["id"] / v["poster"], out / "media" / "posters" / f"{c['id']}__{s}.webp")
            if not a.media_base:
                (out / "media" / "video").mkdir(exist_ok=True)
                shutil.copy2(runs / c["id"] / v["mp4"], out / "media" / "video" / f"{c['id']}__{s}.mp4")
            views.append({"view": v["view"], "slug": s, "frames": v["frames"], "width": v["width"], "height": v["height"], "seconds": v["seconds"]})
        plots = []
        for p in d.get("plots", []):
            name = f"{c['id']}__{p['file']}"; shutil.copy2(runs / c["id"] / p["file"], out / "media" / "plots" / name)
            plots.append({"title": p["title"], "img": "media/plots/" + name, "explain": p.get("explain", "")})
        preset = c["sweep"] == "Presets of the app"
        if preset:
            case_of_scene[c["scene"]] = c["id"]
        dv = DEFAULT_VIEW.get(c["experiment"])
        default_view = dv if dv in r["views"] else r["views"][0]
        label = catalog.preset_label(c["scene"]) if preset else c["label"]
        index.append({"id": c["id"], "experiment": c["experiment"], "exhibit": c["exhibit"],
                      "scene": c["scene"] if preset else rep_of[c["experiment"]], "preset": preset,
                      "sweep": c["sweep"], "label": label, "params": c["params"], "aliases": [al["label"] for al in c["aliases"]]})
        details[c["id"]] = {
            "id": c["id"], "info": f"{exp_of[c['experiment']]['name']} · {label} · {grid_of(r)}", "label": label,
            "views": views, "default_view": default_view, "cmap": d.get("cmap"), "stats": stats(d.get("metrics", {}), r),
            "derived": d.get("derived", []), "plots": plots, "quality": d.get("quality", {}),
            "meta": {"kind": r.get("kind"), "frames": r.get("frames"), "times": r.get("times"), "time_unit": r.get("time_unit"), "shape": r.get("shape")},
            "grid": grid_of(r), "solve_s": d.get("timing", {}).get("solve_s"), "threads": d.get("timing", {}).get("threads")}
        (out / "data" / "case" / f"{c['id']}.json").write_text(json.dumps(details[c["id"]], separators=(",", ":"), ensure_ascii=False))
    if missing:
        raise SystemExit(f"{len(missing)} cases have no finished run, e.g. {missing[:3]}")
    (out / "data" / "cases.json").write_text(json.dumps({"cases": index}, separators=(",", ":"), ensure_ascii=False))

    # ---- the app's catalogue and scene descriptions, with clips and posters from the library
    thumbs = FUNOOS / "results" / "gallery" / "thumbs"
    (out / "results" / "gallery" / "thumbs").mkdir(parents=True)

    def media_of(key):
        dv = details[case_of_scene[key]]
        s = next(v["slug"] for v in dv["views"] if v["view"] == dv["default_view"])
        return media + f"{dv['id']}__{s}.mp4", f"media/posters/{dv['id']}__{s}.webp"

    cat = api.catalog()
    for g in cat["groups"]:
        for e in g["experiments"]:
            for pz in e["presets"]:
                pz["clip"], pz["poster"] = media_of(pz["key"])
                if all((thumbs / (pz["key"] + ext)).exists() for ext in (".mp4", ".jpg")):
                    for ext in (".mp4", ".jpg"):
                        shutil.copy2(thumbs / (pz["key"] + ext), out / "results" / "gallery" / "thumbs" / (pz["key"] + ext))
                    pz["thumb"], pz["thumb_poster"] = f"results/gallery/thumbs/{pz['key']}.mp4", f"results/gallery/thumbs/{pz['key']}.jpg"
                else:
                    pz["thumb"] = pz["thumb_poster"] = None
            rep = next(pz for pz in e["presets"] if pz["key"] == e["representative"])
            e["clip"], e["poster"] = rep["clip"], rep["poster"]
            e["thumb"], e["thumb_poster"] = rep["thumb"] or rep["clip"], rep["thumb_poster"] or rep["poster"]
            e["n_cases"] = sum(1 for x in index if x["experiment"] == e["id"])
    cat["counts"]["cases"] = len(index)
    (out / "data" / "catalog.json").write_text(json.dumps(cat, separators=(",", ":"), ensure_ascii=False))
    for s in catalog.SCENES:
        d = api.scene_detail(s["key"]); d.pop("req", None)
        d["clip"], d["poster"] = media_of(s["key"]); d["web_case"] = case_of_scene[s["key"]]
        (out / "data" / "scene" / f"{s['key']}.json").write_text(json.dumps(d, separators=(",", ":"), ensure_ascii=False))
    (out / "data" / "exhibits.json").write_text(json.dumps(api.exhibits(), separators=(",", ":"), ensure_ascii=False))
    (out / "data" / "about.json").write_text(json.dumps(api.about(), separators=(",", ":"), ensure_ascii=False))

    # ---- the interface: the app's files unchanged, plus the web layer
    n_exps = len({x["experiment"] for x in index})
    (out / "index.html").write_text(patch_index((FUNOOS / "index.html").read_text(), len(index), n_exps))
    for f in ("app.js", "app.css", "logic.js"):
        shutil.copy2(FUNOOS / "web" / f, out / "web" / f)
    for f in ("web_backend.js", "web_overrides.js", "web.css", "favicon.svg"):
        shutil.copy2(SITE / f, out / "web" / f)
    (out / "web" / "config.js").write_text(f"window.FUNOOS_MEDIA_BASE = {json.dumps(media)};\n")
    (out / ".nojekyll").write_text("")
    # Older addresses keep working. The first version of the site had one page per experiment,
    # experiments/<id>.html#<case id>, and about.html; the app interface was first shown at
    # preview/. A case id of the first version that is now an alias of another case (the same
    # setup reached from a preset and a sweep) leads to that case.
    built = {x["id"] for x in index}
    old = {e["id"]: {} for e in catalog.EXPERIMENTS}
    for c in lib:
        if c["id"] not in built:
            continue
        old[c["experiment"]][c["id"]] = c["id"]
        for al in c["aliases"]:
            ov = al["overrides"]
            aid = "__".join([c["experiment"]] + [f"{n}_{cases._slug(v)}" for n, v in ov.items()]) if ov else f"{c['experiment']}__{al['scene']}"
            old[c["experiment"]].setdefault(aid, c["id"])

    def redirect(path, title, to, script):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f'<!DOCTYPE html><meta charset="utf-8"><title>{title}</title><script>{script}</script>'
                        f'<noscript><meta http-equiv="refresh" content="0; url={to}"></noscript><a href="{to}">{title}</a>\n')

    for e in catalog.EXPERIMENTS:
        to = f"../index.html#e/{e['representative']}"
        m = json.dumps(old[e["id"]], separators=(",", ":"))
        redirect(out / "experiments" / f"{e['id']}.html", f"{e['name']} · Funoos", to,
                 f'var m={m},h=decodeURIComponent(location.hash.slice(1));location.replace(m[h]?"../index.html#c/"+m[h]:"{to}")')
    redirect(out / "about.html", "About · Funoos", "index.html#about", 'location.replace("index.html#about")')
    redirect(out / "preview" / "index.html", "Funoos", "../index.html", 'location.replace("../index.html"+location.hash)')
    rev = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=str(FUNOOS), capture_output=True, text=True).stdout.strip()
    print(f"site: {n_exps} experiments, {len(index)} cases, {len(catalog.SCENES)} scenes -> {out} (Funoos interface at {rev})")


if __name__ == "__main__":
    main()
