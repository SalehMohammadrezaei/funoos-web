# Funoos web version: assessment and plan

Status: proposal, nothing built, nothing run beyond benchmarks. Date 2026-11-18.
Everything marked *estimate* is extrapolated from measurements on this machine; the pilot (step 1) replaces the estimates with measured numbers before the big batch.

## 1. Resources and benchmarks

Machine: 192 hardware threads, 385 GB RAM free, D: has 362 GB free. Home disk `/` has 1.4 GB free, so every batch output goes to `/mnt/d/Saleh/funoos_web/`.

Measured (gallery settings: resolution High, duration 1.8, machine otherwise idle unless noted):

| Case | Solver | Cells / particles | Steps | Threads | Solve time | Notes |
|---|---|---|---|---|---|---|
| lbm_cylinder | LBM | 1215 x 405 | 79,200 | 2 | 502 s | |
| lbm_cylinder | LBM | | | 4 | 292 s | |
| lbm_cylinder | LBM | | | 8 | 152 s | |
| lbm_cylinder | LBM | | | 16 | 76 s | near-perfect scaling to 16 |
| ns_rb (heated layer) | INS, exact projection | 201k | 8,640 | 4 | ~75 min | measured during load, upper bound |
| ns_rb | INS | 201k | 8,640 | 12 | ~58 min | measured during load |
| ns_rb, **Medium** | INS | 110k | 8,640 | 8 | 1167 s (19.5 min) | idle machine |
| ns_rb, Medium, duration 1.0 | INS | 110k | 4,800 | 8 | 671 s | cost is linear in steps |
| ns_chimney | INS | 413k | 8,640 | 12 | 150 to 240 min | from September re-render logs, under load |
| ns_smoke, ns_rt | INS | 225k | 8,640 | 12 | ~66 min | September logs |
| ns_flame | INS | 124k | 8,640 | 12 | ~30 min | September logs |
| rendering one view | | | | | 1.6 s | 97 frames, 405 x 1409 |

Fast solvers (euler, sph, spectral, reaction-diffusion, tracer, porous, dye): see table FAST below (filled in from `bench/quick.log`).

| Case | Solver | 4 threads | 8 threads | Scales with threads? |
|---|---|---|---|---|
| euler_blast | Euler (C++) | 25 s | 16 s | yes |
| sph_dam | SPH (C++) | 11 s | 7 s | yes |
| porous_phi60 | LBM porous (C++) | 91 s | 57 s | yes |
| spec_kh | spectral (Python, FFT) | 370 s | 357 s | no |
| tracer_pulse | tracer (Python) | 377 s | 389 s | no |
| mix_stir | dye (Python) | 335 s | 375 s | no |
| rd_spots | reaction-diffusion (Python) | 80 s | 90 s | no |

(all 14 jobs ran at once, so these are times under 56-thread concurrency; rendering 0.7 to 2.3 s per view)

The four Python solvers are single-core in practice: give them **2 threads each and run 30 at once**; the C++ solvers get 8 threads each.

What this means:

- The incompressible Navier-Stokes scenes (smoke, Rayleigh-Taylor, flame, heated layer, chimney) are the cost driver. Their conjugate-gradient pressure solve is called every step, so time scales with cells x steps and worse. Everything else is seconds to a few minutes.
- Parallel versus threads: LBM scales almost perfectly to 16 threads, so for LBM it does not matter much; 8 threads per job with many jobs is simplest. For the NS solver the OpenMP scaling is weaker (4 -> 12 threads gave only 1.3x in September), so running **many NS jobs at 8 threads each** beats fewer jobs at 24 or 48 threads. Recommendation: a job pool of 16 concurrent jobs x 8 threads = 128 threads, leaving a third of the machine free. The pilot measures whether 16 concurrent jobs slow each other down (memory bandwidth); if they do, drop to 12 x 8.
- Resolution decision for the NS scenes: **High costs about 3x Medium** (1.8x cells and more CG iterations). With 50 NS runs (section 2): High is roughly 50 x 60 min / 16 jobs = **3 to 5 h wall**, Medium about **1.5 h**. Both fit one night. Recommendation: run NS at **High** like the gallery, with Medium as the fallback if the pilot shows High exceeding 90 min per run under full load. All other exhibits at High.

## 2. Parameter library

