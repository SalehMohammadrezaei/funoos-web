import os, sys, time, json, subprocess
ROOT='/mnt/d/Saleh/Funoos_dev'; PY='/home/impres/Saleh/FlowZoo/.venv/bin/python'
RUN=r'''
import sys,time,json; sys.path.insert(0,%r)
from flowzoo import engine,catalog
s=catalog.scene(%r); p={q["name"]:q["default"] for q in engine.EXHIBITS[s["exhibit"]]["params"]}; p.update(s["preset"])
if "resolution" in p: p["resolution"]="High"
if "duration" in p: p["duration"]=1.8
t=time.time(); r=engine.solve_exhibit(s["exhibit"],p); solve=time.time()-t
t=time.time(); fr=r.render(r.views[0],engine.DEFCMAP[r.kind]); print(json.dumps(dict(solve_s=solve,render_s=time.time()-t,frames=len(fr),shape=list(fr[0].shape))))
'''
jobs=[(k,int(t)) for k in sys.argv[1].split(',') for t in sys.argv[2].split(',')]
procs=[]
for k,t in jobs:
    procs.append((k,t,time.time(),subprocess.Popen([PY,'-c',RUN%(ROOT,k)],cwd=ROOT,env=dict(os.environ,OMP_NUM_THREADS=str(t)),stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,text=True)))
for k,t,t0,p in procs:
    out,_=p.communicate(); rec=dict(key=k,threads=t,wall_s=round(time.time()-t0,1))
    try: rec.update(json.loads(out.strip().splitlines()[-1]))
    except Exception: rec['failed']=True
    print(json.dumps(rec),flush=True)
