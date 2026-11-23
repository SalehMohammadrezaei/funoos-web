# Checks of the pre-run library

Cases run: 214 of 214. Passing every per-case check: 209. Failing: 5.

## Cases with a failed per-case check
- `tracer_transport__peclet_0p5__injection_continuous_supply`:  ['quality_not_incomplete']
- `tracer_transport__peclet_0p5__injection_pulse`:  ['quality_not_incomplete']
- `tracer_transport__peclet_2__injection_continuous_supply`:  ['quality_not_incomplete']
- `tracer_transport__peclet_2__injection_pulse`:  ['quality_not_incomplete']
- `tracer_transport__tracer_diffusive`:  ['quality_not_incomplete']

## Solver quality notes
Cases the solver itself marked as not fully quantitative, with its reason.

- `porous_flow__porosity_0p45__grain_0p07` (qualitative): the pore Reynolds number is 1.59, not the creeping flow that Darcy's law and a frozen velocity field assume
- `porous_flow__porosity_0p6__grain_0p07` (qualitative): the pore Reynolds number is 4.18, not the creeping flow that Darcy's law and a frozen velocity field assume; the sample was asked for a porosity of 0.60 and packed to 0.583
- `porous_flow__porosity_0p75__grain_0p035` (qualitative): the pore Reynolds number is 4.64, not the creeping flow that Darcy's law and a frozen velocity field assume
- `porous_flow__porosity_0p75__grain_0p07` (qualitative): the pore Reynolds number is 21.4, not the creeping flow that Darcy's law and a frozen velocity field assume; the sample was asked for a porosity of 0.75 and packed to 0.739
- `porous_flow__porosity_0p85__grain_0p02` (qualitative): the pore Reynolds number is 2.1, not the creeping flow that Darcy's law and a frozen velocity field assume
- `porous_flow__porosity_0p85__grain_0p035` (qualitative): the pore Reynolds number is 9.21, not the creeping flow that Darcy's law and a frozen velocity field assume
- `porous_flow__porosity_0p85__grain_0p07` (qualitative): the flow had not settled: the permeability was still changing when the run ended; the pore Reynolds number is 35.2, not the creeping flow that Darcy's law and a frozen velocity field assume
- `porous_flow__porous_aniso` (qualitative): the pore Reynolds number is 1.04, not the creeping flow that Darcy's law and a frozen velocity field assume
- `porous_flow__porous_phi60` (qualitative): the pore Reynolds number is 1.4, not the creeping flow that Darcy's law and a frozen velocity field assume
- `tracer_transport__peclet_0p5__injection_continuous_supply` (incomplete): the step budget stopped this run after 0.146 of the 2.16 pore-volume crossings asked for; the pore Reynolds number is 1.84, not the creeping flow that Darcy's law and a frozen velocity field assume
- `tracer_transport__peclet_0p5__injection_pulse` (incomplete): the step budget stopped this run after 0.146 of the 2.16 pore-volume crossings asked for; the pore Reynolds number is 1.84, not the creeping flow that Darcy's law and a frozen velocity field assume
- `tracer_transport__peclet_100__injection_continuous_supply` (qualitative): the pore Reynolds number is 1.84, not the creeping flow that Darcy's law and a frozen velocity field assume
- `tracer_transport__peclet_100__injection_pulse` (qualitative): the pore Reynolds number is 1.84, not the creeping flow that Darcy's law and a frozen velocity field assume
- `tracer_transport__peclet_20__injection_continuous_supply` (qualitative): the pore Reynolds number is 1.84, not the creeping flow that Darcy's law and a frozen velocity field assume
- `tracer_transport__peclet_2__injection_continuous_supply` (incomplete): the step budget stopped this run after 0.52 of the 2.16 pore-volume crossings asked for; the pore Reynolds number is 1.84, not the creeping flow that Darcy's law and a frozen velocity field assume
- `tracer_transport__peclet_2__injection_pulse` (incomplete): the step budget stopped this run after 0.52 of the 2.16 pore-volume crossings asked for; the pore Reynolds number is 1.84, not the creeping flow that Darcy's law and a frozen velocity field assume
- `tracer_transport__peclet_400__injection_continuous_supply` (qualitative): the pore Reynolds number is 1.84, not the creeping flow that Darcy's law and a frozen velocity field assume
- `tracer_transport__peclet_400__injection_pulse` (qualitative): the pore Reynolds number is 1.84, not the creeping flow that Darcy's law and a frozen velocity field assume
- `tracer_transport__tracer_diffusive` (incomplete): the step budget stopped this run after 0.281 of the 2.16 pore-volume crossings asked for; the pore Reynolds number is 1.84, not the creeping flow that Darcy's law and a frozen velocity field assume
- `tracer_transport__tracer_front` (qualitative): the pore Reynolds number is 1.84, not the creeping flow that Darcy's law and a frozen velocity field assume
- `tracer_transport__tracer_pulse` (qualitative): the pore Reynolds number is 1.84, not the creeping flow that Darcy's law and a frozen velocity field assume

