import pcbnew
b = pcbnew.LoadBoard("/home/christian-thomas-hearn/Desktop/X-BAND FMCW RADAR/Radar1/Radar1.kicad_pcb")
code = b.FindNet("IFQ_IN").GetNetCode()
_keep, k = [], 0
for t in list(b.Tracks()):
    if t.GetNetCode() == code:
        _keep.append(t); b.Remove(t); k += 1
print(f"ripped {k} IFQ_IN objects")
pcbnew.ZONE_FILLER(b).Fill(b.Zones())
pcbnew.SaveBoard("/home/christian-thomas-hearn/Desktop/X-BAND FMCW RADAR/Radar1/Radar1.kicad_pcb", b)
