"""One gallery-resolution run per solver at several OMP thread counts; wall time per case."""
import json, os, sys, time, subprocess
ROOT = '/mnt/d/Saleh/Funoos_dev'
PY = '/home/impres/Saleh/FlowZoo/.venv/bin/python'
CASES = [('lbm_cylinder','LBM'),('ns_rb','NS projection'),('euler_blast','Euler'),('sph_dam','SPH'),
         ('spec_kh','spectral'),('rd_spots','reaction-diffusion'),('tracer_pulse','tracer'),('porous_phi60','porous LBM'),('mix_stir','dye transport')]
THREADS = [int(t) for t in sys.argv[1].split(',')] if len(sys.argv) > 1 else [1, 2, 4, 8, 16]
out = '/mnt/d/Saleh/funoos_web/bench/bench.jsonl'
RUN = r'''
import sys, time, json; sys.path.insert(0, %r)
from flowzoo import engine, catalog
s = catalog.scene(%r); p = {q["name"]: q["default"] for q in engine.EXHIBITS[s["exhibit"]]["params"]}; p.update(s["preset"])
if "resolution" in p: p["resolution"] = "High"
if "duration" in p: p["duration"] = 1.8
t = time.time(); r = engine.solve_exhibit(s["exhibit"], p); solve = time.time() - t
t = time.time(); fr = r.render(r.views[0], engine.DEFCMAP[r.kind]); rend = time.time() - t
print(json.dumps(dict(solve_s=solve, render_s=rend, frames=len(fr), shape=list(fr[0].shape), quality=r.quality[0])))
'''
for key, solver in CASES:
    for th in THREADS:
        env = dict(os.environ, OMP_NUM_THREADS=str(th))
        t = time.time()
        pr = subprocess.run([PY, '-c', RUN % (ROOT, key)], cwd=ROOT, env=env, capture_output=True, text=True)
        rec = dict(key=key, solver=solver, threads=th, wall_s=round(time.time() - t, 1), ok=pr.returncode == 0)
        try: rec.update(json.loads(pr.stdout.strip().splitlines()[-1]))
        except Exception: rec['err'] = (pr.stderr or pr.stdout)[-300:]
        open(out, 'a').write(json.dumps(rec) + '\n'); print(json.dumps(rec), flush=True)
