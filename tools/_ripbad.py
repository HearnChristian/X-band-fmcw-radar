import math, pcbnew
from pcbnew import ToMM
b = pcbnew.LoadBoard("/home/christian-thomas-hearn/Desktop/X-BAND FMCW RADAR/Radar1/Radar1.kicad_pcb")
_keep, k = [], 0
codes = {b.FindNet(n).GetNetCode() for n in ("EE_CLK","ADF_TXDATA","IFB_INP","RFINB_N")}
vgg = b.FindNet("-VGG").GetNetCode()
for t in list(b.Tracks()):
    c = t.GetNetCode()
    if c in codes:
        _keep.append(t); b.Remove(t); k += 1
    elif c == vgg and not isinstance(t, pcbnew.PCB_VIA):
        s, e = t.GetStart(), t.GetEnd()
        mx, my = (ToMM(s.x)+ToMM(e.x))/2, (ToMM(s.y)+ToMM(e.y))/2
        if math.hypot(mx-76.6, my-73.6) < 1.0:
            _keep.append(t); b.Remove(t); k += 1
print(f"ripped {k} objects")
pcbnew.ZONE_FILLER(b).Fill(b.Zones())
pcbnew.SaveBoard("/home/christian-thomas-hearn/Desktop/X-BAND FMCW RADAR/Radar1/Radar1.kicad_pcb", b)