## Trend checks across the sweeps

- PASS: Cylinder: wake oscillation dies out below Re 47 and is sustained above (last-quarter swing over first)
  - {"40": 0.159, "80": 2.599, "180": 0.881, "400": 0.855, "1200": 1.079}
- PASS: Cylinder: Strouhal number 0.15 to 0.26 for Re 180 to 1200
  - {"40": 0.14, "80": 0.17, "180": 0.204, "400": 0.228, "1200": 0.242}
- FAIL: Airfoil: lift coefficient monotone in angle up to 14 degrees and changes sign through 0
  - {"-14": -0.137, "-6": -0.468, "0": -0.002, "6": 0.463, "14": 0.131, "20": -0.032}
- PASS: Airfoil: lift antisymmetric in angle, |C_l(a) + C_l(-a)| within 5 % of |C_l(a)|
  - {"6": "-1.2 %", "14": "-4.9 %"}
- PASS: Porous flow: permeability rises with porosity at fixed grain size
  - {"0.035": {"0.45": "1.03", "0.6": "31.8", "0.75": "131", "0.85": "296"}, "0.02": {"0.45": "0.611", "0.6": "5.41", "0.75": "29.5", "0.85": "124"}, "0.07": {"0.45": "13.3", "0.6": "45.1", "0.75": "292", "0.85": "551"}}
- PASS: Porous flow: permeability rises with grain size at fixed porosity
  - {"0.45": {"0.02": "0.611", "0.035": "1.03", "0.07": "13.3"}, "0.6": {"0.02": "5.41", "0.035": "31.8", "0.07": "45.1"}, "0.75": {"0.02": "29.5", "0.035": "131", "0.07": "292"}, "0.85": {"0.02": "124", "0.035": "296", "0.07": "551"}}
- PASS: Tracer: mass balance closes within 2 % in every case
  - worst 1.06e-12
- PASS: Tracer: dispersion over molecular diffusion rises with the Peclet number (pulse)
  - {"0.5": 0.84, "2.0": 3.64, "20.0": 27.49, "100.0": 161.78, "400.0": 597.21}
- PASS: Heated layer: Nusselt number 1 (within 5 %) with buoyancy off
  - 1.0
- FAIL: Heated layer: Nusselt number (final-frame readout of the app) rises with buoyancy
  - {"0.0": 1.0, "0.0015": 85.77, "0.003": 116.84, "0.006": 250.85, "0.012": 185.58}
- PASS: Heated layer: kinetic energy (mean of the second half) rises with buoyancy
  - {"0.0": "0", "0.0015": "0.0321", "0.003": "0.0721", "0.006": "0.169", "0.012": "0.338"}
- PASS: Rayleigh-Taylor: time for the mixing zone to reach half the box scales as A^(-1/2) (within 10 %)
  - {"time to half width, by modes then Atwood": {"0": {"0.2": 3354.0, "0.5": 2106.0, "0.7": 1794.0, "1.0": 1482.0}, "3": {"0.2": 3822.0, "0.5": 2418.0, "0.7": 2028.0, "1.0": 1716.0}}, "worst deviation from A^(-1/2)": 0.012}
