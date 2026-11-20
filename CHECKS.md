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

- `porous_flow__porosity_0p6__grain_0p07` (qualitative): the pore Reynolds number is 1.97, not the creeping flow that Darcy's law and a frozen velocity field assume
- `porous_flow__porosity_0p75__grain_0p035` (qualitative): the pore Reynolds number is 2.31, not the creeping flow that Darcy's law and a frozen velocity field assume
- `porous_flow__porosity_0p75__grain_0p07` (qualitative): the pore Reynolds number is 11.6, not the creeping flow that Darcy's law and a frozen velocity field assume; the sample was asked for a porosity of 0.75 and packed to 0.736
- `porous_flow__porosity_0p85__grain_0p02` (qualitative): the pore Reynolds number is 1.03, not the creeping flow that Darcy's law and a frozen velocity field assume
- `porous_flow__porosity_0p85__grain_0p035` (qualitative): the pore Reynolds number is 5.53, not the creeping flow that Darcy's law and a frozen velocity field assume
- `porous_flow__porosity_0p85__grain_0p07` (qualitative): the pore Reynolds number is 21.5, not the creeping flow that Darcy's law and a frozen velocity field assume
- `tracer_transport__peclet_0p5__injection_continuous_supply` (incomplete): the step budget stopped this run after 0.253 of the 2.16 pore-volume crossings asked for
- `tracer_transport__peclet_0p5__injection_pulse` (incomplete): the step budget stopped this run after 0.253 of the 2.16 pore-volume crossings asked for
- `tracer_transport__peclet_2__injection_continuous_supply` (incomplete): the step budget stopped this run after 0.864 of the 2.16 pore-volume crossings asked for
- `tracer_transport__peclet_2__injection_pulse` (incomplete): the step budget stopped this run after 0.864 of the 2.16 pore-volume crossings asked for
- `tracer_transport__tracer_diffusive` (incomplete): the step budget stopped this run after 0.478 of the 2.16 pore-volume crossings asked for

## Trend checks across the sweeps

- PASS: Cylinder: wake oscillation dies out below Re 47 and is sustained above (last-quarter swing over first)
  - {"40": 0.08, "80": 1.244, "180": 0.899, "400": 0.836, "1200": 1.038}
- PASS: Cylinder: Strouhal number 0.15 to 0.26 for Re 180 to 1200
  - {"40": 0.14, "80": 0.171, "180": 0.204, "400": 0.228, "1200": 0.243}
- FAIL: Airfoil: lift coefficient monotone in angle up to 14 degrees and changes sign through 0
  - {"-14": -0.311, "-6": -0.445, "0": -0.003, "6": 0.439, "14": 0.303, "20": 0.283}
- PASS: Airfoil: lift antisymmetric in angle, |C_l(a) + C_l(-a)| within 5 % of |C_l(a)|
  - {"6": "-1.5 %", "14": "-2.7 %"}
- PASS: Porous flow: permeability rises with porosity at fixed grain size
  - {"0.035": {"0.45": "0.313", "0.6": "17.2", "0.75": "84.3", "0.85": "230"}, "0.02": {"0.45": "0.326", "0.6": "2.83", "0.75": "16.7", "0.85": "80.6"}, "0.07": {"0.45": "6.77", "0.6": "28.7", "0.75": "210", "0.85": "445"}}
- FAIL: Porous flow: permeability rises with grain size at fixed porosity
  - {"0.45": {"0.02": "0.326", "0.035": "0.313", "0.07": "6.77"}, "0.6": {"0.02": "2.83", "0.035": "17.2", "0.07": "28.7"}, "0.75": {"0.02": "16.7", "0.035": "84.3", "0.07": "210"}, "0.85": {"0.02": "80.6", "0.035": "230", "0.07": "445"}}
- PASS: Tracer: mass balance closes within 2 % in every case
  - worst 7.61e-13
- PASS: Tracer: dispersion over molecular diffusion rises with the Peclet number (pulse)
  - {"0.5": 1.04, "2.0": 2.25, "20.0": 28.19, "100.0": 127.43, "400.0": 658.24}
- PASS: Heated layer: Nusselt number 1 (within 5 %) with buoyancy off
  - 1.0
- FAIL: Heated layer: Nusselt number (final-frame readout of the app) rises with buoyancy
  - {"0.0": 1.0, "0.0015": 51.36, "0.003": 56.29, "0.006": 144.3, "0.012": 126.03}
- PASS: Heated layer: kinetic energy (mean of the second half) rises with buoyancy
  - {"0.0": "0", "0.0015": "0.0247", "0.003": "0.0525", "0.006": "0.111", "0.012": "0.249"}
