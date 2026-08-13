#!/usr/bin/env python3
"""Tests for blockvendor.

The point of this tool is that a permutation cannot silently change a circuit.
That guarantee is only worth what these tests are worth, so they cover the two
ways it can fail: accepting a permutation it should reject, and emitting a sheet
that does not match the permutation it accepted.

    python3 test_blockvendor.py <blocks-repo-root> <symbol-library>
"""
import sys, os, re, json, tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import blockvendor as BV

PASS = FAIL = 0


def check(name, cond, detail=''):
    global PASS, FAIL
    if cond: PASS += 1; print(f'  ok    {name}')
    else:    FAIL += 1; print(f'  FAIL  {name}  {detail}')


def main():
    root, symlib_path = sys.argv[1], sys.argv[2]
    symlib = open(symlib_path).read()
    sheet_rel = 'sheets/cv-mux-8/cv-mux-8.kicad_sch'
    sheet = open(os.path.join(root, sheet_rel)).read()

    # ---- interchangeability is derived, not declared
    check('CD4066 switches are interchangeable, supply unit is not',
          BV.interchangeable_units(symlib, '4066') == [1, 2, 3, 4])
    check('CD4011 gates are interchangeable',
          BV.interchangeable_units(symlib, '4011') == [1, 2, 3, 4])
    check('CD40106 inverters are interchangeable',
          BV.interchangeable_units(symlib, '40106') == [1, 2, 3, 4, 5, 6])
    check('TL072 op-amps are interchangeable',
          BV.interchangeable_units(symlib, 'TL072IP') == [1, 2])
    check('CD4017 has NO interchangeable units (its outputs are a sequence)',
          BV.interchangeable_units(symlib, '4017') == [])

    # ---- the checker must fail closed
    def lock_with(units):
        return {'blocks': {'b': {
            'source': {'sheet': sheet_rel}, 'symlib': os.path.relpath(symlib_path, root),
            'vendored': 'out.kicad_sch', 'transform': {'units': units}}}}

    def errs(units):
        e, _ = BV.check_lock(lock_with(units), root, verbose=False)
        return e

    check('rejects moving the supply unit', errs({'U1.1': 'U1.5', 'U1.5': 'U1.1'}))
    check('rejects a non-bijection',        errs({'U1.1': 'U1.2'}))
    check('rejects a unit that does not exist', errs({'U1.1': 'U1.9', 'U1.9': 'U1.1'}))
    check('rejects mixing part types',      errs({'U1.1': 'C1.1', 'C1.1': 'U1.1'}))
    check('rejects an unknown reference',   errs({'U1.1': 'U9.1', 'U9.1': 'U1.1'}))
    check('accepts a legal swap',           not errs({'U1.1': 'U1.2', 'U1.2': 'U1.1'}))
    check('accepts the identity',           not errs({}))

    # ---- the transform must match the permutation it was given, exactly
    perm = {'U1.1': 'U1.1', 'U1.2': 'U1.4', 'U1.3': 'U1.2', 'U1.4': 'U2.3',
            'U2.1': 'U2.1', 'U2.2': 'U1.3', 'U2.3': 'U2.4', 'U2.4': 'U2.2'}
    out, _ = BV.transform(sheet, {'strip': ['PWR_FLAG'], 'units': perm})
    pkg = BV.package_map(sheet)['main']

    def slots(t):
        top = BV.balanced(t, t.index('(lib_symbols')); d = {}
        for st, en in BV.blocks_of(t, r'symbol\s*\n', top):
            blk = t[st:en]
            uid = re.search(r'\n\s*\(uuid "([0-9a-f-]+)"\)', blk)
            r = re.search(r'\(property "Reference" "([^"]+)"', blk)
            u = re.search(r'\(unit (\d+)\)', blk)
            inst = dict((p, f'{rr}.{uu}') for p, rr, uu in re.findall(
                r'\(project "([^"]+)"\s*\n\s*\(path "[^"]*"\s*\n\s*'
                r'\(reference "([^"]+)"\)\s*\n\s*\(unit (\d+)\)', blk))
            if uid and r and u and r.group(1).startswith('U'):
                d[uid.group(1)] = (f'{r.group(1)}.{u.group(1)}', inst.get('main'))
        return d

    a, b = slots(sheet), slots(out)
    moved_ok = mod_ok = True
    for uid, (sa, ma) in a.items():
        sb, mb = b[uid]
        want = perm.get(sa, sa)
        moved_ok &= (sb == want)
        wr, wu = want.split('.')
        mod_ok &= (mb == f'{pkg[wr]}.{wu}')
    check('every symbol lands on the slot the lock names', moved_ok)
    check('module-side references follow a package change', mod_ok,
          '(a gate that changes package must take its module reference with it)')

    # ---- everything the permutation must NOT touch
    def geom(t):
        return (sorted(re.findall(r'\((?:label|hierarchical_label|global_label) "([^"]+)"', t)),
                len(re.findall(r'\(junction\b', t)))
    ga, gb = geom(sheet), geom(out)
    check('labels are untouched', ga[0] == gb[0])
    check('junctions are untouched', ga[1] == gb[1])
    def flag_instances(t):
        top = BV.balanced(t, t.index('(lib_symbols'))
        return sum(1 for st, en in BV.blocks_of(t, r'symbol\s*\n', top)
                   if 'PWR_FLAG' in t[st:en])
    check('PWR_FLAG instances are stripped',
          flag_instances(out) == 0 and flag_instances(sheet) > 0,
          '(the unused lib_symbols definition may remain; KiCad prunes it)')
    nflag = len(re.findall(r'PWR_FLAG', sheet))
    check('stripping removed the stub wires too',
          len(re.findall(r'\(wire\b', out)) < len(re.findall(r'\(wire\b', sheet)),
          f'({nflag} flag references in the source)')

    # ---- vendoring is a pure function: same inputs, same bytes
    again, _ = BV.transform(sheet, {'strip': ['PWR_FLAG'], 'units': perm})
    check('transform is deterministic', again == out)

    print(f'\n  {PASS} passed, {FAIL} failed')
    return 1 if FAIL else 0


if __name__ == '__main__':
    sys.exit(main())
