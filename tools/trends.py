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
        d = json.loads(m.read_text()); d["_dir"] = m.parent; out[d["case"]["id"]] = d
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

    def points(exp, sweep_name=None):
        """(overrides, run) for every finished point of a sweep, including the points that equal
        a preset: those are stored once, as the preset, with the sweep point as an alias."""
        out = []
        for cid, c in lib.items():
            if c["experiment"] != exp or cid not in runs or not runs[cid].get("ok"):
                continue
            if sweep_name is None or c["sweep"] == sweep_name:
                out.append((c["overrides"], runs[cid]))
            out += [(al["overrides"], runs[cid]) for al in c["aliases"] if al["sweep"] == sweep_name]
        return out

    def sweep(exp, sweep_name, key):
        return [(o, d["metrics"].get(key)) for o, d in points(exp, sweep_name)]

    def series(d, key):
        return [x for x in json.loads((d["_dir"] / "series.json").read_text()).get(key, []) if x is not None]

    def late_mean(d, key):
        """Mean over the second half of the run: a turbulent plume's kinetic energy fluctuates, so a
        single final frame does not rank cases."""
        v = series(d, key); v = v[len(v) // 2:]
        return sum(v) / len(v) if v else None

    results = []

    def check(name, ok, detail):
        results.append((name, ok, detail))

    # Cylinder: steady wake at Re 40 (below onset at about 47), sustained shedding above, Strouhal
    # 0.15 to 0.26 for Re 180 to 1200. The app's Strouhal readout also reports the frequency of a
    # decaying start-up oscillation, so "steady" is judged from the cross-stream probe: its swing
    # in the last quarter of the run against the first.
    pts = {o["reynolds"]: d for o, d in points("cylinder_wake", "Reynolds number")}
    if pts:
        def decay(d):
            uy = [x for x in json.loads((d["_dir"] / "series.json").read_text()).get("probe_uy", []) if x is not None]
            q = len(uy) // 4
            return (max(uy[-q:]) - min(uy[-q:])) / max(max(uy[:q]) - min(uy[:q]), 1e-30) if q else None
        dec = {re: decay(d) for re, d in sorted(pts.items())}
        st = {re: d["metrics"].get("strouhal") for re, d in sorted(pts.items())}
        ok = all(v is not None and (v < 0.2 if re < 47 else v > 0.5) for re, v in dec.items())
        check("Cylinder: wake oscillation dies out below Re 47 and is sustained above (last-quarter swing over first)", ok, {re: round(v, 3) for re, v in dec.items() if v is not None})
        ok = all(0.15 <= (st.get(re) or 0) <= 0.26 for re in st if re >= 180)
        check("Cylinder: Strouhal number 0.15 to 0.26 for Re 180 to 1200", ok, {re: None if v is None else round(v, 3) for re, v in st.items()})
    # Airfoil: cl sign follows the angle, monotone up to 14 degrees
    rows = {o["angle"]: v for o, v in sweep("airfoil_lift", "Angle of attack", "cl_circulation")}
    if rows:
        angs = sorted(a for a in rows if abs(a) <= 14)
        ok = monotone([rows[a] for a in angs], True) and all((rows[a] > 0) == (a > 0) for a in angs if a != 0)
        check("Airfoil: lift coefficient monotone in angle up to 14 degrees and changes sign through 0", ok, {a: round(rows[a], 3) for a in sorted(rows)})
        # a symmetric section: C_l(-a) = -C_l(a); a solver or measurement asymmetry shows up here
        pairs = {a: (rows[a] + rows[-a]) / max(abs(rows[a]), 1e-9) for a in sorted(rows) if a > 0 and -a in rows}
        if pairs:
            check("Airfoil: lift antisymmetric in angle, |C_l(a) + C_l(-a)| within 5 % of |C_l(a)|", all(abs(v) < 0.05 for v in pairs.values()),
                  {a: f"{100 * v:+.1f} %" for a, v in pairs.items()})
    # Porous: k increases with porosity at fixed grain and with grain at fixed porosity
    rows = sweep("porous_flow", "Porosity and grain size", "permeability_cells2")
    if rows:
        byg = {}; byp = {}
        for o, v in rows:
            byg.setdefault(o["grain"], {})[o["porosity"]] = v; byp.setdefault(o["porosity"], {})[o["grain"]] = v
        ok1 = all(monotone([d[p] for p in sorted(d)], True) for d in byg.values())
        ok2 = all(monotone([d[g] for g in sorted(d)], True) for d in byp.values())
        check("Porous flow: permeability rises with porosity at fixed grain size", ok1, {g: {p: f"{v:.3g}" for p, v in sorted(d.items())} for g, d in byg.items()})
        check("Porous flow: permeability rises with grain size at fixed porosity", ok2, {p: {g: f"{v:.3g}" for g, v in sorted(d.items())} for p, d in sorted(byp.items())})
    # Tracer: mass balance, dispersion ratio rises with Pe (pulse)
    rows = [(o, d["metrics"]) for o, d in points("tracer_transport")]
    rows += [(o, d["metrics"]) for o, d in points("tracer_transport", "Peclet number and injection") if o not in [r[0] for r in rows]]
    if rows:
        mb = max(m.get("tracer_mass_balance", 0) for _o, m in rows)
        check("Tracer: mass balance closes within 2 % in every case", mb < 0.02, f"worst {mb:.2e}")
        pulse = sorted((o["peclet"], m.get("dispersion_over_molecular")) for o, m in rows if o.get("injection") == "Pulse" and m.get("dispersion_over_molecular") is not None)
        if len(pulse) > 1:
            check("Tracer: dispersion over molecular diffusion rises with the Peclet number (pulse)", monotone([v for _p, v in pulse], True, 0.05), {p: round(v, 2) for p, v in pulse})
    # Heated layer: Nu about 1 below onset, rising with buoyancy at fixed viscosity
    # The app's Nusselt readout is taken from the final frame alone, which in turbulent convection
    # fluctuates; the kinetic energy is judged as a second-half mean.
    pts = sorted(((o["buoyancy"], d) for o, d in points("heated_layer", "Buoyancy (Rayleigh number)")), key=lambda x: x[0])
    if pts:
        nu = {b: d["metrics"].get("nusselt") for b, d in pts}
        check("Heated layer: Nusselt number 1 (within 5 %) with buoyancy off", nu.get(0.0) is not None and abs(nu[0.0] - 1) < 0.05, round(nu.get(0.0) or 0, 3))
        check("Heated layer: Nusselt number (final-frame readout of the app) rises with buoyancy", monotone(list(nu.values()), True, 0.02),
              {b: round(v, 2) for b, v in nu.items()})
        ke = {b: late_mean(d, "kinetic_energy_per_mass") for b, d in pts}
        check("Heated layer: kinetic energy (mean of the second half) rises with buoyancy", monotone(list(ke.values()), True, 0.02),
              {b: f"{v:.3g}" for b, v in ke.items()})
    # RT: by the end of the run the mixing zone fills the box at every Atwood number, so the final
    # width cannot rank them. The time the zone takes to reach half the box can: the linear growth
    # rate sqrt(A g k) and the self-similar h = alpha A g t^2 both make it scale as A^(-1/2).
    pts = points("rayleigh_taylor", "Atwood number and modes")
    if pts:
        def t_half(d):
            t, w = series(d, "time"), series(d, "mixing_width_frac")
            return next((ti for ti, wi in zip(t, w) if wi >= 0.5), None)
        bym = {}
        for o, d in pts:
            bym.setdefault(o["modes"], {})[o["atwood"]] = t_half(d)
        ok = all(None not in d.values() for d in bym.values())
        dev = {}
        for m, d in bym.items():
            a0 = min(d)
            for a, t in d.items():
                if t is not None and d[a0] is not None:
                    dev[(m, a)] = abs(t / (d[a0] * math.sqrt(a0 / a)) - 1)
        ok = ok and all(monotone([d[a] for a in sorted(d)], False) for d in bym.values()) and max(dev.values()) < 0.1
        check("Rayleigh-Taylor: time for the mixing zone to reach half the box scales as A^(-1/2) (within 10 %)", ok,
              {"time to half width, by modes then Atwood": {m: {a: t for a, t in sorted(d.items())} for m, d in bym.items()},
               "worst deviation from A^(-1/2)": round(max(dev.values()), 3) if dev else None})
    # Smoke, flame, chimney: kinetic energy rises with buoyancy at fixed second parameter
    # Mean over the second half of the run, not the final frame (see late_mean). In a crosswind the
    # kinetic energy is mostly the wind's own, so the chimney is judged in calm air; the windy rows
    # are listed for information.
    for exp, sw, other, judged in (("rising_smoke", "Buoyancy and confinement", "confinement", None),
                                   ("candle_flame", "Stoichiometric mixture fraction and buoyancy", "zst", None),
                                   ("chimney_plume", "Wind and buoyancy", "wind", 0.0)):
        pts = points(exp, sw)
        if pts:
            by = {}
            for o, d in pts:
                by.setdefault(o[other], {})[o["buoyancy"]] = late_mean(d, "kinetic_energy_per_mass")
            rows = {k: d for k, d in by.items() if judged is None or k == judged}
            ok = all(monotone([d[b] for b in sorted(d)], True, 0.02) for d in rows.values())
            where = f"at fixed {other}" if judged is None else f"in calm air ({other} {judged:g})"
            check(f"{exp}: kinetic energy (mean of the second half) rises with buoyancy {where}", ok,
                  {k: {b: f"{v:.3g}" for b, v in sorted(d.items())} for k, d in sorted(by.items())})
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
    tg = points("taylor_green", "Viscosity")
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