Rules applied: only parameters the experiment is about are swept; everything else stays at the preset value; every value is inside the slider range and passes `schema.validate` with no error and no warning (all grids below were checked with the app's own validator); where two parameters interact the full grid is run so every offered combination exists; held-fixed derived quantities (Wind Tunnel tau and Mach, tracer Dm from Pe) are what the app computes from the preset.

| # | Experiment (scene) | Parameters | Values | Runs | Reason |
|---|---|---|---|---|---|
| 1 | Cylinder wake (lbm_cylinder) | reynolds | 40, 80, 180, 400, 1200 | 5 | steady wake below Re 47, onset of shedding, preset, and two higher Re; Strouhal vs Re is the classic plot (tau 0.82 -> 0.51, Mach 0.14 fixed) |
| | | obstacle at Re 180 | Square, Diamond | 2 | bluff-body shape changes separation point and drag |
| 2 | Airfoil lift (lbm_airfoil) | angle at Re 400 | -14, -6, 0, 6, 14, 20 | 6 | lift sign change through zero, linear range, stall at high angle (circulation-based cl) |
| 3 | Cycling and drafting (lbm_peloton) | reynolds | 200, 500, 1000 | 3 | how the wake shelter changes with Re; speed fixed at preset 0.09 |
| 4 | Flow around text (lbm_name) | reynolds, text "Funoos" | 60, 220, 800 | 3 | same text, laminar to unsteady; custom text needs the app |
| 5 | Car silhouette (lbm_f1) | reynolds | 100, 320, 1000 | 3 | wake and drag of a bluff car body vs Re |
| 6 | Porous flow (porous_phi60) | porosity x grain | {0.45, 0.6, 0.75, 0.85} x {0.02, 0.035, 0.07} | 12 | Kozeny-Carman trend: k grows with porosity cubed and grain squared; full grid so any pair exists |
| 7 | Tracer through rock (tracer_pulse) | peclet x injection | {0.5, 2, 20, 100, 400} x {Pulse, Continuous supply} | 10 | diffusion-dominated to advection-dominated; both injection modes because arrival-time and dispersion diagnostics differ |
| 8 | Rising smoke (ns_smoke) | buoyancy x confinement | {0.001, 0.0022, 0.005} x {0, 7, 18} | 9 | plume speed vs buoyancy; vorticity confinement from off to strong shows what is physics and what is model |
| 9 | Rayleigh-Taylor (ns_rt) | atwood x modes | {0.2, 0.5, 0.7, 1.0} x {0, 3} | 8 | growth rate rises with Atwood number; single-mode vs multimode mixing width |
| 10 | Candle flame (ns_flame) | zst x buoyancy | {0.10, 0.16, 0.25} x {0.012, 0.025} | 6 | stoichiometric mixture fraction sets flame position; buoyancy sets flicker and height |
| 11 | Heated layer (ns_rb) | buoyancy x viscosity | {0, 0.0015, 0.003, 0.006, 0.012} x {0.0003, 0.0006, 0.0012} | 15 | Rayleigh number from 0 to 2.4e10 through onset at 657.5; Nusselt vs Ra is the key plot; buoyancy 0 is the conduction control |
| 12 | Chimney plume (ns_chimney) | wind x buoyancy | {0, 0.15, 0.3, 0.55} x {0.002, 0.005, 0.01} | 12 | plume rise vs bending; wind 0 is a vertical plume control |
| 13 | Sod shock tube (euler_sod) | resolution | Low, Medium, High, Ultra | 4 | only free parameter is grid; density vs exact solution shows convergence |
| 14 | Open-air blast (euler_blast) | pressure | 20, 50, 140, 400 | 4 | shock radius vs time and overpressure ratio |
| 15 | Blast and obstacles (euler_city) | pressure, Rigid walls | 50, 160, 400 | 3 | shock diffraction and reflection strength; "Erodes" is marked experimental in the app and is left out |
| | | charge at 160 | 0.03, 0.12 | 2 | charge size vs shielding |
| 16 | Shock-bubble (euler_bubble) | mach x densratio | {1.2, 1.6, 2.5} x {0.14, 0.5, 3.0} | 9 | light bubble (helium-like) vs heavy bubble (R22-like); ratio 1 is skipped because there is no bubble |
| | | target at M1.6, ratio 0.18 | Two bubbles | 1 | interaction between bubbles |
| 17 | Still water (sph_rest) | particles | 600, 3000, 12000 | 3 | hydrostatic baseline, pressure noise vs resolution, speed-limiter count must be zero |
| 18 | Dam break (sph_dam) | width x height | {0.5, 1, 2} x {1, 2, 3} | 9 | front speed scales with sqrt(g h); aspect ratio changes the splash |
| 19 | Water-blob impact (sph_drop) | dropsize x dropheight | {0.2, 0.4, 0.8} x {0.5, 0.9} | 6 | impact speed from height, crown from size |
| 20 | Sloshing tank (sph_slosh) | sloshT x sloshA | {0.6, 1.1, 2.0} x {0.3, 0.7, 1.5} | 9 | resonance when forcing period meets the tank's natural period; amplitude from linear to breaking |
| 21 | Pouring (sph_pour) | pourv x spout | {0.5, 1.4, 3.0} x {0.025, 0.09} | 6 | jet speed and width set splash and air entrainment |
| 22 | Wave tank (sph_waves) | waveA x waveT | {0.15, 0.4, 0.8} x {0.5, 0.9, 1.8} | 9 | wave steepness from amplitude over wavelength; short periods break |
| 23 | Floating hull (sph_ship) | shipsz x waveA | {0.5, 1.0, 1.8} x {0.2, 0.6} | 6 | hull size relative to wavelength decides pitch and heave |
| 24 | Kelvin-Helmholtz (spec_kh) | viscosity x thickness | {1e-5, 8e-5, 4e-4} x {0.015, 0.033, 0.08} | 9 | thinner layer grows faster; viscosity damps small scales |
| 25 | Decaying turbulence (spec_decay) | viscosity | 1e-5, 8e-5, 4e-4 | 3 | energy and enstrophy decay rates vs viscosity |
| | | seed at 8e-5 | 2 | 1 | shows statistics are the same for a different realisation |
| 26 | Taylor-Green (spec_tg) | viscosity | 5e-5, 2e-4, 4e-4 | 3 | exact exponential decay exp(-2 nu k^2 t) to compare against |
| | | perturbation at 4e-4 | 0.005, 0.2 | 2 | when the vortex array breaks symmetry |
| 27 | Dye transport (mix_bands) | stir x diffusion | {0, 0.5, 1} x {0, 1e-4, 1e-3} | 9 | stirring vs molecular diffusion; stir 0 and D 0 is the do-nothing control |
| | | bands at preset | 2, 14 | 2 | initial scale of the dye |
| 28 | Gray-Scott (rd_spots) | pattern | Spots, Stripes, Maze, Mitosis, Coral, Waves | 6 | the six named Pearson regimes |
| | | Custom F x k | {0.03, 0.055} x {0.06, 0.065} | 4 | shows how a small move in F, k changes regime |

Totals: **204 runs**, of which 50 are incompressible NS (the expensive ones), 22 LBM, 132 fast solvers. Each run stores all its views (3 to 4), so about 720 clips.

Not included on purpose: speed, size and xpos in the Wind Tunnel (held fixed by the preset to keep tau and Mach safe), seeds (no physics), duration (all 1.8), "Erodes" structures, custom text.

## 3. Checks

Per run, automatic, written to `checks.json` beside the result:

1. Process exit code 0 and `result.quality` not "unstable"; the NS solver exits 4 on a non-finite state, which fails the run.
2. Every stored field and every rendered frame finite (`np.isfinite`), no all-constant frames after the first.
3. Existing diagnostics from `postproc.metrics()` present and within sane bounds (per exhibit list below); `result.hints` recorded and shown on the page.
4. Media: clip produced, duration matches frame count, size under the per-file budget.

Per sweep, after the batch (trend checks, these are the physics):

- Cylinder: Strouhal rises from 0 (Re 40, no shedding) to about 0.18 to 0.21 for Re 180 to 1200. Airfoil: cl changes sign through 0 degrees and is monotone for |angle| <= 14.
- Porous: permeability increases with porosity and with grain squared, monotone on the grid. Tracer: mass balance within 2 %; dispersion over molecular rises with Pe; t50 arrival falls with Pe for pulse injection.
- Heated layer: Nusselt about 1 for Ra below 657 (buoyancy 0 and the two lowest Ra), rising monotonically above. RT: mixing width grows with Atwood number at fixed modes.
- Smoke, flame, chimney: final kinetic energy increases with buoyancy at fixed confinement or wind.
- Sod: density error falls with resolution (roughly first order). Blast: final shock radius increases with pressure. Shock-bubble: ke_final increases with Mach.
- SPH: still water has zero speed-limiter events at all particle counts; dam-break front position scales with sqrt(g h); slosh amplitude peaks nearest the natural period.
- KH and decay: enstrophy at the end decreases with viscosity; TG kinetic energy decay matches exp(-2 nu k^2 t) to a few percent (quantitative).
- Dye: final dye variance decreases with stir and with diffusion. Gray-Scott: pattern coverage differs between regimes and is stable (no blow-up, no extinction except where Pearson predicts it).

A trend that fails does not stop publication by itself; it flags the sweep for a look and the page says what was found. Quality labels come from the app itself (`result.quality`: quantitative, qualitative, illustrative) and are shown on every page.

## 4. Pilot, totals, storage

Pilot: the 15 representative presets (one per exhibit), full pipeline: run, checks, render, encode, page. All 15 fit in one pool; wall time set by ns_chimney at High, **about 3 h** (estimate; 1 h if NS goes Medium). Outcome: measured run times under concurrency, measured clip sizes, a first look at the pages, and a go/no-go on High vs Medium.

Full batch (estimate, to be replaced by pilot numbers): NS 50 runs x ~60 min at 8 threads, 16 concurrent -> 3 to 5 h; LBM 22 x 2.5 min -> 10 min; fast 132 runs (about 290 min of serial time, 30 at once) -> 15 min; rendering and encoding 720 clips -> about 1 h. **One night** total, nothing to do during it.

Storage on D: per run about 15 to 30 MB (params and metrics JSON, plots as SVG and PNG, final-state npz for re-rendering, mp4 per view) -> about 5 GB in `/mnt/d/Saleh/funoos_web/runs/`. Fine.

Video settings proposed: H.264 (libx264), CRF 28, preset slow, yuv420p, longest side 960 px, 24 fps, each clip 4 s (97 frames) and set to loop; plus a WebP poster per clip. Gallery clips at these sizes were 60 kB to 2.8 MB (reaction-diffusion and Rayleigh-Taylor compress worst). Estimate **0.9 MB average -> 650 MB** of video for 720 clips. Compare pages reuse the same files.

Hosting: GitHub Pages has a soft 1 GB site limit, 100 GB per month bandwidth, and a 100 MB per-file limit through git. Recommendation: **two places**. Site repo `funoos-web` on Pages holds HTML, JSON, plots and posters (estimate under 100 MB). Videos go as **release assets** of the same repo (2 GB per file, no total limit, served over HTTPS with the right CORS headers for `<video>`), one release per batch (`media-v1`). A fallback if release URLs misbehave on phones is a second Pages repo for media. I would rather not put 650 MB of mp4 in the Funoos source repo.

## 5. Site

Static, generated by one Python script (Jinja2 templates) from the run folder, no framework and no build step beyond that script. No server, no install.

- Home: the seven phenomenon groups from `catalog.by_phenomenon()` with one poster each; search by name; link to the desktop app releases (v1.3.2, macOS, Windows, Linux).
- Experiment page (28): the question from the catalog; fixed-choice controls (dropdown per swept parameter) that switch the video, metrics and plots without a page reload (one JSON manifest per experiment); a note at the top: "These are pre-run cases. Install Funoos to choose any value."; view switcher (Vorticity, Speed, ...); key numbers from `postproc.metrics` and the derived readouts from `schema.derived` (Re, tau, Mach, Ra, Pe, ...); plots from `postproc.plots_svg`; the nine explanation layers from `catalog.scene_layers` as collapsible sections; equations from `engine.META[...]['eq']` rendered with KaTeX (all 16 use standard macros, verified); `result.quality` and hints shown; the Sod page shows density against the exact solution.
- Compare: two cases of the same experiment side by side (pick two parameter sets), videos synchronised, metrics in one table. Also cross-experiment compare for the pairs in `EXPERIMENTS[...]['compare']`.
- Course pages: generated from `courses.yaml` (code, title, one paragraph, ordered list of experiments with a line each). Proposed defaults, to be corrected by you: MATH24412 (Kelvin-Helmholtz, Taylor-Green, decaying turbulence, cylinder wake, Sod), CHEN40451 (porous flow, tracer, dye transport, heated layer, rising smoke), EART63012 (porous flow, tracer, Rayleigh-Taylor, heated layer, dam break).
- Phones: single column under 700 px, videos full width, dropdowns instead of sliders. Light/dark from the system setting with a toggle. KaTeX loaded from the CDN with a vendored fallback.

## 6. Timeline and what I need from you

| Step | Work | Time | Needed from you |
|---|---|---|---|
| 0 | Approve this plan, or change grids, resolution, hosting | now | decision: High or Medium for NS; release assets or second repo for media; new repo name (`funoos-web`) |
| 1 | Batch runner, checks, pilot of 15 cases on branch `web` of Funoos_dev | 3 h run + 2 h code | nothing; I start when you say go |
| 2 | Site generator and the experiment page with pilot data, served locally for you to look at | 3 h | look at it on your laptop and phone, tell me what to change; confirm course lists and paragraphs |
| 3 | Full batch of 204 runs | one night | machine left idle |
| 4 | Checks report, trend plots, encode, compare and course pages, home | 4 h | read the checks report with me, decide on any sweep that failed a trend |
| 5 | Create `funoos-web` repo, push branch, open PR, enable Pages on the branch, upload media release | 1 h | create the repo (or let me create it with the token), review the preview URL, approve publishing; link from the Funoos README |

Things I cannot promise until measured: run times under 16-way concurrency (pilot), clip sizes for the worst compressing scenes (pilot), and that phones autoplay muted video from release-asset URLs (I will test on the preview with your phone).
