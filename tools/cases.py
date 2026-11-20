"""The case library of the Funoos web version.

Every case is one solver run: a scene (one of the 51 presets of the desktop app) plus the
parameter overrides of the sweep it belongs to. Resolution is High and duration 1.8 for every
case, the gallery settings of the app. All 51 presets are included unchanged; the sweeps add
the physically meaningful values listed in PLAN.md. Where two parameters interact the full
grid is run so every offered combination exists.

    python tools/cases.py          # list, validate, count
"""
import itertools, json, sys
from pathlib import Path

FUNOOS = Path("/mnt/d/Saleh/Funoos_dev")
sys.path.insert(0, str(FUNOOS))
from flowzoo import catalog, engine, schema  # noqa: E402

RESOLUTION, DURATION = "High", 1.8

# experiment id -> list of (sweep name, [parameter names], list of value tuples)
# Values are applied on top of the representative preset of the experiment.
SWEEPS = {
    "cylinder_wake": [("Reynolds number", ["reynolds"], [(40,), (80,), (180,), (400,), (1200,)]),
                      ("Shape at Re 180", ["obstacle"], [("Square",), ("Diamond",)])],
    "airfoil_lift": [("Angle of attack", ["angle"], [(-14,), (-6,), (0,), (6,), (14,), (20,)])],
    "cycling_drafting": [("Reynolds number", ["reynolds"], [(200,), (500,), (1000,)])],
    "flow_text": [("Reynolds number", ["reynolds"], [(60,), (220,), (800,)])],
    "car_silhouette": [("Reynolds number", ["reynolds"], [(40,), (320,), (1200,)])],
    "porous_flow": [("Porosity and grain size", ["porosity", "grain"],
                     list(itertools.product([0.45, 0.6, 0.75, 0.85], [0.02, 0.035, 0.07])))],
    "tracer_transport": [("Peclet number and injection", ["peclet", "injection"],
                          list(itertools.product([0.5, 2.0, 20.0, 100.0, 400.0], ["Pulse", "Continuous supply"])))],
    "rising_smoke": [("Buoyancy and confinement", ["buoyancy", "confinement"],
                      list(itertools.product([0.001, 0.0022, 0.005], [0, 7, 18])))],
    "rayleigh_taylor": [("Atwood number and modes", ["atwood", "modes"],
                         list(itertools.product([0.2, 0.5, 0.7, 1.0], [0, 3])))],
    "candle_flame": [("Stoichiometric mixture fraction and buoyancy", ["zst", "buoyancy"],
                      list(itertools.product([0.10, 0.16, 0.25], [0.012, 0.025])))],
    # Every nonzero buoyancy is far above onset (Ra 1e9 to 1e11 in grid units at High), so buoyancy
    # sets the look (onset time, regular columns or turbulence). Viscosity over its whole slider range
    # (0.0002 to 0.0015, Prandtl << 1) leaves the clips identical, so it is not swept; the thermal
    # diffusivity sets how sharp the plumes are, so it is.
    "heated_layer": [("Buoyancy (Rayleigh number)", ["buoyancy"], [(0.0,), (0.0015,), (0.003,), (0.006,), (0.012,)]),
                     ("Thermal diffusivity at buoyancy 0.006", ["kappa"], [(0.005,), (0.02,), (0.1,)])],
    "chimney_plume": [("Wind and buoyancy", ["wind", "buoyancy"],
                       list(itertools.product([0.0, 0.15, 0.3, 0.55], [0.002, 0.005, 0.01])))],
    "sod_tube": [("Resolution", ["resolution"], [("Low (fast)",), ("Medium",), ("High",), ("Ultra (slow)",)])],
    "open_blast": [("Pressure ratio", ["pressure"], [(20.0,), (50.0,), (140.0,), (400.0,)])],
    "blast_obstacles": [("Pressure ratio", ["pressure"], [(50.0,), (160.0,), (400.0,)]),
                        ("Charge size at pressure 160", ["charge"], [(0.03,), (0.12,)])],
    "shock_bubble": [("Mach number and density ratio", ["mach", "densratio"],
                      list(itertools.product([1.2, 1.6, 2.5], [0.14, 0.5, 3.0])))],
    "still_water": [("Particle count", ["particles"], [(600,), (3000,), (12000,)])],
    "dam_break": [("Column width and height", ["width", "height"], list(itertools.product([0.5, 1.0, 2.0], [1.0, 2.0, 3.0])))],
    "blob_impact": [("Blob size and drop height", ["dropsize", "dropheight"], list(itertools.product([0.2, 0.4, 0.8], [0.5, 0.9])))],
    "sloshing": [("Forcing period and amplitude", ["sloshT", "sloshA"], list(itertools.product([0.6, 1.1, 2.0], [0.3, 0.7, 1.5])))],
    "pouring": [("Jet speed and spout width", ["pourv", "spout"], list(itertools.product([0.5, 1.4, 3.0], [0.025, 0.09])))],
    "wave_tank": [("Wave amplitude and period", ["waveA", "waveT"], list(itertools.product([0.15, 0.4, 0.8], [0.5, 0.9, 1.8])))],
    "floating_hull": [("Hull size and wave amplitude", ["shipsz", "waveA"], list(itertools.product([0.5, 1.0, 1.8], [0.2, 0.6])))],
    "kelvin_helmholtz": [("Viscosity and layer thickness", ["viscosity", "thickness"],
                          list(itertools.product([1e-5, 8e-5, 4e-4], [0.015, 0.0333333, 0.08])))],
    "decaying_turbulence": [("Viscosity", ["viscosity"], [(1e-5,), (8e-5,), (4e-4,)]),
                            ("Another realisation", ["seed"], [(2,)])],
    # Taylor-Green keeps its shape and only decays (by 0.2 to 8 % of its energy over the slider's
    # viscosity range), so its sweep is read in the decay plot, not the clip; the scene ignores
    # the perturbation parameter, so that is not swept.
    "taylor_green": [("Viscosity", ["viscosity"], [(1e-5,), (1e-4,), (4e-4,)])],
    # diffusion 1e-4 looks the same as none at this resolution; 3e-4 is the smallest that shows
    "dye_transport": [("Stirring and diffusion", ["stir", "diffusion"], list(itertools.product([0.0, 0.3, 1.0], [0.0, 3e-4, 1e-3]))),
                      ("Number of bands", ["bands"], [(2,), (14,)])],
    "gray_scott": [("Pearson regime", ["pattern"], [("Spots",), ("Stripes",), ("Maze",), ("Mitosis",), ("Coral",), ("Waves",)]),
                   ("Custom feed and kill rate", ["pattern", "F", "k"], [("Custom", F, k) for F, k in itertools.product([0.03, 0.055], [0.06, 0.065])])],
}


