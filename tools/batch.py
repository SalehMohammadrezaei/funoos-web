"""Batch driver: runs the case library through run_case.py with a thread budget.

    python tools/batch.py <runs directory> [--only id1,id2] [--budget 176] [--smoke]

Each case is a separate process. Native solvers get 8 threads (incompressible Navier-Stokes
12), the Python solvers 2. Cases with a finished, passing meta.json are skipped, so the batch
can be restarted. Progress goes to <runs>/batch.log as one JSON line per finished case.
"""
import argparse, json, os, subprocess, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import cases  # noqa: E402

PY = sys.executable
NS = {"Rising Smoke", "Mushroom Clouds", "Candle Flame", "Rayleigh-Benard", "Chimney Plume"}
NATIVE = {"Wind Tunnel", "Porous Flow", "Detonation", "Shock Tube", "Shockwave Strike", "The Big Splash"}
COST = {"Chimney Plume": 5, "Rising Smoke": 4, "Mushroom Clouds": 4, "Rayleigh-Benard": 3, "Candle Flame": 2,
        "Cloud Billows": 1, "Ink in Motion": 1, "Tracer in Rock": 1}       # ordering only: long jobs first


def threads_for(exhibit):
    if exhibit in NS:
        return 12
    if exhibit in NATIVE:
        return 8
    return 2


def done(run_dir):
    m = run_dir / "meta.json"
    if not m.exists():
        return False
    try:
        return json.loads(m.read_text()).get("ok", False)
    except Exception:                                   # noqa: BLE001
        return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("runs"); ap.add_argument("--only", default=""); ap.add_argument("--budget", type=int, default=176)
    ap.add_argument("--smoke", action="store_true"); ap.add_argument("--timeout", type=float, default=6 * 3600)
    a = ap.parse_args()
    runs = Path(a.runs); runs.mkdir(parents=True, exist_ok=True)
    log = open(runs / "batch.log", "a")
    todo = cases.build()
    if a.only:
        keep = set(a.only.split(",")); todo = [c for c in todo if c["id"] in keep]
    todo = [c for c in todo if not done(runs / c["id"])]
    todo.sort(key=lambda c: -COST.get(c["exhibit"], 0))
    print(f"{len(todo)} cases to run, thread budget {a.budget}", flush=True)
    running = {}                                         # proc -> (case, threads, t0)
    used = 0; t_batch = time.time(); n_done = 0; n_fail = 0
    while todo or running:
        while todo and (used + threads_for(todo[0]["exhibit"]) <= a.budget or not running):
            c = todo.pop(0); th = threads_for(c["exhibit"])
            env = dict(os.environ, OMP_NUM_THREADS=str(th), OPENBLAS_NUM_THREADS=str(th), MKL_NUM_THREADS=str(th),
                       NUMEXPR_NUM_THREADS=str(th), PYTHONUNBUFFERED="1")
            if a.smoke:
                env["FUNOOS_SMOKE"] = "1"
            (runs / c["id"]).mkdir(parents=True, exist_ok=True)
            err = open(runs / c["id"] / "stderr.txt", "w")
            p = subprocess.Popen([PY, str(HERE / "run_case.py"), c["id"], str(runs)], stdout=subprocess.PIPE,
                                 stderr=err, text=True, env=env)
            running[p] = (c, th, time.time(), err); used += th
            print(time.strftime("%H:%M:%S"), "start", c["id"], f"({th} thr, {len(running)} running, {used} threads)", flush=True)
        time.sleep(5)
        for p in list(running):
            c, th, t0, err = running[p]
            rc = p.poll()
            if rc is None and time.time() - t0 > a.timeout:
                p.kill(); rc = -9
            if rc is None:
                continue
            out = p.stdout.read().strip().splitlines(); err.close()
            rec = {"id": c["id"], "exhibit": c["exhibit"], "threads": th, "wall_s": round(time.time() - t0, 1), "rc": rc}
            try:
                rec.update(json.loads(out[-1]))
            except Exception:                           # noqa: BLE001
                rec["ok"] = False
            log.write(json.dumps(rec) + "\n"); log.flush()
            n_done += 1; n_fail += 0 if rec.get("ok") else 1
            print(time.strftime("%H:%M:%S"), "done ", c["id"], f"{rec['wall_s']:.0f}s", "OK" if rec.get("ok") else "FAILED",
                  f"[{n_done} done, {n_fail} failed, {len(todo)} waiting]", flush=True)
            del running[p]; used -= th
    print(f"batch finished in {(time.time() - t_batch) / 60:.1f} min: {n_done} cases, {n_fail} failed", flush=True)


if __name__ == "__main__":
    main()
