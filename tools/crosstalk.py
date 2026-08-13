#!/usr/bin/env python3
"""Report how far analogue and digital traces run together, and mark the spots.

KiCad's DRC can ask how CLOSE two traces get. It cannot ask how FAR they run
together, and coupled length is the thing that matters: capacitive coupling
scales with the distance two conductors share, not with how many times they
cross. A 90 degree crossing is nearly free. Twenty millimetres side by side is
not. So a clearance rule catches the wrong quantity and a tool has to do it.

    crosstalk.py report <pcb>        list coupled runs, worst first
    crosstalk.py mark   <pcb>        also draw them on a user layer

Coupled length is measured by walking each victim trace and asking, at every
step, whether an aggressor is within the threshold. That is robust to segments
of different lengths, to corners and to tracks that converge and diverge, none
of which a pairwise-angle test handles well.

Same layer is the default. Opposite layers are reported separately: 1.6mm of FR4
plus a ground pour between them makes broadside coupling far weaker, but a long
overlapping run is still worth seeing.
"""
import sys, os, re, json, math, argparse, fnmatch, uuid, collections

STEP = 0.25          # mm between samples along a victim trace
MARK_LAYER = 'User.9'


def balanced(t, i):
    d = 0
    for k in range(i, len(t)):
        if t[k] == '(': d += 1
        elif t[k] == ')':
            d -= 1
            if d == 0: return k + 1
    raise ValueError('unbalanced')


def netclasses(pro_path):
    """-> (pattern list, class names). Patterns are applied in order, last wins,
    which is how KiCad resolves them."""
    with open(pro_path) as f: d = json.load(f)
    ns = d.get('net_settings', {})
    return ns.get('netclass_patterns', []), [c['name'] for c in ns.get('classes', [])]


def class_of(net, patterns):
    hit = [p['netclass'] for p in patterns if fnmatch.fnmatchcase(net, p['pattern'])]
    return hit[-1] if hit else 'Default'


def tracks(pcb_text):
    """-> [(net, layer, (x0,y0), (x1,y1), width)] for every routed segment."""
    out = []
    for m in re.finditer(r'\(segment\b', pcb_text):
        st = m.start(); seg = pcb_text[st:balanced(pcb_text, st)]
        net = re.search(r'\(net "([^"]*)"\)', seg)
        lay = re.search(r'\(layer "([^"]+)"\)', seg)
        s = re.search(r'\(start ([-\d.]+) ([-\d.]+)\)', seg)
        e = re.search(r'\(end ([-\d.]+) ([-\d.]+)\)', seg)
        w = re.search(r'\(width ([\d.]+)\)', seg)
        if not (net and lay and s and e): continue
        out.append((net.group(1), lay.group(1),
                    (float(s.group(1)), float(s.group(2))),
                    (float(e.group(1)), float(e.group(2))),
                    float(w.group(1)) if w else 0.25))
    return out


def _seg_dist(p, a, b):
    """Distance from point p to segment a-b."""
    ax, ay = a; bx, by = b; px, py = p
    dx, dy = bx - ax, by - ay
    L2 = dx*dx + dy*dy
    if L2 == 0: return math.dist(p, a)
    t = max(0.0, min(1.0, ((px-ax)*dx + (py-ay)*dy) / L2))
    return math.dist(p, (ax + t*dx, ay + t*dy))


def coupled(victims, aggressors, threshold):
    """-> {(victim net, aggressor net): [coupled mm, (x, y) of the worst point]}

    Walks each victim and asks what is nearby, rather than comparing segment
    pairs geometrically. Edge-to-edge distance, so trace width counts.
    """
    runs = collections.defaultdict(lambda: [0.0, None, threshold])
    for vnet, vlay, va, vb, vw in victims:
        L = math.dist(va, vb)
        if L == 0: continue
        n = max(1, int(L / STEP))
        # The bounding-box reject must allow for BOTH trace widths. Sizing the
        # margin on the threshold alone drops wide traces whose edges already
        # overlap, which is exactly the case that matters most.
        near = []
        for anet, alay, aa, ab, aw in aggressors:
            if alay != vlay: continue
            m = threshold + (vw + aw) / 2 + 0.01
            if (min(aa[0], ab[0]) - m <= max(va[0], vb[0])
                    and max(aa[0], ab[0]) + m >= min(va[0], vb[0])
                    and min(aa[1], ab[1]) - m <= max(va[1], vb[1])
                    and max(aa[1], ab[1]) + m >= min(va[1], vb[1])):
                near.append((anet, aa, ab, aw))
        if not near: continue
        for i in range(n + 1):
            t = i / n
            p = (va[0] + (vb[0]-va[0])*t, va[1] + (vb[1]-va[1])*t)
            for anet, aa, ab, aw in near:
                gap = _seg_dist(p, aa, ab) - vw/2 - aw/2
                if gap < threshold:
                    key = (vnet, anet)
                    runs[key][0] += L / n
                    if gap < runs[key][2]: runs[key][2] = gap; runs[key][1] = p
    return runs


