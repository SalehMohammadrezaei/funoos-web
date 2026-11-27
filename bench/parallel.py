"""Throughput test: N cases at once, T threads each, on a mix of solvers, gallery resolution."""
import json, os, sys, time, subprocess
ROOT='/mnt/d/Saleh/Funoos_dev'; PY='/home/impres/Saleh/FlowZoo/.venv/bin/python'
N, T = int(sys.argv[1]), int(sys.argv[2])
keys=['lbm_cylinder','ns_rb','euler_blast','sph_dam','spec_kh','rd_spots','tracer_pulse','porous_phi60','mix_stir','lbm_airfoil','ns_smoke','rd_maze'][:N]
RUN=r'''
import sys,time,json; sys.path.insert(0,%r)
from flowzoo import engine,catalog
s=catalog.scene(%r); p={q["name"]:q["default"] for q in engine.EXHIBITS[s["exhibit"]]["params"]}; p.update(s["preset"])
if "resolution" in p: p["resolution"]="High"
if "duration" in p: p["duration"]=1.8
t=time.time(); r=engine.solve_exhibit(s["exhibit"],p); print(json.dumps(dict(solve_s=time.time()-t)))
'''
t0=time.time(); procs=[]
for k in keys:
    procs.append((k, subprocess.Popen([PY,'-c',RUN%(ROOT,k)],cwd=ROOT,env=dict(os.environ,OMP_NUM_THREADS=str(T)),stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,text=True)))
res={}
for k,p in procs:
    out,_=p.communicate(); 
    try: res[k]=json.loads(out.strip().splitlines()[-1])['solve_s']
    except Exception: res[k]=None
wall=time.time()-t0
print(json.dumps(dict(N=N,threads=T,wall_s=round(wall,1),per_case=res)))
