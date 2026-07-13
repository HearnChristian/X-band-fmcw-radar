import math, cmath

FPFD, FVCO = 50e6, 24.15e9
N = FVCO / FPFD
KV_T, KV_M = 720e6, 2000e6
ICP = 2.5e-3
FC, PM = 150e3, 52.0
G3 = 7.0                       # third pole at G3*fc

# corrected topology: CP node A: C17 shunt + (R3 series C18) to GND;
# R4 from A to node C; C19 shunt at C -> VTUNE
def zfil(f, C17, R3, C18, R4, C19):
    s = 1j*2*math.pi*f
    zA = 1/(s*C17 + 1/(R3 + 1/(s*C18)))
    # Vtune/I = zA * divider(R4, C19) with C19 loading zA:
    # exact 2-node: node A: I = VA*(sC17 + 1/(R3+1/sC18)) + (VA-VC)/R4
    #              node C: (VA-VC)/R4 = VC*sC19
    y1 = s*C17 + 1/(R3 + 1/(s*C18))
    g4 = 1/R4
    # [y1+g4, -g4; -g4, g4+sC19][VA,VC]=[I,0]
    det = (y1+g4)*(g4+s*C19) - g4*g4
    return g4/det                     # VC/I

def loop(f, kv, icp, *e):
    s = 1j*2*math.pi*f
    return (icp/(2*math.pi))*zfil(f,*e)*(2*math.pi*kv)/(s*N)

def fc_pm(kv, icp, *e):
    lo, hi = 1e3, 30e6
    for _ in range(90):
        mid = math.sqrt(lo*hi)
        if abs(loop(mid, kv, icp, *e)) > 1: lo = mid
        else: hi = mid
    fc = math.sqrt(lo*hi)
    ph = math.degrees(cmath.phase(loop(fc, kv, icp, *e)))
    if ph > 0: ph -= 360
    return fc, 180 + ph

wc = 2*math.pi*FC
def build(alpha):
    C18 = 1e-9
    C17 = C18/(alpha*alpha - 1)     # T1 = T2/alpha^2
    R3 = alpha/(wc*C18)             # T2 = alpha/wc
    R4 = 2*R3
    C19 = 1/(wc*G3*R4)
    k = abs(loop(FC, KV_T, ICP, C17, R3, C18, R4, C19))
    return C17*k, R3/k, C18*k, R4/k, C19*k

lo, hi = 1.3, 20.0
for _ in range(80):
    a = math.sqrt(lo*hi)
    fc, pm = fc_pm(KV_T, ICP, *build(a))
    if pm < PM: lo = a
    else: hi = a
e = build(math.sqrt(lo*hi))
fc, pm = fc_pm(KV_T, ICP, *e)
print(f"ideal: C17={e[0]*1e12:.0f}pF R3={e[1]:.0f}R C18={e[2]*1e9:.2f}nF "
      f"R4={e[3]:.0f}R C19={e[4]*1e12:.0f}pF  (fc={fc/1e3:.1f}k pm={pm:.1f})")

def e24(x):
    ser=[1.0,1.1,1.2,1.3,1.5,1.6,1.8,2.0,2.2,2.4,2.7,3.0,3.3,3.6,3.9,4.3,
         4.7,5.1,5.6,6.2,6.8,7.5,8.2,9.1]
    ex = math.floor(math.log10(x))
    return min(ser, key=lambda v: abs(v-x/10**ex))*10**ex
vals = tuple(e24(v) for v in e)
print(f"E24:   C17={vals[0]*1e12:.0f}pF R3={vals[1]:.0f}R C18={vals[2]*1e9:.2f}nF "
      f"R4={vals[3]:.0f}R C19={vals[4]*1e12:.0f}pF")
for kv, tag in ((KV_T,"Kvco typ 720M/V "),(KV_M,"Kvco max 2000M/V")):
    fc, pm = fc_pm(kv, ICP, *vals)
    print(f"  {tag}: fc={fc/1e3:6.0f} kHz  PM={pm:5.1f} deg")
for icp, tag in ((1.25e-3,"Icp 1.25mA      "),(5e-3,"Icp 5.00mA      ")):
    fc, pm = fc_pm(KV_T, icp, *vals)
    print(f"  {tag}: fc={fc/1e3:6.0f} kHz  PM={pm:5.1f} deg")
fcw, pmw = fc_pm(KV_M, 5e-3, *vals)
print(f"  worst (2G/V+5mA) : fc={fcw/1e3:6.0f} kHz  PM={pmw:5.1f} deg")
fcb, pmb = fc_pm(KV_M, 1.25e-3, *vals)
print(f"  (2G/V+1.25mA)    : fc={fcb/1e3:6.0f} kHz  PM={pmb:5.1f} deg")
