"""Run one case of the library end to end and write everything the site needs.

    python tools/run_case.py <case id> <runs directory>

Output in <runs>/<case id>/:
    meta.json          case, parameters, result metadata, measurements, derived quantities,
                       quality, explanation layers, checks, timings
    series.json        time series of the diagnostics
    <view>.mp4         one clip per view (H.264 at 24 fps; CRF 28 and longest side 960 px, or
                       FUNOOS_CLIP_CRF / FUNOOS_CLIP_MAXW)
    <view>.webp        poster (a developed frame, 70 % through the clip)
    plot_<n>.svg       diagnostic plots (vector), titles and explanations in meta.json
The solver threads come from OMP_NUM_THREADS, set by the batch driver.
"""
import json, math, os, subprocess, sys, time, traceback
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import cases  # noqa: E402
from flowzoo import catalog, engine, postproc, render, schema  # noqa: E402

# clip size and quality: longest side at most MAXW px (never upscaled), H.264 CRF; the High
# library uses 960 / 28, the Ultra library FUNOOS_CLIP_MAXW=1920 FUNOOS_CLIP_CRF=23
MAXW, FPS, CRF = int(os.environ.get("FUNOOS_CLIP_MAXW", 960)), 24, int(os.environ.get("FUNOOS_CLIP_CRF", 28))


def _slug(view):
    return "".join(c if c.isalnum() else "_" for c in view).strip("_").lower()


def _finite_frames(frames_iter):
    """Pass frames through; raise if any is not finite. Frames are uint8, so the check is on shape."""
    for f in frames_iter:
        if f.ndim != 3 or f.shape[2] != 3:
            raise ValueError(f"bad frame shape {f.shape}")
        yield f


def _even_scale(w, h):
    s = min(1.0, MAXW / max(w, h))
    W, H = int(round(w * s / 2)) * 2, int(round(h * s / 2)) * 2
    return max(W, 2), max(H, 2)


