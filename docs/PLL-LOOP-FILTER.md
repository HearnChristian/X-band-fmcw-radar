# PLL Loop Filter Design (Rev-E)

Chirp synthesizer loop: ADF4159 (PFD + charge pump) locks the BGT24LTR11
VCO through its ÷16 divider output. This note replaces the schematic-capture
placeholder values with a computed design (`tools/pll_loop_filter.py`).

## Loop parameters

| Parameter | Value | Source |
|---|---|---|
| f_REF = f_PFD | 50 MHz | ECS-TXO-2520MV-500 (Y1), R-counter = 1 |
| f_VCO | 24.05–24.25 GHz | BGT24LTR11 DS Table 5 (R_TUNE = 16 kΩ) |
| N (VCO→PFD) | 483 | includes BGT24 ÷16 (ADF4159 INT ≈ 30.2, frac) |
| Kvco | 720 MHz/V typ, 2000 MHz/V max | BGT24LTR11 DS Table 5 |
| V_TUNE range | 0.7–2.5 V | BGT24LTR11 DS; ADF4159 CP compliance 0.5–2.8 V ✓ |
| Icp | 2.5 mA design point | RSET = 5.1 kΩ → 0.31–5 mA in 16 steps |

## Topology fix

The captured filter was an all-shunt RC ladder (C17 ∥ → R3 → C18 ∥ → R4 →
C19 ∥ → V_TUNE). A current-driven RC ladder has **no finite zero at the
output node**, so a type-2 loop built on it is unconditionally unstable —
confirmed by exact network analysis. **Rev-E moves R4's input from the
R3/C18 junction to the charge-pump node**, restoring the standard 3rd-order
passive filter: the R3+C18 series branch at CPOUT provides the stabilizing
zero, R4/C19 form the spur-filter pole.

```
CPOUT ──┬────┬───── R4 (560R) ───┬──── V_TUNE
        │    │                   │
      C17   R3 (270R)          C19 (270pF)
     910pF   │                   │
        │  C18 (15nF)           GND
       GND   │
            GND
```

## Values and verified performance (exact ladder analysis)

C17 = 910 pF, R3 = 270 Ω, C18 = 15 nF, R4 = 560 Ω, C19 = 270 pF (E12/E24).

| Corner | f_c | Phase margin |
|---|---|---|
| Kvco typ, Icp 2.5 mA (design) | 146 kHz | 52° |
| Kvco max, Icp 2.5 mA | 331 kHz | 36° |
| Kvco typ, Icp 1.25 mA | 81 kHz | 51° |
| Kvco max, Icp 1.25 mA | 193 kHz | 49° |
| Kvco typ, Icp 5 mA | 259 kHz | 43° |

150 kHz sits near the noise-optimal crossover (ADF4159 in-band floor
≈ −90 dBc/Hz at N = 483 meets the VCO's −80 dBc/Hz @100 kHz, −20 dB/dec
a little above 300 kHz) and comfortably tracks the FMCW ramp
(250 MHz / 1 ms ≈ 0.35 V/ms on V_TUNE).

## Firmware notes

- Program Icp = 2.5 mA (setting 8/16). If lab tuning shows Kvco at the
  high end, drop to 1.25 mA rather than raising the bandwidth.
- R-counter = 1, reference doubler/divider off (f_PFD = 50 MHz).
- Keep **VCC_PTAT = 0 V**: the BGT24 divider is ÷16 only when V_PTAT is
  disabled; at 3.3 V it becomes ÷8192 and the loop constants are wrong.
- MUXOUT is open-drain 1.8 V logic (R22 pull-up to +1V8, Rev-D).