- PASS: Rayleigh-Taylor: time for the mixing zone to reach half the box scales as A^(-1/2) (within 10 %)
  - {"time to half width, by modes then Atwood": {"0": {"0.2": 2808.0, "0.5": 1794.0, "0.7": 1560.0, "1.0": 1248.0}, "3": {"0.2": 3354.0, "0.5": 2106.0, "0.7": 1794.0, "1.0": 1482.0}}, "worst deviation from A^(-1/2)": 0.039}
- PASS: rising_smoke: kinetic energy (mean of the second half) rises with buoyancy at fixed confinement
  - {"0": {"0.001": "0.0705", "0.0022": "0.0792", "0.005": "0.252"}, "7": {"0.001": "0.128", "0.0022": "0.191", "0.005": "0.201"}, "18": {"0.001": "0.19", "0.0022": "0.223", "0.005": "0.338"}}
- PASS: candle_flame: kinetic energy (mean of the second half) rises with buoyancy at fixed zst
  - {"0.1": {"0.012": "0.147", "0.025": "0.197"}, "0.16": {"0.012": "0.0857", "0.025": "0.145"}, "0.25": {"0.012": "0.0496", "0.025": "0.168"}}
- PASS: chimney_plume: kinetic energy (mean of the second half) rises with buoyancy in calm air (wind 0)
  - {"0.0": {"0.002": "0.15", "0.005": "0.169", "0.01": "0.273"}, "0.15": {"0.002": "0.129", "0.005": "0.129", "0.01": "0.174"}, "0.3": {"0.002": "0.244", "0.005": "0.226", "0.01": "0.253"}, "0.55": {"0.002": "0.446", "0.005": "0.456", "0.01": "0.484"}}
- PASS: Sod tube: density error against the exact solution falls with resolution
  - {"Low (fast)": 0.0026, "Medium": 0.00178, "High": 0.00144, "Ultra (slow)": 0.00117}
- PASS: Open blast: final shock radius rises with the pressure ratio
  - {"20.0": 172.1, "50.0": 213.2, "140.0": 271.3, "400.0": 343.6}
- PASS: Shock-bubble: final kinetic energy rises with the Mach number at fixed density ratio
  - {"3.0": {"1.2": "2.54e+04", "1.6": "3.39e+05", "2.5": "2.54e+06"}, "0.14": {"1.2": "2.71e+04", "1.6": "3.46e+05", "2.5": "2.6e+06"}, "0.5": {"1.2": "2.65e+04", "1.6": "3.42e+05", "2.5": "2.59e+06"}}
- PASS: Still water: zero speed-limiter events at every particle count
  - {"3000": 0.0, "600": 0.0, "12000": 0.0}
- PASS: Dam break: peak kinetic energy rises with column height at fixed width
  - {"1.0": {"1.0": "2.02e+03", "2.0": "1.01e+04", "3.0": "2.49e+04"}, "0.5": {"1.0": "1.07e+03", "2.0": "5.06e+03", "3.0": "1.29e+04"}, "2.0": {"1.0": "3.01e+03", "2.0": "1.45e+04", "3.0": "3.54e+04"}}
- PASS: kelvin_helmholtz: final enstrophy falls with viscosity
  - {"0.015": {"1e-05": "1.01", "8e-05": "0.91", "0.0004": "0.699"}, "0.0333333": {"1e-05": "0.675", "8e-05": "0.639", "0.0004": "0.561"}, "0.08": {"1e-05": "0.381", "8e-05": "0.367", "0.0004": "0.347"}}
- PASS: decaying_turbulence: final enstrophy falls with viscosity
  - {"0": {"1e-05": "0.136", "8e-05": "0.0604", "0.0004": "0.013"}}
- PASS: Taylor-Green: kinetic-energy decay within 5 % of exp(-4 nu t)
  - {"0.0004": "ratio 0.9239 exact 0.9239 rel err 9.35e-13", "1e-05": "ratio 0.9980 exact 0.9980 rel err 4.71e-14", "0.0001": "ratio 0.9804 exact 0.9804 rel err 1.28e-12"}
- PASS: Dye: final variance falls with diffusion at fixed stirring
  - {"1.0": {"0.0": "0.00982", "0.0003": "0.00347", "0.001": "0.000942"}, "0.0": {"0.0": "0.249", "0.0003": "0.0752", "0.001": "0.00745"}, "0.3": {"0.0": "0.101", "0.0003": "0.0281", "0.001": "0.00412"}}
- PASS: Dye: final variance falls with stirring at fixed diffusion
- FAIL: Gray-Scott: every named regime ends with a pattern (coverage between 1 % and 99 %)
  - {"Spots": 18.6, "Stripes": 17.0, "Maze": 34.3, "Mitosis": 0.2, "Coral": 4.3, "Waves": 8.5}
