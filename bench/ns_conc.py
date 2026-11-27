"""Throughput of the incompressible Navier-Stokes solver under concurrency.

    python bench/ns_conc.py <N> <T> [--pin] [--key ns_smoke] [--duration 0.15] [--resolution High]

Runs N copies of one NS scene at once, T OpenMP threads each, and appends one JSON line to
bench/ns_conc.jsonl: per-job solve time and the wall time of the set. Solver scratch goes to
D:, not /tmp. Short durations are fine for comparing configurations: cost is linear in steps.

Pinning (--pin MODE). WSL numbers the SMT siblings as adjacent pairs (0-1, 2-3, ...) and hides
the cache topology; the 7995WX has 12 chiplets of 8 cores, each with its own 32 MB L3, which
in vCPU order would be 16k .. 16k+15.
    block     job i on vCPUs [i*T, (i+1)*T)
    ccd       job i on the 16 vCPUs of chiplet i (8 cores, both SMT threads)
    ccd-even  job i on one vCPU per core of chiplet i (16i, 16i+2, ..., 16i+14)
"""
import argparse, json, os, shutil, subprocess, sys, time
from pathlib import Path

ROOT = "/mnt/d/Saleh/Funoos_dev"
HERE = Path(__file__).resolve().parent
RUN = r'''
import sys, time, json; sys.path.insert(0, %r)
from flowzoo import engine, catalog
s = catalog.scene(%r); p = {q["name"]: q["default"] for q in engine.EXHIBITS[s["exhibit"]]["params"]}; p.update(s["preset"])
p["resolution"] = %r; p["duration"] = %r
t = time.time(); r = engine.solve_exhibit(s["exhibit"], p); print(json.dumps(dict(solve_s=time.time() - t)))
'''


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("N", type=int); ap.add_argument("T", type=int)
    ap.add_argument("--pin", nargs="?", const="block", default="", choices=["", "block", "ccd", "ccd-even"])
    ap.add_argument("--key", default="ns_smoke"); ap.add_argument("--duration", type=float, default=0.15)
    ap.add_argument("--resolution", default="High")
    a = ap.parse_args()
    scratch = HERE.parent / "runs" / "_scratch" / "bench"; shutil.rmtree(scratch, ignore_errors=True)
    procs = []; t0 = time.time()
    for i in range(a.N):
        tmp = scratch / str(i); tmp.mkdir(parents=True)
        env = dict(os.environ, OMP_NUM_THREADS=str(a.T), TMPDIR=str(tmp))
        cmd = [sys.executable, "-c", RUN % (ROOT, a.key, a.resolution, a.duration)]
        cpus = {"block": f"{i * a.T}-{(i + 1) * a.T - 1}", "ccd": f"{16 * i}-{16 * i + 15}",
                "ccd-even": ",".join(str(16 * i + 2 * j) for j in range(8))}.get(a.pin)
        if cpus:
            cmd = ["taskset", "-c", cpus] + cmd
        procs.append(subprocess.Popen(cmd, cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True))
    per = []
    for p in procs:
        out, _ = p.communicate()
        try:
            per.append(round(json.loads(out.strip().splitlines()[-1])["solve_s"], 1))
        except Exception:                                   # noqa: BLE001
            per.append(None)
    wall = time.time() - t0
    shutil.rmtree(scratch, ignore_errors=True)
    ok = [x for x in per if x]
    rec = {"N": a.N, "T": a.T, "pin": a.pin, "key": a.key, "resolution": a.resolution, "duration": a.duration,
           "wall_s": round(wall, 1), "mean_s": round(sum(ok) / len(ok), 1) if ok else None, "per_job": per}
    with open(HERE / "ns_conc.jsonl", "a") as f:
        f.write(json.dumps(rec) + "\n")
    print(json.dumps(rec), flush=True)


if __name__ == "__main__":
    main()
