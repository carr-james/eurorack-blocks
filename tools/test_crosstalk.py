#!/usr/bin/env python3
"""Tests for crosstalk.py.

The whole claim of the tool is that it distinguishes a long parallel run from a
crossing, because that is the distinction a clearance rule cannot make. If these
two cases score the same, the tool is worthless however pretty its output.

    python3 test_crosstalk.py <a routed-or-not .kicad_pcb> <its .kicad_pro>
"""
import sys, os, math, tempfile, shutil, uuid

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import crosstalk as X

PASS = FAIL = 0


def check(name, cond, detail=''):
    global PASS, FAIL
    if cond: PASS += 1; print(f'  ok    {name}')
    else:    FAIL += 1; print(f'  FAIL  {name}  {detail}')


def seg(net, a, b, layer='F.Cu', w=0.25):
    return (net, layer, a, b, w)


def run(victims, aggressors, threshold=1.0):
    r = X.coupled(victims, aggressors, threshold)
    return sum(v[0] for v in r.values())


def main():
    pcb, pro = sys.argv[1], sys.argv[2]

    # ---- the core discrimination
    parallel = run([seg('/CV_0', (10, 10), (30, 10))],
                   [seg('/CLK',  (10, 10.5), (30, 10.5))])
    crossing = run([seg('/CV_0', (10, 10), (30, 10))],
                   [seg('/CLK',  (20, 0), (20, 20))])
    far      = run([seg('/CV_0', (10, 10), (30, 10))],
                   [seg('/CLK',  (10, 25), (30, 25))])
    print(f'    parallel 20mm at 0.25mm gap : {parallel:.1f} mm coupled')
    print(f'    90 degree crossing          : {crossing:.1f} mm coupled')
    print(f'    20mm apart                  : {far:.1f} mm coupled')
    check('a long parallel run scores high', parallel > 15, f'{parallel:.1f}')
    # A crossing does register a little: within a 1mm threshold the traces are
    # close for roughly +/-1mm of the victim either side of the intersection.
    # That is real, and small. What matters is that it stays a rounding error
    # next to a parallel run, which the ratio check below pins down.
    check('a 90 degree crossing scores only a couple of mm', crossing < 3.0, f'{crossing:.1f}')
    check('a crossing scores far below a parallel run', crossing * 5 < parallel)
    check('well separated traces score zero', far == 0, f'{far:.1f}')

    # ---- threshold and geometry behave
    near = run([seg('/CV_0', (10, 10), (30, 10))], [seg('/CLK', (10, 10.6), (30, 10.6))], 1.0)
    tight = run([seg('/CV_0', (10, 10), (30, 10))], [seg('/CLK', (10, 10.6), (30, 10.6))], 0.2)
    check('a tighter threshold reports less', tight < near, f'{tight:.1f} vs {near:.1f}')
    check('edge to edge, not centre to centre',
          run([seg('/CV_0', (0, 0), (10, 0), 'F.Cu', 2.0)],
              [seg('/CLK', (0, 1.6), (10, 1.6), 'F.Cu', 2.0)], 0.5) > 5,
          '(two 2mm traces 1.6mm apart on centres overlap at the edges)')

    # ---- layers are respected
    other = run([seg('/CV_0', (10, 10), (30, 10), 'F.Cu')],
                [seg('/CLK', (10, 10.5), (30, 10.5), 'B.Cu')])
    check('the opposite layer is not counted as same-layer coupling', other == 0, f'{other:.1f}')

    # ---- netclass resolution comes from the project, not a guess
    pats, names = X.netclasses(pro)
    check('netclass patterns load from the project', len(pats) > 0, str(names))
    check('a CV net resolves to ANALOG', X.class_of('/CV_0', pats) == 'ANALOG',
          X.class_of('/CV_0', pats))
    check('a clock net resolves to DIGITAL', X.class_of('/CLK', pats) == 'DIGITAL',
          X.class_of('/CLK', pats))
    check('GND resolves to GND', X.class_of('GND', pats) == 'GND', X.class_of('GND', pats))

    # ---- end to end on a copy of the real board, with traces added
    tmp = tempfile.mkdtemp()
    try:
        base = os.path.splitext(pcb)[0]
        for ext in ('.kicad_pcb', '.kicad_pro', '.kicad_dru'):
            if os.path.exists(base + ext): shutil.copy(base + ext, tmp)
        p2 = os.path.join(tmp, os.path.basename(pcb))
        text = open(p2).read()
        add = ''
        for net, y in (('/CV_0', 60.0), ('/CLK', 60.55)):
            add += (f'\t(segment\n\t\t(start 25 {y})\n\t\t(end 45 {y})\n'
                    f'\t\t(width 0.25)\n\t\t(layer "F.Cu")\n\t\t(net "{net}")\n'
                    f'\t\t(uuid "{uuid.uuid4()}")\n\t)\n')
        cut = text.rstrip().rfind(')')
        open(p2, 'w').write(text[:cut] + add + ')\n')
        segs, vic, agg, runs = X.analyse(p2, os.path.join(tmp, os.path.basename(pro)),
                                         1.0, 'ANALOG', 'DIGITAL')
        total = sum(v[0] for v in runs.values())
        check('reads real tracks out of a .kicad_pcb', len(segs) >= 2, str(len(segs)))
        check('classifies them via the real project netclasses',
              len(vic) >= 1 and len(agg) >= 1, f'{len(vic)} victims, {len(agg)} aggressors')
        check('finds the planted 20mm coupled run', total > 15, f'{total:.1f} mm')
        loc = [v[1] for v in runs.values() if v[1]]
        check('reports where to look', bool(loc), str(loc[:1]))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print(f'\n  {PASS} passed, {FAIL} failed')
    return 1 if FAIL else 0


if __name__ == '__main__':
    sys.exit(main())
