# Funoos on the web

The static web version of [Funoos](https://github.com/SalehMohammadrezaei/Funoos), the fluid
simulation laboratory: the app's own interface (home, gallery, experiment pages, Studio) with
every experiment pre-run at Ultra, its highest resolution, served as a plain GitHub Pages site. No
installation, no server, no account.

The site is generated from a library of pre-computed cases. Each case is one run of the app's
engine with its parameters, measurements, diagnostic plots, explanation layers and one clip per
view. The Studio's controls offer the pre-run values; for any other value, geometry or duration
the desktop app is the tool.

The interface is not a copy kept in this repository: `tools/build_site.py` takes `index.html`
and `web/` from the Funoos source, unchanged, and adds a layer that answers the app's backend
calls from the library instead of the Python solver. A new Funoos interface is picked up by
rebuilding.

## Layout

| Path | What it is |
|---|---|
| `tools/cases.py` | the case library: all 51 presets of the app plus the parameter sweeps of each experiment; every case passes the app's own validity checks |
| `tools/run_case.py` | runs one case end to end: solve, measure, plot, render and encode, with per-case checks |
| `tools/batch.py` | runs the library with a thread budget; restartable |
| `tools/trends.py` | cross-case physics checks, written to `CHECKS.md` |
| `tools/build_site.py` | writes the site into `docs/`: the app's interface from the Funoos source, the web layer from `site/`, and the case data from the finished runs |
| `site/web_backend.js` | answers the app's backend calls (`window.pywebview.api`) from the pre-run library: catalogue, scenes, runs, views, plots, run history, sweeps |
| `site/web_overrides.js` | the changes a pre-run library needs: Studio controls list the pre-run values (other controls move to the nearest pre-run combination), results load at once, side-by-side comparison, links that follow the page |
| `site/web.css` | additions to the app's stylesheet: hidden desktop-only tools, comparison layout, phone layout |
| `docs/` | the generated site served by GitHub Pages |
| `PLAN.md` | the assessment and plan the library follows |

The clips are release assets of this repository (`media-v2`; `media-v1` holds the earlier High
library); the pages load them from there.
Posters, plots, the app's gallery thumbnails and the case data (`data/`) live in `docs/`.
Links: `#gallery`, `#e/<scene>` (an experiment page), `#c/<case id>` (a case in the Studio).
The addresses of the first version of the site (`experiments/<id>.html#<case id>`, `about.html`)
and of the preview (`preview/`) redirect to the same place in this one.

## Rebuilding

```bash
# with the Funoos source at the path set in tools/cases.py and its Python environment active
export FUNOOS_RESOLUTION="Ultra (slow)" FUNOOS_CLIP_MAXW=1920 FUNOOS_CLIP_CRF=23
python tools/batch.py runs_ultra --group other --budget 188                    # a few hours
python tools/batch.py runs_ultra --group ns --pin ccd --budget 188 --timeout 259200
python tools/trends.py runs_ultra CHECKS.md
python tools/upload_media.py runs_ultra media-v2 <file holding a GitHub token>   # clips to the release; restartable
python tools/build_site.py runs_ultra docs --media-base https://github.com/SalehMohammadrezaei/funoos-web/releases/download/media-v2/
```

Keep `FUNOOS_RESOLUTION` set for every command: it decides which cases the library holds.
Without these variables the same tools build the High library (960 px clips) in `runs/`.

Run the two batch groups one after the other. With other jobs on the same chiplets, the Ultra
Navier-Stokes jobs ran about five times slower than on their own, because their pressure solve
(conjugate gradients) is limited by cache and memory bandwidth.

Without `--media-base` the clips are copied into `docs/media/video/` for a local preview
(`python -m http.server` inside `docs/`).

The batch keeps solver scratch (raw frames, up to about 0.5 GB per job) in `runs/_scratch/`,
not `/tmp`, and runs at most `--ns-slots` incompressible Navier-Stokes jobs at once: their
pressure solve is limited by memory bandwidth, so running dozens together makes each one many
times slower. `--group ns` or `--group other` runs one part of the library;
`bench/ns_conc.py` measures NS throughput against the number of concurrent jobs. On a
Threadripper PRO 7995WX, 12 jobs of 8 threads gave 3.5 times the throughput of one job, with
or without pinning each job to a chiplet. The Navier-Stokes runs at High took 18.4 hours there;
the whole library at Ultra took 58.5 hours.

## Licence

MIT, copyright (c) 2026 Saleh Mohammadrezaei. The simulations, text and figures are produced by
Funoos, released under the same licence.
