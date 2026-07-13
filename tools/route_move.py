"""Surgical placement nudge: move the parts plugging the two capacity zones,
sweep their orphaned copper, and leave healing to tools/route_finish.py.

C19 (loop-filter cap) blocks the U1-south escape slot; R22/R15 sit in the
U2->U7 SPI corridor. Each move is validated against courtyards, the RF
GCPW/fence corridors and the board edge; alternates are tried in order.
"""
import math, pcbnew
from pcbnew import ToMM, FromMM, VECTOR2I

BOARD = "/home/christian-thomas-hearn/Desktop/X-BAND FMCW RADAR/Radar1/Radar1.kicad_pcb"
b = pcbnew.LoadBoard(BOARD)
F, B = pcbnew.F_Cu, pcbnew.B_Cu

MOVES = {   # ref -> search rectangle (x0, y0, x1, y1), nearest legal wins
    "C19": (66.0, 61.5, 76.5, 71.0),
    "R22": (85.5, 66.8, 96.0, 72.5),
    "R15": (89.0, 66.8, 99.5, 72.5),
}
OX, OY, BW, BH = 60.0, 40.0, 66.0, 46.0

rf_segs = []
for t in b.Tracks():
    if not isinstance(t, pcbnew.PCB_VIA) and t.GetNetname() in \
            ("RF_TX", "ANT_TX", "ANT_RX"):
        s, e = t.GetStart(), t.GetEnd()
        rf_segs.append((ToMM(s.x), ToMM(s.y), ToMM(e.x), ToMM(e.y)))

def segd(px, py, s):
    x0, y0, x1, y1 = s
    dx, dy = x1-x0, y1-y0
    L2 = dx*dx + dy*dy
    tt = 0.0 if L2 == 0 else max(0.0, min(1.0, ((px-x0)*dx+(py-y0)*dy)/L2))
    return math.hypot(px-(x0+tt*dx), py-(y0+tt*dy))

fps = {fp.GetReference(): fp for fp in b.GetFootprints()}

def fp_bb(fp):
    try:    return fp.GetBoundingBox(False)      # no text
    except TypeError:
        try: return fp.GetBoundingBox(False, False)
        except TypeError: return fp.GetBoundingBox()

def bbox_at(fp, x, y):
    bb = fp_bb(fp)
    pos = fp.GetPosition()
    dx, dy = x - ToMM(pos.x), y - ToMM(pos.y)
    return (ToMM(bb.GetLeft()) + dx, ToMM(bb.GetTop()) + dy,
            ToMM(bb.GetRight()) + dx, ToMM(bb.GetBottom()) + dy)

def legal(ref, x, y):
    r = bbox_at(fps[ref], x, y)
    if r[0] < OX+1.0 or r[1] < OY+1.0 or r[2] > OX+BW-1.0 or r[3] > OY+BH-2.0:
        return "edge"
    for oref, ofp in fps.items():
        if oref == ref: continue
        ob = fp_bb(ofp)
        o = (ToMM(ob.GetLeft()), ToMM(ob.GetTop()),
             ToMM(ob.GetRight()), ToMM(ob.GetBottom()))
        if r[0]-0.25 < o[2] and r[2]+0.25 > o[0] and \
           r[1]-0.25 < o[3] and r[3]+0.25 > o[1]:
            return oref
    cx, cy = (r[0]+r[2])/2, (r[1]+r[3])/2
    half = max(r[2]-r[0], r[3]-r[1]) / 2
    if any(segd(cx, cy, s) < half + 0.9 for s in rf_segs):
        return "RF"
    return None

