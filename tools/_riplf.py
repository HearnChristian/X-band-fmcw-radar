import pcbnew
b = pcbnew.LoadBoard("/home/christian-thomas-hearn/Desktop/X-BAND FMCW RADAR/Radar1/Radar1.kicad_pcb")
codes = {b.FindNet(n).GetNetCode() for n in ("LF_A", "LF_B")}
_keep, k = [], 0
for t in list(b.Tracks()):
    if t.GetNetCode() in codes:
        _keep.append(t); b.Remove(t); k += 1
print(f"ripped {k} LF_A/LF_B objects")
pcbnew.ZONE_FILLER(b).Fill(b.Zones())
pcbnew.SaveBoard("/home/christian-thomas-hearn/Desktop/X-BAND FMCW RADAR/Radar1/Radar1.kicad_pcb", b)
