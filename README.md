# Funoos on the web

The static web version of [Funoos](https://github.com/SalehMohammadrezaei/Funoos), the fluid
simulation laboratory: every experiment of the desktop app, pre-run at the app's gallery
quality and served as a plain GitHub Pages site. No installation, no server, no account.

The site is generated from a library of pre-computed cases. Each case is one run of the app's
engine with its parameters, measurements, diagnostic plots, explanation layers and one clip per
view. The pages offer fixed choices; for any other value, geometry or duration the desktop app
is the tool.

## Layout

| Path | What it is |
|---|---|
| `tools/cases.py` | the case library: all 51 presets of the app plus the parameter sweeps of each experiment; every case passes the app's own validity checks |
| `tools/run_case.py` | runs one case end to end: solve, measure, plot, render and encode, with per-case checks |
| `tools/batch.py` | runs the library with a thread budget; restartable |
| `tools/trends.py` | cross-case physics checks, written to `CHECKS.md` |
| `tools/build_site.py` | writes the site into `docs/` from the finished runs |
| `site/assets/` | the stylesheet (the app's own design system plus a light theme), the page script and the icon |
| `docs/` | the generated site served by GitHub Pages |
| `PLAN.md` | the assessment and plan the library follows |

The clips are release assets of this repository (`media-v1`); the pages load them from there.
Posters, plots and the per-experiment JSON manifests live in `docs/`.

## Rebuilding

```bash
# with the Funoos source at the path set in tools/cases.py and its Python environment active
python tools/batch.py runs --pin ccd           # the whole library (about a day on a 96-core workstation)
python tools/trends.py runs CHECKS.md
python tools/build_site.py runs docs --media-base https://github.com/SalehMohammadrezaei/funoos-web/releases/download/media-v1/
python tools/upload_media.py runs media-v1 <file holding a GitHub token>   # clips to the release; restartable
```

Without `--media-base` the clips are copied into `docs/media/video/` for a local preview
(`python -m http.server` inside `docs/`).

The batch keeps solver scratch (raw frames, up to about 0.5 GB per job) in `runs/_scratch/`,
not `/tmp`, and runs at most `--ns-slots` incompressible Navier-Stokes jobs at once: their
pressure solve is limited by memory bandwidth, so running dozens together makes each one many
times slower. `--group ns` or `--group other` runs one part of the library;
`bench/ns_conc.py` measures NS throughput against the number of concurrent jobs. On a
Threadripper PRO 7995WX, 12 jobs of 8 threads gave 3.5 times the throughput of one job, with
or without pinning each job to a chiplet. The Navier-Stokes runs at High took 18.4 hours there;
everything else together takes under 2 hours.

## Licence

MIT, copyright (c) 2026 Saleh Mohammadrezaei. The simulations, text and figures are produced by
Funoos, released under the same licence.