- PASS: rising_smoke: kinetic energy (mean of the second half) rises with buoyancy at fixed confinement
  - {"0": {"0.001": "0.0689", "0.0022": "0.105", "0.005": "0.295"}, "7": {"0.001": "0.121", "0.0022": "0.2", "0.005": "0.249"}, "18": {"0.001": "0.198", "0.0022": "0.258", "0.005": "0.298"}}
- PASS: candle_flame: kinetic energy (mean of the second half) rises with buoyancy at fixed zst
  - {"0.1": {"0.012": "0.122", "0.025": "0.184"}, "0.16": {"0.012": "0.0966", "0.025": "0.188"}, "0.25": {"0.012": "0.124", "0.025": "0.158"}}
- PASS: chimney_plume: kinetic energy (mean of the second half) rises with buoyancy in calm air (wind 0)
  - {"0.0": {"0.002": "0.132", "0.005": "0.191", "0.01": "0.256"}, "0.15": {"0.002": "0.149", "0.005": "0.231", "0.01": "0.273"}, "0.3": {"0.002": "0.2", "0.005": "0.234", "0.01": "0.285"}, "0.55": {"0.002": "0.616", "0.005": "0.54", "0.01": "0.463"}}
- PASS: Sod tube: density error against the exact solution falls with resolution
  - {"Low (fast)": 0.0026, "Medium": 0.00178, "High": 0.00144, "Ultra (slow)": 0.00117}
- PASS: Open blast: final shock radius rises with the pressure ratio
  - {"20.0": 190.2, "50.0": 239.7, "140.0": 307.6, "400.0": 393.9}
- PASS: Shock-bubble: final kinetic energy rises with the Mach number at fixed density ratio
  - {"3.0": {"1.2": "3.51e+04", "1.6": "4.85e+05", "2.5": "4.55e+06"}, "0.14": {"1.2": "3.83e+04", "1.6": "5.13e+05", "2.5": "4.65e+06"}, "0.5": {"1.2": "3.72e+04", "1.6": "5.03e+05", "2.5": "4.62e+06"}}
- PASS: Still water: zero speed-limiter events at every particle count
  - {"3000": 0.0, "600": 0.0, "12000": 0.0}
- PASS: Dam break: peak kinetic energy rises with column height at fixed width
  - {"1.0": {"1.0": "2.02e+03", "2.0": "1.01e+04", "3.0": "2.49e+04"}, "0.5": {"1.0": "1.07e+03", "2.0": "5.06e+03", "3.0": "1.29e+04"}, "2.0": {"1.0": "3.01e+03", "2.0": "1.45e+04", "3.0": "3.54e+04"}}
- PASS: kelvin_helmholtz: final enstrophy falls with viscosity
  - {"0.015": {"1e-05": "1.01", "8e-05": "0.912", "0.0004": "0.699"}, "0.0333333": {"1e-05": "0.673", "8e-05": "0.639", "0.0004": "0.561"}, "0.08": {"1e-05": "0.381", "8e-05": "0.368", "0.0004": "0.347"}}
- PASS: decaying_turbulence: final enstrophy falls with viscosity
  - {"0": {"1e-05": "0.136", "8e-05": "0.0607", "0.0004": "0.013"}}
- PASS: Taylor-Green: kinetic-energy decay within 5 % of exp(-4 nu t)
  - {"0.0004": "ratio 0.9239 exact 0.9239 rel err 1.86e-12", "1e-05": "ratio 0.9980 exact 0.9980 rel err 8.02e-13", "0.0001": "ratio 0.9804 exact 0.9804 rel err 1.94e-12"}
- PASS: Dye: final variance falls with diffusion at fixed stirring
  - {"1.0": {"0.0": "0.0128", "0.0003": "0.004", "0.001": "0.000975"}, "0.0": {"0.0": "0.249", "0.0003": "0.0752", "0.001": "0.00744"}, "0.3": {"0.0": "0.114", "0.0003": "0.03", "0.001": "0.00434"}}
- PASS: Dye: final variance falls with stirring at fixed diffusion
- FAIL: Gray-Scott: every named regime ends with a pattern (coverage between 1 % and 99 %)
  - {"Spots": 8.1, "Stripes": 17.1, "Maze": 34.4, "Mitosis": 0.1, "Coral": 3.7, "Waves": 8.5}