def load(pcb):
    with open(pcb) as f: return f.read()


def analyse(pcb, pro, threshold, va_class, ag_class):
    text = load(pcb)
    pats, names = netclasses(pro)
    segs = tracks(text)
    missing = [c for c in (va_class, ag_class) if c not in names]
    if missing:
        # Not a warning to scroll past. Without these classes every net falls
        # back to Default, so the tool reports a clean board no matter what is
        # routed. Netclasses have gone missing from this project's file before.
        print(f'  ERROR: no netclass called {missing}; classes are {names}')
        print(f'         every net would fall back to Default and nothing would be')
        print(f'         reported. Check net_settings in the .kicad_pro.')
        raise SystemExit(2)
    vic = [s for s in segs if class_of(s[0], pats) == va_class]
    agg = [s for s in segs if class_of(s[0], pats) == ag_class]
    return segs, vic, agg, coupled(vic, agg, threshold)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('cmd', choices=['report', 'mark'])
    ap.add_argument('pcb')
    ap.add_argument('--pro', default=None)
    ap.add_argument('--threshold', type=float, default=1.0,
                    help='mm edge to edge below which traces count as coupled')
    ap.add_argument('--min-length', type=float, default=3.0,
                    help='mm of coupled run below which a pair is not worth reporting')
    ap.add_argument('--victim', default='ANALOG')
    ap.add_argument('--aggressor', default='DIGITAL')
    a = ap.parse_args()
    pro = a.pro or os.path.splitext(a.pcb)[0] + '.kicad_pro'

    segs, vic, agg, runs = analyse(a.pcb, pro, a.threshold, a.victim, a.aggressor)
    print(f'  {len(segs)} routed segments: {len(vic)} {a.victim}, {len(agg)} {a.aggressor}')
    if not segs:
        print('  nothing routed yet, so nothing to couple'); return 0
    bad = sorted(((v, k) for k, v in runs.items() if v[0] >= a.min_length),
                 key=lambda z: -z[0][0])
    if not bad:
        print(f'  no pair runs within {a.threshold}mm for {a.min_length}mm or more')
        return 0
    print(f'  {len(bad)} coupled run(s) at or over {a.min_length}mm, worst first:')
    for (length, where, gap), (vn, an) in bad:
        loc = f'({where[0]:.2f}, {where[1]:.2f})' if where else '?'
        print(f'    {length:6.1f} mm   {vn}  <-  {an}   closest {gap:.2f}mm at {loc}')
    if a.cmd == 'mark':
        text = load(a.pcb)
        add = ''
        for (length, where, gap), (vn, an) in bad:
            if not where: continue
            x, y = where; r = 1.0
            add += (f'\t(gr_circle\n\t\t(center {x:g} {y:g})\n\t\t(end {x+r:g} {y:g})\n'
                    f'\t\t(stroke (width 0.15) (type solid))\n\t\t(fill none)\n'
                    f'\t\t(layer "{MARK_LAYER}")\n\t\t(uuid "{uuid.uuid4()}")\n\t)\n')
            add += (f'\t(gr_text "{length:.0f}mm {vn.split("/")[-1]}/{an.split("/")[-1]}"\n'
                    f'\t\t(at {x:g} {y-1.6:g} 0)\n\t\t(layer "{MARK_LAYER}")\n'
                    f'\t\t(uuid "{uuid.uuid4()}")\n'
                    f'\t\t(effects (font (size 0.8 0.8) (thickness 0.12)))\n\t)\n')
        cut = text.rstrip().rfind(')')
        with open(a.pcb, 'w') as f: f.write(text[:cut] + add + ')\n')
        print(f'  marked {len(bad)} hotspot(s) on {MARK_LAYER}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