moved_nets = set()
for ref, (sx0, sy0, sx1, sy1) in MOVES.items():
    fp = fps[ref]
    pos = fp.GetPosition()
    ox_, oy_ = ToMM(pos.x), ToMM(pos.y)
    cands = sorted(((sx0 + 0.5*i - ox_)**2 + (sy0 + 0.5*j - oy_)**2,
                    sx0 + 0.5*i, sy0 + 0.5*j)
                   for i in range(int((sx1-sx0)/0.5)+1)
                   for j in range(int((sy1-sy0)/0.5)+1))
    placed = False
    blockers = {}
    for _, x, y in cands:
        why = legal(ref, x, y)
        if why is None:
            fp.SetPosition(VECTOR2I(FromMM(x), FromMM(y)))
            print(f"moved {ref} -> ({x},{y})")
            placed = True
            break
        blockers[why] = blockers.get(why, 0) + 1
    if not placed:
        print(f"NO LEGAL SPOT for {ref}; blockers: {blockers}")
        continue
    for p in fp.Pads():
        n = p.GetNetname()
        if n and n != "GND" and not n.startswith("unconnected"):
            moved_nets.add(n)

# orphan sweep: copper fragments of moved nets left without pad contact
# (their old stubs/attachments) would block the freed corridors
def pad_rects_of(code):
    out = []
    for fp in b.GetFootprints():
        for p in fp.Pads():
            if p.GetNetCode() == code:
                bb = p.GetBoundingBox()
                out.append((ToMM(bb.GetLeft()), ToMM(bb.GetTop()),
                            ToMM(bb.GetRight()), ToMM(bb.GetBottom())))
    return out

_keep = []
swept = 0
for n in sorted(moved_nets):
    code = b.FindNet(n).GetNetCode()
    prects = pad_rects_of(code)
    # iteratively remove tracks/vias not touching any pad nor surviving copper
    changed = True
    while changed:
        changed = False
        objs = [t for t in b.Tracks() if t.GetNetCode() == code]
        keepset = []
        for t in objs:
            if isinstance(t, pcbnew.PCB_VIA):
                pos = t.GetPosition()
                pts = [(ToMM(pos.x), ToMM(pos.y))]
                hw = ToMM(t.GetWidth())/2
            else:
                s, e = t.GetStart(), t.GetEnd()
                pts = [(ToMM(s.x), ToMM(s.y)), (ToMM(e.x), ToMM(e.y))]
                hw = ToMM(t.GetWidth())/2
            touch_pad = any(r[0]-hw+0.05 <= x <= r[2]+hw-0.05 and
                            r[1]-hw+0.05 <= y <= r[3]+hw-0.05
                            for r in prects for (x, y) in pts)
            keepset.append((t, touch_pad))
        # BFS from pad-touching objects through object-object contact
        def obj_pts(t):
            if isinstance(t, pcbnew.PCB_VIA):
                pos = t.GetPosition()
                return [(ToMM(pos.x), ToMM(pos.y))], ToMM(t.GetWidth())/2, None
            s, e = t.GetStart(), t.GetEnd()
            lay = 0 if t.GetLayer() == F else (1 if t.GetLayer() == B else 2)
            return [(ToMM(s.x), ToMM(s.y)), (ToMM(e.x), ToMM(e.y))], \
                   ToMM(t.GetWidth())/2, lay
        alive = {id(t) for t, tp in keepset if tp}
        grew = True
        while grew:
            grew = False
            for t, _ in keepset:
                if id(t) in alive: continue
                pts, hw, lay = obj_pts(t)
                for t2, _ in keepset:
                    if id(t2) not in alive: continue
                    pts2, hw2, lay2 = obj_pts(t2)
                    if lay is not None and lay2 is not None and \
                       lay != 2 and lay2 != 2 and lay != lay2: continue
                    if any(math.hypot(a-c, b_-d) <= hw+hw2-0.05
                           for a, b_ in pts for c, d in pts2):
                        alive.add(id(t)); grew = True; break
        for t, _ in keepset:
            if id(t) not in alive:
                _keep.append(t); b.Remove(t); swept += 1; changed = True
print(f"orphan copper swept: {swept} objects on {sorted(moved_nets)}")

pcbnew.ZONE_FILLER(b).Fill(b.Zones())
pcbnew.SaveBoard(BOARD, b)
print("saved")