def encode(result, view, cmap, out_mp4, out_poster, poster_at=cases.POSTER_AT_DEFAULT):
    frames = result.render(view, cmap)                     # list: needed twice (clip and poster)
    n = len(frames); h, w = frames[0].shape[:2]
    W, H = _even_scale(w, h)
    ff = render._ffmpeg()
    cmd = [ff, "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{w}x{h}", "-framerate", str(FPS),
           "-i", "-", "-vf", f"scale={W}:{H}:flags=lanczos", "-pix_fmt", "yuv420p", "-c:v", "libx264", "-preset", "slow",
           "-crf", str(CRF), "-movflags", "+faststart", str(out_mp4)]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    bad = 0
    for f in frames:
        f = np.ascontiguousarray(f, dtype=np.uint8)
        if f.shape[:2] != (h, w):
            bad += 1; continue
        p.stdin.write(f.tobytes())
    p.stdin.close(); err = p.stderr.read().decode(errors="replace"); p.wait()
    if p.returncode != 0:
        raise RuntimeError("ffmpeg: " + err[-300:])
    poster = frames[int(poster_at * (n - 1))]
    from PIL import Image
    im = Image.fromarray(poster)
    if im.width != W or im.height != H:
        im = im.resize((W, H), Image.LANCZOS)
    im.save(out_poster, "WEBP", quality=82, method=6)
    # still water or a tracer before injection may hold the first frames; the clip must change somewhere
    const = n > 2 and np.array_equal(frames[0], frames[-1]) and np.array_equal(frames[0], frames[n // 2])
    return {"view": view, "mp4": out_mp4.name, "poster": out_poster.name, "poster_at": poster_at, "frames": n, "width": W, "height": H,
            "seconds": round(n / FPS, 2), "bytes": out_mp4.stat().st_size, "all_frames_identical": bool(const),
            "frames_skipped": bad}


def raw_finite(result):
    ok = True
    for fr in (result.raw[0], result.raw[-1]):
        arrs = fr if isinstance(fr, tuple) else (fr,)
        for a in arrs:
            a = np.asarray(a)
            if a.dtype.kind == "f" and not np.isfinite(a).all():
                ok = False
    vel = result.hints.get("vel")
    if isinstance(vel, list) and vel:
        for a in vel[-1]:
            if not np.isfinite(np.asarray(a)).all():
                ok = False
    return ok


def jsonable(x):
    if isinstance(x, dict):
        return {str(k): jsonable(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [jsonable(v) for v in x]
    if isinstance(x, (np.floating, float)):
        v = float(x); return v if math.isfinite(v) else None
    if isinstance(x, (np.integer,)):
        return int(x)
    if isinstance(x, np.ndarray):
        return jsonable(x.tolist())
    if isinstance(x, (str, int, bool)) or x is None:
        return x
    return str(x)


def complete_metrics(metrics, series):
    """Add the measurements the app's postproc.metrics() drops, taken from its own series.

    In Funoos 1.3.2 metrics() opens a second if-chain with the particle kind (the speed-limiter
    count), so its later SPH branch never runs and peak and final kinetic energy and the particle
    count are missing. series() computes the same quantities with the same function
    (_sph_energy), so they are read from there. Works on the JSON forms, so finished runs can be
    completed from series.json without solving again.
    """
    ke, n = series.get("kinetic_energy_J_per_m"), series.get("particles")
    if ke and n and "ke_peak" not in metrics:
        ke = [x for x in ke if x is not None]; n = [x for x in n if x is not None]
        if ke and n:
            metrics.update(ke_peak=max(ke), ke_final=ke[-1], particles_final=int(n[-1]))
    return metrics


def metrics_finite(metrics):
    # the app reports NaN for the shedding frequency when no clean peak exists: that is information, not a failure
    return all(isinstance(x, (int, float)) and math.isfinite(x) for k, x in metrics.items() if k != "shedding_frequency_per_step")


def frames_change(views, static=False):
    """The clip must move: catches a solver or renderer stuck on one frame.

    At least one view has to change; a single still view is allowed, because streamlines of a
    steady or frozen flow (the tracer runs on a fixed flow field, a porous sample settles to
    steady Darcy flow) are the same in every frame by construction. A declared do-nothing
    control (cases.EXPECT_STATIC) must instead stay still in every view.
    """
    still = [vw["all_frames_identical"] for vw in views]
    return all(still) if static else not all(still)


def main(cid, runs):
    out = Path(runs) / cid; out.mkdir(parents=True, exist_ok=True)
    case = next(c for c in cases.build() if c["id"] == cid)
    ex, params, scene_key = case["exhibit"], case["params"], case["scene"]
    if os.environ.get("FUNOOS_SMOKE"):                       # pipeline check only: tiny run
        params = dict(params, duration=0.3, **({"resolution": "Low (fast)"} if "resolution" in params else {}))
    s = catalog.scene(scene_key)
    t0 = time.time(); timing = {"threads": os.environ.get("OMP_NUM_THREADS")}
    meta = {"case": {k: v for k, v in case.items() if k != "params"}, "params": params, "ok": False}
    try:
        v = schema.validate(ex, params, allow_outside=False)
        meta["validation"] = {"errors": v.errors, "warnings": v.warnings}
        r = engine.solve_exhibit(ex, params)
        timing["solve_s"] = round(time.time() - t0, 1); t1 = time.time()
        level, notes = r.quality
        meta["result"] = jsonable(r.meta())
        meta["quality"] = {"level": level, "notes": notes}
        series = jsonable(postproc.series(r))
        meta["metrics"] = complete_metrics(jsonable(postproc.metrics(r)), series)
        meta["derived"] = jsonable(schema.derived(ex, params))
        meta["layers"] = jsonable(catalog.scene_layers(scene_key))
        meta["eq"] = engine.META.get(ex, {}).get("eq")
        meta["method_label"] = engine.META.get(ex, {}).get("method", "")
        (out / "series.json").write_text(json.dumps(series))
        plots = []
        for i, (title, svg, explain) in enumerate(postproc.plots_svg(r)):
            f = out / f"plot_{i}.svg"; f.write_text(svg)
            plots.append({"title": title, "file": f.name, "explain": explain})
        meta["plots"] = plots
        timing["diagnostics_s"] = round(time.time() - t1, 1); t2 = time.time()
        cmap = s.get("cmap") or engine.DEFCMAP[r.kind]
        meta["cmap"] = cmap
        views = []
        poster_at = cases.POSTER_AT.get(case["experiment"], cases.POSTER_AT_DEFAULT)
        for view in r.views:
            sl = _slug(view)
            views.append(encode(r, view, cmap, out / f"{sl}.mp4", out / f"{sl}.webp", poster_at))
        meta["views"] = views
        timing["render_s"] = round(time.time() - t2, 1)
        checks = {
            "solver_finished": True,
            "fields_finite": raw_finite(r),
            "quality_not_incomplete": level != "incomplete",
            "metrics_finite": metrics_finite(meta["metrics"]),
            "clips_written": all(vw["bytes"] > 0 for vw in views),
            "frames_change": frames_change(views, case.get("static")),
            "no_frames_skipped": all(vw["frames_skipped"] == 0 for vw in views),
            "validation_clean": not v.errors and not v.warnings,
        }
        checks["all"] = all(checks.values())
        meta["checks"] = checks; meta["ok"] = True
    except Exception as e:                                   # noqa: BLE001
        meta["error"] = f"{type(e).__name__}: {e}"; meta["traceback"] = traceback.format_exc()[-3000:]
        meta["checks"] = {"solver_finished": False, "all": False}
    timing["total_s"] = round(time.time() - t0, 1); meta["timing"] = timing
    (out / "meta.json").write_text(json.dumps(meta, indent=1, ensure_ascii=False))
    print(json.dumps({"id": cid, "ok": meta["ok"], "checks": meta["checks"].get("all"), **timing}), flush=True)
    return 0 if meta["ok"] else 1


def reposter(runs):
    """Re-cut the posters of finished runs at cases.POSTER_AT from their clips (no solving)."""
    import io
    from PIL import Image
    n = 0
    for m in sorted(Path(runs).glob("*/meta.json")):
        d = json.loads(m.read_text())
        frac = cases.POSTER_AT.get(d["case"].get("experiment"), cases.POSTER_AT_DEFAULT)
        if not d.get("ok") or all(v.get("poster_at", cases.POSTER_AT_DEFAULT) == frac for v in d["views"]):
            continue
        for v in d["views"]:
            t = int(frac * (v["frames"] - 1)) / FPS
            png = subprocess.run([render._ffmpeg(), "-v", "error", "-ss", f"{t:.3f}", "-i", str(m.parent / v["mp4"]), "-frames:v", "1",
                                  "-f", "image2pipe", "-vcodec", "png", "-"], capture_output=True, check=True).stdout
            Image.open(io.BytesIO(png)).convert("RGB").save(m.parent / v["poster"], "WEBP", quality=82, method=6)
            v["poster_at"] = frac
        m.write_text(json.dumps(d, indent=1, ensure_ascii=False)); n += 1
    print(f"posters re-cut for {n} runs")


if __name__ == "__main__":
    if sys.argv[1] == "--posters":
        reposter(sys.argv[2]); sys.exit(0)
    sys.exit(main(sys.argv[1], sys.argv[2]))
