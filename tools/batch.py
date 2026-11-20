"""Batch driver: runs the case library through run_case.py with a thread budget.

    python tools/batch.py <runs directory> [--only id1,id2] [--group all|ns|other] [--budget 176]
                          [--ns-slots 12] [--scratch DIR] [--smoke]

Each case is a separate process. Native solvers get 8 threads, the Python solvers 2. At most
--ns-slots incompressible Navier-Stokes jobs run at once: their pressure solve is limited by
cache and memory bandwidth, and with dozens running together each one slowed down 10 to 20
times (first full batch). Cases with a finished, passing meta.json are skipped, so the batch
can be restarted. Progress goes to <runs>/batch.log as one JSON line per finished case.

Solver scratch (the raw frames, up to about 0.5 GB per job) goes to <runs>/_scratch/<case id>
through TMPDIR, not /tmp: the home disk is nearly full and the first batch lost 156 runs to it.
No job starts while the scratch disk has less than MIN_FREE_GB free.
"""
import argparse, json, os, shutil, signal, subprocess, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import cases  # noqa: E402

PY = sys.executable
NS = {"Rising Smoke", "Mushroom Clouds", "Candle Flame", "Rayleigh-Benard", "Chimney Plume"}
NATIVE = {"Wind Tunnel", "Porous Flow", "Detonation", "Shock Tube", "Shockwave Strike", "The Big Splash"}
COST = {"Chimney Plume": 5, "Rising Smoke": 4, "Mushroom Clouds": 4, "Rayleigh-Benard": 3, "Candle Flame": 2,
        "Cloud Billows": 1, "Ink in Motion": 1, "Tracer in Rock": 1}       # ordering only: long jobs first
MIN_FREE_GB = 8


def threads_for(exhibit):
    if exhibit in NS or exhibit in NATIVE:
        return 8
    return 2


CHIPLETS = 12                                            # 7995WX: 12 x 8 cores; WSL vCPUs 16k..16k+15 (SMT pairs adjacent)


def chiplet_cpus(k, mode):
    return f"{16 * k}-{16 * k + 15}" if mode == "ccd" else ",".join(str(16 * k + 2 * j) for j in range(8))


def free_gb(path):
    return shutil.disk_usage(path).free / 1e9


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
    ap.add_argument("--group", choices=["all", "ns", "other"], default="all")
    ap.add_argument("--ns-slots", type=int, default=12); ap.add_argument("--scratch", default="")
    ap.add_argument("--defer", default="", help="comma-separated exhibits to run after everything else")
    ap.add_argument("--pin", choices=["none", "ccd", "ccd-even"], default="none",
                    help="bind each NS job to one chiplet (see bench/ns_conc.py): all 16 of its vCPUs, or one per core")
    a = ap.parse_args()
    if a.pin != "none":
        a.ns_slots = min(a.ns_slots, CHIPLETS)
    free_slots = list(range(a.ns_slots))
    runs = Path(a.runs); runs.mkdir(parents=True, exist_ok=True)
    scratch = Path(a.scratch) if a.scratch else runs / "_scratch"; scratch.mkdir(parents=True, exist_ok=True)
    log = open(runs / "batch.log", "a")
    todo = cases.build()
    if a.only:
        keep = set(a.only.split(",")); todo = [c for c in todo if c["id"] in keep]
    if a.group != "all":
        todo = [c for c in todo if (c["exhibit"] in NS) == (a.group == "ns")]
    todo = [c for c in todo if not done(runs / c["id"])]
    defer = set(filter(None, a.defer.split(",")))
    todo.sort(key=lambda c: (c["exhibit"] in defer, -COST.get(c["exhibit"], 0)))
    print(f"{len(todo)} cases to run, thread budget {a.budget}, {a.ns_slots} NS slots, scratch {scratch}", flush=True)
    running = {}                                         # proc -> (case, threads, t0, stderr file, scratch dir, NS slot)
    used = 0; t_batch = time.time(); n_done = 0; n_fail = 0; low_disk = False

    def can_start(c):
        if running and used + threads_for(c["exhibit"]) > a.budget:
            return False
        return c["exhibit"] not in NS or sum(1 for v in running.values() if v[0]["exhibit"] in NS) < a.ns_slots

    while todo or running:
        while todo:
            if free_gb(scratch) < MIN_FREE_GB:
                if not low_disk:
                    print(time.strftime("%H:%M:%S"), f"scratch disk below {MIN_FREE_GB} GB free, holding new jobs", flush=True)
                low_disk = True; break
            low_disk = False
            c = next((c for c in todo if can_start(c)), None)
            if c is None:
                break
            todo.remove(c); th = threads_for(c["exhibit"])
            tmp = scratch / c["id"]; shutil.rmtree(tmp, ignore_errors=True); tmp.mkdir(parents=True)
            env = dict(os.environ, OMP_NUM_THREADS=str(th), OPENBLAS_NUM_THREADS=str(th), MKL_NUM_THREADS=str(th),
                       NUMEXPR_NUM_THREADS=str(th), PYTHONUNBUFFERED="1", TMPDIR=str(tmp), TMP=str(tmp), TEMP=str(tmp))
            if a.smoke:
                env["FUNOOS_SMOKE"] = "1"
            (runs / c["id"]).mkdir(parents=True, exist_ok=True)
            err = open(runs / c["id"] / "stderr.txt", "w")
            cmd = [PY, str(HERE / "run_case.py"), c["id"], str(runs)]
            slot = free_slots.pop(0) if c["exhibit"] in NS else None
            cpus = chiplet_cpus(slot, a.pin) if slot is not None and a.pin != "none" else ""
            if cpus:
                cmd = ["taskset", "-c", cpus] + cmd
            p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=err, text=True, env=env, start_new_session=True)
            running[p] = (c, th, time.time(), err, tmp, slot); used += th
            print(time.strftime("%H:%M:%S"), "start", c["id"], f"({th} thr, {len(running)} running, {used} threads{', cpus ' + cpus if cpus else ''})", flush=True)
        time.sleep(5)
        for p in list(running):
            c, th, t0, err, tmp, slot = running[p]
            rc = p.poll()
            if rc is None and time.time() - t0 > a.timeout:
                os.killpg(p.pid, signal.SIGKILL); p.wait(); rc = -9          # the C++ solver child too
            if rc is None:
                continue
            out = p.stdout.read().strip().splitlines(); err.close(); shutil.rmtree(tmp, ignore_errors=True)
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
            if slot is not None:
                free_slots.append(slot)
    print(f"batch finished in {(time.time() - t_batch) / 60:.1f} min: {n_done} cases, {n_fail} failed", flush=True)


if __name__ == "__main__":
    main()