# Controls in which nothing is supposed to move: the clip is expected to be a still image, so the
# per-case check that frames change over time does not apply to them.
EXPECT_STATIC = {"dye_transport": {"stir": 0.0, "diffusion": 0.0}}

# Where in the clip the poster frame is taken (fraction of the run; default POSTER_AT_DEFAULT).
# The poster is what the gallery and the page show before playing, so it should catch the event:
# the blob hits the water early, and a tracer pulse has mostly left the sample by 70 %. Rayleigh-
# Taylor fills the box with the same well-mixed state at every Atwood number by mid-run, and the
# heated layer settles into the same stirred convection at every buoyancy; their differences
# (finger length, onset time) show early.
POSTER_AT_DEFAULT = 0.7
POSTER_AT = {"blob_impact": 0.25, "tracer_transport": 0.3, "rayleigh_taylor": 0.3, "heated_layer": 0.12}


def full_params(scene_key, overrides=None):
    s = catalog.scene(scene_key)
    p = {q["name"]: q["default"] for q in engine.EXHIBITS[s["exhibit"]]["params"]}
    p.update(s["preset"]); p.update(overrides or {})
    if "resolution" in p and "resolution" not in (overrides or {}):
        p["resolution"] = RESOLUTION
    if "duration" in p:
        p["duration"] = DURATION
    return p


def _slug(v):
    if isinstance(v, (int, float)) and not isinstance(v, bool):  # -6 -> m6, so that -6 and 6 stay distinct
        s = f"{v:g}".replace("-", "m").replace(".", "p").replace("+", "")
    else:
        s = "".join(c if c.isalnum() else "_" for c in str(v)).strip("_").lower()
    return s


def build():
    """Return the list of cases: dicts with id, experiment, scene, sweep, overrides, params."""
    cases, seen = [], {}

    def add(exp_id, scene_key, sweep, names, values, label):
        ov = dict(zip(names, values)) if names else {}
        params = full_params(scene_key, ov)
        # numbers by value: a preset's 140 and a sweep's 140.0 are the same setup
        norm = {k: float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else v for k, v in params.items()}
        sig = (catalog.scene(scene_key)["exhibit"], json.dumps(norm, sort_keys=True))
        if sig in seen:                                  # same physics already in the library
            seen[sig]["aliases"].append({"scene": scene_key, "sweep": sweep, "label": label, "overrides": ov})
            return
        parts = [exp_id] + [f"{n}_{_slug(v)}" for n, v in zip(names, values)] if names else [exp_id, scene_key]
        cid = "__".join(parts)
        static = exp_id in EXPECT_STATIC and all(ov.get(k) == v for k, v in EXPECT_STATIC[exp_id].items())
        c = {"id": cid, "experiment": exp_id, "scene": scene_key, "exhibit": sig[0], "sweep": sweep,
             "overrides": ov, "label": label, "params": params, "aliases": [], "static": static}
        seen[sig] = c; cases.append(c)

    for e in catalog.EXPERIMENTS:
        rep = e["representative"]
        for key, label in e["presets"]:                 # every preset of the app, unchanged
            add(e["id"], key, "Presets of the app", [], (), label)
        for sweep, names, grid in SWEEPS.get(e["id"], []):
            for values in grid:
                label = ", ".join(f"{n} = {v}" for n, v in zip(names, values))
                add(e["id"], rep, sweep, names, values, label)
    return cases


def validate_all(cases):
    bad = []
    for c in cases:
        v = schema.validate(c["exhibit"], c["params"], allow_outside=False)
        if v.errors or v.warnings:
            bad.append((c["id"], v.errors, v.warnings))
    return bad


if __name__ == "__main__":
    cases = build()
    bad = validate_all(cases)
    by_exp = {}
    for c in cases:
        by_exp.setdefault(c["experiment"], []).append(c)
    for k, v in by_exp.items():
        print(f"{k:22s} {len(v):3d}")
    print("total", len(cases), "aliases", sum(len(c["aliases"]) for c in cases))
    for cid, e, w in bad:
        print("PROBLEM", cid, e, w)
    if not bad:
        print("all cases pass schema.validate with no warnings")
