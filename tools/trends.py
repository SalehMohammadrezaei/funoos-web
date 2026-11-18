"""Cross-case trend checks on the finished runs, written as CHECKS.md.

    python tools/trends.py <runs directory> [CHECKS.md]

Per-case checks (finite fields, finished solver, clips) are made by run_case.py; this script
reads them back and adds the physics trends across each sweep. A failed trend is reported,
not hidden; it does not block the site.
"""
import json, math, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import cases  # noqa: E402


def load(runs):
    out = {}
    for m in Path(runs).glob("*/meta.json"):
        d = json.loads(m.read_text()); out[d["case"]["id"]] = d
    return out


def monotone(vals, increasing=True, tol=0.0):
    return all((b - a) >= -tol * max(abs(a), abs(b), 1e-300) if increasing else (a - b) >= -tol * max(abs(a), abs(b), 1e-300)
               for a, b in zip(vals, vals[1:]))


def main(runs_dir, out_md):
    runs = load(runs_dir); lib = {c["id"]: c for c in cases.build()}
    lines = ["# Checks of the pre-run library", ""]
    n_ok = sum(1 for d in runs.values() if d.get("ok") and d["checks"].get("all"))
    n_fail = [cid for cid, d in runs.items() if not d.get("ok") or not d["checks"].get("all")]
    lines += [f"Cases run: {len(runs)} of {len(lib)}. Passing every per-case check: {n_ok}. Failing: {len(n_fail)}.", ""]
    if n_fail:
        lines.append("## Cases with a failed per-case check")
        for cid in sorted(n_fail):
            d = runs[cid]; bad = [k for k, v in d.get("checks", {}).items() if v is False and k != "all"]
            lines.append(f"- `{cid}`: {d.get('error', '')} {bad}")
        lines.append("")
    lines += ["## Solver quality notes", "Cases the solver itself marked as not fully quantitative, with its reason.", ""]
    for cid in sorted(runs):
        q = runs[cid].get("quality", {})
        if q.get("level") and q["level"] != "quantitative":
            lines.append(f"- `{cid}` ({q['level']}): " + "; ".join(q.get("notes", [])))
    lines.append("")

    def sweep(exp, sweep_name, key):
        rows = []
        for cid, c in lib.items():
            if c["experiment"] == exp and c["sweep"] == sweep_name and cid in runs and runs[cid].get("ok"):
                rows.append((c["overrides"], runs[cid]["metrics"].get(key)))
        return rows

    results = []

    def check(name, ok, detail):
        results.append((name, ok, detail))

    # Cylinder: Strouhal 0 at Re 40, within 0.15 to 0.25 for Re 180 to 1200
    rows = {o["reynolds"]: v for o, v in sweep("cylinder_wake", "Reynolds number", "strouhal")}
    if rows:
        st = {re: rows.get(re) for re in sorted(rows)}
        ok = (st.get(40) is None or st[40] < 0.05) and all(0.15 <= (st.get(re) or 0) <= 0.26 for re in (180, 400, 1200) if re in st)
        check("Cylinder: no shedding at Re 40, Strouhal 0.15 to 0.26 at Re 180 to 1200", ok, {k: None if v is None else round(v, 3) for k, v in st.items()})
    # Airfoil: cl sign follows the angle, monotone up to 14 degrees
    rows = {o["angle"]: v for o, v in sweep("airfoil_lift", "Angle of attack", "cl_circulation")}
    if rows:
        angs = sorted(a for a in rows if abs(a) <= 14)
        ok = monotone([rows[a] for a in angs], True) and all((rows[a] > 0) == (a > 0) for a in angs if a != 0)
        check("Airfoil: lift coefficient monotone in angle up to 14 degrees and changes sign through 0", ok, {a: round(rows[a], 3) for a in sorted(rows)})
    # Porous: k increases with porosity at fixed grain and with grain at fixed porosity
    rows = sweep("porous_flow", "Porosity and grain size", "permeability_cells2")
    if rows:
        byg = {}; byp = {}
        for o, v in rows:
            byg.setdefault(o["grain"], {})[o["porosity"]] = v; byp.setdefault(o["porosity"], {})[o["grain"]] = v
        ok1 = all(monotone([d[p] for p in sorted(d)], True) for d in byg.values())
        ok2 = all(monotone([d[g] for g in sorted(d)], True) for d in byp.values())
        check("Porous flow: permeability rises with porosity at fixed grain size", ok1, {g: {p: f"{v:.3g}" for p, v in sorted(d.items())} for g, d in byg.items()})
        check("Porous flow: permeability rises with grain size at fixed porosity", ok2, "")
    # Tracer: mass balance, dispersion ratio rises with Pe (pulse)
    rows = [(o, runs[cid]["metrics"]) for cid, c in lib.items() if c["experiment"] == "tracer_transport" and cid in runs and runs[cid].get("ok") for o in [c["overrides"]]]
    if rows:
        mb = max(m.get("tracer_mass_balance", 0) for _o, m in rows)
        check("Tracer: mass balance closes within 2 % in every case", mb < 0.02, f"worst {mb:.2e}")
        pulse = sorted((o["peclet"], m.get("dispersion_over_molecular")) for o, m in rows if o.get("injection") == "Pulse" and m.get("dispersion_over_molecular") is not None)
        if len(pulse) > 1:
            check("Tracer: dispersion over molecular diffusion rises with the Peclet number (pulse)", monotone([v for _p, v in pulse], True, 0.05), {p: round(v, 2) for p, v in pulse})
    # Heated layer: Nu about 1 below onset, rising with buoyancy at fixed viscosity
    rows = sweep("heated_layer", "Buoyancy and viscosity (Rayleigh number)", "nusselt")
    if rows:
        bynu = {}
        for o, v in rows:
            bynu.setdefault(o["viscosity"], {})[o["buoyancy"]] = v
        cond = [d.get(0.0) for d in bynu.values() if d.get(0.0) is not None]
        check("Heated layer: Nusselt number 1 (within 5 %) with buoyancy off", all(abs(v - 1) < 0.05 for v in cond), [round(v, 3) for v in cond])
        ok = all(monotone([d[b] for b in sorted(d)], True, 0.02) for d in bynu.values())
        check("Heated layer: Nusselt number rises with buoyancy at fixed viscosity", ok, {nu: {b: round(v, 2) for b, v in sorted(d.items())} for nu, d in bynu.items()})
    # RT: mixing width grows with Atwood at fixed modes
    rows = sweep("rayleigh_taylor", "Atwood number and modes", "mixing_width_final_frac")
    if rows:
        bym = {}
        for o, v in rows:
            bym.setdefault(o["modes"], {})[o["atwood"]] = v
        ok = all(monotone([d[a] for a in sorted(d)], True, 0.05) for d in bym.values())
        check("Rayleigh-Taylor: final mixing width grows with the Atwood number at fixed mode", ok, {m: {a: round(v, 3) for a, v in sorted(d.items())} for m, d in bym.items()})
    # Smoke, flame, chimney: kinetic energy rises with buoyancy at fixed second parameter
    for exp, sw, other in (("rising_smoke", "Buoyancy and confinement", "confinement"), ("candle_flame", "Stoichiometric mixture fraction and buoyancy", "zst"), ("chimney_plume", "Wind and buoyancy", "wind")):
        rows = sweep(exp, sw, "ke_final")
        if rows:
            by = {}
            for o, v in rows:
                by.setdefault(o[other], {})[o["buoyancy"]] = v
            ok = all(monotone([d[b] for b in sorted(d)], True, 0.02) for d in by.values())
            check(f"{exp}: final kinetic energy rises with buoyancy at fixed {other}", ok, {k: {b: f"{v:.3g}" for b, v in sorted(d.items())} for k, d in by.items()})
    # Sod: error falls with resolution
    rows = {o["resolution"]: v for o, v in sweep("sod_tube", "Resolution", "sod_err_rho")}
    if rows:
        order = ["Low (fast)", "Medium", "High", "Ultra (slow)"]
        vals = [rows[r] for r in order if r in rows]
        check("Sod tube: density error against the exact solution falls with resolution", monotone(vals, False), {r: round(rows[r], 5) for r in order if r in rows})
    # Blast: shock radius rises with pressure
    rows = {o["pressure"]: v for o, v in sweep("open_blast", "Pressure ratio", "shock_radius_final_cells")}
    if rows:
        check("Open blast: final shock radius rises with the pressure ratio", monotone([rows[p] for p in sorted(rows)], True), {p: round(v, 1) for p, v in sorted(rows.items())})
    # Shock bubble: ke rises with Mach at fixed density ratio
    rows = sweep("shock_bubble", "Mach number and density ratio", "ke_final")
    if rows:
        by = {}
        for o, v in rows:
            by.setdefault(o["densratio"], {})[o["mach"]] = v
        ok = all(monotone([d[m] for m in sorted(d)], True) for d in by.values())
        check("Shock-bubble: final kinetic energy rises with the Mach number at fixed density ratio", ok, {r: {m: f"{v:.3g}" for m, v in sorted(d.items())} for r, d in by.items()})
    # SPH: still water never trips the limiter
    rows = {o["particles"]: v for o, v in sweep("still_water", "Particle count", "speed_limiter_events")}
    if rows:
        check("Still water: zero speed-limiter events at every particle count", all(v == 0 for v in rows.values()), rows)
    # Dam break: peak KE rises with height at fixed width
    rows = sweep("dam_break", "Column width and height", "ke_peak")
    if rows:
        by = {}
        for o, v in rows:
            by.setdefault(o["width"], {})[o["height"]] = v
        ok = all(monotone([d[h] for h in sorted(d)], True) for d in by.values())
        check("Dam break: peak kinetic energy rises with column height at fixed width", ok, {w: {h: f"{v:.3g}" for h, v in sorted(d.items())} for w, d in by.items()})
    # KH and decay: final enstrophy falls with viscosity
    for exp, sw in (("kelvin_helmholtz", "Viscosity and layer thickness"), ("decaying_turbulence", "Viscosity")):
        rows = sweep(exp, sw, "enstrophy_final")
        if rows:
            by = {}
            for o, v in rows:
                by.setdefault(o.get("thickness", 0), {})[o["viscosity"]] = v
            ok = all(monotone([d[n] for n in sorted(d)], False) for d in by.values())
            check(f"{exp}: final enstrophy falls with viscosity", ok, {t: {n: f"{v:.3g}" for n, v in sorted(d.items())} for t, d in by.items()})
    # Taylor-Green: KE decay matches exp(-4 nu t) : ke_final/ke_initial vs exact
    tg = [(o, runs[cid]) for cid, c in lib.items() if c["experiment"] == "taylor_green" and c["sweep"] == "Viscosity" and cid in runs and runs[cid].get("ok") for o in [c["overrides"]]]
    if tg:
        det = {}
        ok = True
        for o, d in tg:
            m = d["metrics"]; t = d["result"]["times"][-1] if d["result"].get("times") else None
            if m.get("ke_initial") and t is not None:
                ratio = m["ke_final"] / m["ke_initial"]; exact = math.exp(-4 * o["viscosity"] * t)
                rel = abs(ratio - exact) / exact; det[o["viscosity"]] = f"ratio {ratio:.4f} exact {exact:.4f} rel err {rel:.2e}"
                ok = ok and rel < 0.05
        check("Taylor-Green: kinetic-energy decay within 5 % of exp(-4 nu t)", ok, det)
    # Dye: final variance falls with diffusion at fixed stir, and with stir at fixed diffusion
    rows = sweep("dye_transport", "Stirring and diffusion", "dye_variance_final")
    if rows:
        bys = {}; byd = {}
        for o, v in rows:
            bys.setdefault(o["stir"], {})[o["diffusion"]] = v; byd.setdefault(o["diffusion"], {})[o["stir"]] = v
        check("Dye: final variance falls with diffusion at fixed stirring", all(monotone([d[k] for k in sorted(d)], False, 0.01) for d in bys.values()), {s: {k: f"{v:.3g}" for k, v in sorted(d.items())} for s, d in bys.items()})
        check("Dye: final variance falls with stirring at fixed diffusion", all(monotone([d[k] for k in sorted(d)], False, 0.01) for d in byd.values()), "")
    # Gray-Scott: every regime keeps a pattern (coverage strictly between 0 and 100)
    rows = {o["pattern"]: v for o, v in sweep("gray_scott", "Pearson regime", "pattern_coverage_pct")}
    if rows:
        check("Gray-Scott: every named regime ends with a pattern (coverage between 1 % and 99 %)", all(1 < v < 99 for v in rows.values()), {k: round(v, 1) for k, v in rows.items()})

    lines += ["## Trend checks across the sweeps", ""]
    for name, ok, detail in results:
        lines.append(f"- {'PASS' if ok else 'FAIL'}: {name}")
        if detail:
            lines.append(f"  - {json.dumps(detail, ensure_ascii=False) if not isinstance(detail, str) else detail}")
    lines.append("")
    Path(out_md).write_text("\n".join(lines))
    print("\n".join(l for l in lines if l.startswith(("- PASS", "- FAIL", "Cases run"))))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "CHECKS.md")
