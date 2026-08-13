#!/usr/bin/env python3
"""Vendor a block sheet into a module, with a permutation, and prove it is still
the same circuit.

A block is a reusable circuit. A module wants to permute the things that are
free to permute — which gate of a package does which job, which connector pin
carries which signal — because that is worth about a third of the ratsnest
crossings. Editing the shared block to suit one board is not acceptable, and
neither is giving up the freedom.

So the module keeps a generated copy and a record of exactly how it differs:

    blocks.lock  ->  block sheet + declared permutation  ->  vendored sheet

`vendor` generates the copy. `verify` regenerates it and fails on any
difference, so the two can never drift apart unnoticed. `check` validates the
permutation itself before either runs.

The permutation is RECORDED, not discovered, so verification is a diff and not
a graph isomorphism search. What has to be checked is that the permutation is
legal: that it only ever swaps units that are genuinely interchangeable.

Commands:
    blockvendor.py check  <lock>     validate the lock and every permutation
    blockvendor.py vendor <lock>     generate the vendored sheets
    blockvendor.py verify <lock>     regenerate and diff; non-zero on drift
    blockvendor.py units  <symlib> <part>   show a part's interchangeable units
"""
import sys, os, re, json, argparse, subprocess, tempfile, difflib


# ----------------------------------------------------------------- s-expr bits
def balanced(t, i):
    """Index just past the s-expression starting at t[i] == '('."""
    d = 0
    for k in range(i, len(t)):
        if t[k] == '(': d += 1
        elif t[k] == ')':
            d -= 1
            if d == 0: return k + 1
    raise ValueError('unbalanced expression')


def blocks_of(text, head, start=0):
    """Yield (start, end) for every s-expression opening with `head`.

    `head` is a regex fragment. Schematic symbol *instances* open with
    `(symbol` then a newline; library *definitions* open with `(symbol "name"`.
    Callers have to say which they mean, and a pattern that only matches one of
    them silently finds nothing rather than failing.
    """
    for m in re.finditer(r'\(' + head, text[start:]):
        st = start + m.start()
        yield st, balanced(text, st)


# ------------------------------------------------------------- symbol library
def symbol_units(symlib_text, part):
    """-> {unit: [(pin number, electrical type), ...]} for one library symbol.

    Derived from the library rather than a hardcoded table, so a symbol that
    gains a unit does not silently invalidate everything downstream.
    """
    i = symlib_text.index(f'(symbol "{part}"')
    blk = symlib_text[i:balanced(symlib_text, i)]
    units = {}
    for st, en in blocks_of(blk, r'symbol "'):
        sub = blk[st:en]
        m = re.match(r'\(symbol "([^"]+)"', sub)
        if not m: continue
        um = re.match(rf'{re.escape(part)}_(\d+)_(\d+)$', m.group(1))
        if not um: continue
        u = int(um.group(1))
        if u == 0: continue                     # unit 0 is common graphics
        pins = []
        for ps, pe in blocks_of(sub, r'pin \w+ \w+\s*\n'):
            p = sub[ps:pe]
            num = re.search(r'\(number "([^"]+)"', p)
            et = re.match(r'\(pin (\w+)', p)
            if num: pins.append((num.group(1), et.group(1) if et else '?'))
        units.setdefault(u, []).extend(pins)
    return {u: sorted(p) for u, p in units.items()}


def interchangeable_units(symlib_text, part):
    """Units that may trade places: same pin count and same multiset of pin
    electrical types, and carrying no power pin.

    A CD4066's four switches qualify. Its supply unit does not, and neither does
    a CD4017, whose outputs are a counting sequence rather than equivalent
    copies.
    """
    units = symbol_units(symlib_text, part)
    shape = {}
    for u, pins in units.items():
        if any(et.startswith('power') for _, et in pins): continue
        shape.setdefault(tuple(sorted(et for _, et in pins)), []).append(u)
    groups = [sorted(v) for v in shape.values() if len(v) > 1]
    return sorted(groups[0]) if len(groups) == 1 else sorted(
        max(groups, key=len)) if groups else []


# ------------------------------------------------------------------ transform
def package_map(text):
    """block reference -> module reference, read from the sheet's own instance
    data. A gate that moves to another package has to take its module-side
    reference with it."""
    top = balanced(text, text.index('(lib_symbols'))
    out = {}
    for st, en in blocks_of(text, r'symbol\s*\n', top):
        blk = text[st:en]
        r = re.search(r'\(property "Reference" "([^"]+)"', blk)
        if not r: continue
        for pm in re.finditer(
                r'\(project "([^"]+)"\s*\n\s*\(path "[^"]*"\s*\n\s*\(reference "([^"]+)"', blk):
            out.setdefault(pm.group(1), {}).setdefault(r.group(1), pm.group(2))
    return out


def apply_units(text, slotmap):
    """Move gates between units AND between packages.

    A slot is "REF.UNIT". The map sends each slot to the slot that should do its
    job, which may sit in a different package: two CD4066s on one sheet give
    eight interchangeable switches, not two groups of four, and restricting to
    within-package permutations throws away most of that.

    Moving a gate to another package changes its reference, so the symbol's own
    reference and unit both move, and so does every per-project instance
    reference. Rewriting the unit but not the reference produces a sheet that
    looks right and nets up wrong.
    """
    pkgmap = package_map(text)
    top = balanced(text, text.index('(lib_symbols'))
    edits, moved = [], 0
    for st, en in blocks_of(text, r'symbol\s*\n', top):
        blk = text[st:en]
        rm = re.search(r'\(property "Reference" "([^"]+)"', blk)
        um = re.search(r'\(unit (\d+)\)', blk)
        if not rm or not um: continue
        src = f'{rm.group(1)}.{um.group(1)}'
        dst = slotmap.get(src)
        if not dst or dst == src: continue
        dref, dunit = dst.split('.')
        nb = blk
        # the symbol's own reference and unit
        nb = re.sub(r'(\(property "Reference" ")[^"]*(")',
                    lambda m: m.group(1) + dref + m.group(2), nb, count=1)
        nb = re.sub(r'\(unit \d+\)', f'(unit {dunit})', nb)
        # every per-project instance: reference follows the package
        # The match must include the closing paren of (reference "..."), or the
        # replacement target is not inside the matched text and the substitution
        # silently does nothing: the gate moves package while its module-side
        # reference stays behind, which nets up as a different board than the one
        # that was optimised.
        def fix_inst(m):
            proj, ref = m.group(1), m.group(2)
            newref = pkgmap.get(proj, {}).get(dref, ref)
            return m.group(0).replace(f'(reference "{ref}")', f'(reference "{newref}")')
        nb, nsub = re.subn(
            r'\(project "([^"]+)"\s*\n\s*\(path "[^"]*"\s*\n\s*\(reference "([^"]+)"\)',
            fix_inst, nb)
        if nsub == 0:
            raise ValueError(f'no project instance found for {src}; refusing to emit a '
                             f'sheet whose module references did not follow the move')
        edits.append((st, en, nb)); moved += 1
    out = text
    for a, b, nb in sorted(edits, reverse=True): out = out[:a] + nb + out[b:]
    return out, moved


def strip_symbols(text, lib_match):
    """Remove matching symbol instances and the single stub wire each one hangs
    on. A PWR_FLAG left in a vendored sheet collides with the module's own power
    source; removing the symbol but leaving its wire trades one ERC error for
    another."""
    out, removed = text, 0
    top = balanced(text, text.index('(lib_symbols'))
    kill_pts, edits = [], []
    for st, en in blocks_of(text, r'symbol\s*\n', top):
        blk = text[st:en]
        lib = re.search(r'\(lib_id "([^"]+)"', blk)
        if not lib or lib_match not in lib.group(1): continue
        at = re.search(r'\n\s*\(at ([-\d.]+) ([-\d.]+)', blk)
        if at: kill_pts.append((round(float(at.group(1)), 3), round(float(at.group(2)), 3)))
        edits.append((st, en, '')); removed += 1
    for ws, we in blocks_of(text, r'wire\s*\n'):
        seg = text[ws:we]
        xy = [(round(float(a), 3), round(float(b), 3))
              for a, b in re.findall(r'\(xy ([-\d.]+) ([-\d.]+)\)', seg)][:2]
        if len(xy) == 2 and (xy[0] in kill_pts or xy[1] in kill_pts):
            edits.append((ws, we, ''))
    for a, b, nb in sorted(set(edits), reverse=True): out = out[:a] + nb + out[b:]
    return out, removed


def transform(sheet_text, spec, symlib_text=None):
    """block sheet + spec -> vendored sheet. Pure function of its inputs, which
    is what makes verify a byte comparison."""
    text = sheet_text
    notes = []
    for lib in spec.get('strip', []):
        text, n = strip_symbols(text, lib)
        notes.append(f'stripped {n} {lib}')
    units = spec.get('units', {})
    if units:
        text, n = apply_units(text, units)
        notes.append(f'reassigned {n} units')
    return text, notes


# ------------------------------------------------------------------ semantics
def circuit(text):
    """A formatting-independent fingerprint of what the sheet actually is.

    Everything electrical, nothing cosmetic. KiCad rewrites child sheets on
    every save — reindenting, pruning unused lib_symbols, reordering — and a
    byte comparison calls all of that drift. Connectivity in a schematic is
    positional, so comparing symbol placement, wire endpoints, junctions and
    labels compares the circuit itself.

    Symbol identity is the uuid, which survives a resave; reference and unit are
    values to compare, not identity, because moving a gate is exactly what we
    are checking for.
    """
    top = balanced(text, text.index('(lib_symbols'))
    body = text[top:]
    syms = {}
    for st, en in blocks_of(body, r'symbol\s*\n'):
        blk = body[st:en]
        uid = re.search(r'\n\s*\(uuid "([0-9a-f-]+)"\)', blk)
        lib = re.search(r'\(lib_id "([^"]+)"', blk)
        ref = re.search(r'\(property "Reference" "([^"]+)"', blk)
        unit = re.search(r'\(unit (\d+)\)', blk)
        at = re.search(r'\n\s*\(at ([-\d.]+) ([-\d.]+)(?: ([-\d.]+))?\)', blk)
        if not (uid and lib): continue
        inst = tuple(sorted((pr, rr, uu) for pr, rr, uu in re.findall(
            r'\(project "([^"]+)"\s*\n\s*\(path "[^"]*"\s*\n\s*'
            r'\(reference "([^"]+)"\)\s*\n\s*\(unit (\d+)\)', blk)))
        syms[uid.group(1)] = (lib.group(1),
                              ref.group(1) if ref else None,
                              unit.group(1) if unit else None,
                              (round(float(at.group(1)), 3), round(float(at.group(2)), 3),
                               float(at.group(3) or 0)) if at else None,
                              dict(((pr, (rr, uu)) for pr, rr, uu in inst)))
    def pts(head):
        out = []
        for st, en in blocks_of(body, head):
            seg = body[st:en]
            xy = [(round(float(a), 3), round(float(b), 3))
                  for a, b in re.findall(r'\(xy ([-\d.]+) ([-\d.]+)\)', seg)]
            if xy: out.append(tuple(sorted(xy)))
        return sorted(out)
    def ats(head):
        out = []
        for st, en in blocks_of(body, head):
            seg = body[st:en]
            nm = re.match(r'\([a-z_]+ "([^"]*)"', seg)
            at = re.search(r'\(at ([-\d.]+) ([-\d.]+)', seg)
            if at: out.append(((nm.group(1) if nm else None),
                               round(float(at.group(1)), 3), round(float(at.group(2)), 3)))
        return sorted(out)
    return {
        'symbols':   syms,
        'wires':     pts(r'wire\s*\n'),
        'junctions': ats(r'junction\s*\n'),
        'noconnect': ats(r'no_connect\s*\n'),
        'labels':    ats(r'label "') + ats(r'hierarchical_label "') + ats(r'global_label "'),
    }


def circuit_diff(a, b):
    """-> [human-readable difference] between two circuit fingerprints."""
    out = []
    ka, kb = set(a['symbols']), set(b['symbols'])
    if ka - kb: out.append(f'{len(ka-kb)} symbol(s) missing from the vendored sheet')
    if kb - ka: out.append(f'{len(kb-ka)} extra symbol(s) in the vendored sheet')
    for uid in sorted(ka & kb):
        x, y = a['symbols'][uid], b['symbols'][uid]
        for i, field in enumerate(['lib_id', 'reference', 'unit', 'position']):
            if x[i] != y[i]: out.append(f'symbol {uid[:8]}: {field} {x[i]!r} != {y[i]!r}')
        # Compare only projects present in BOTH. KiCad drops instance data for
        # projects it is not currently opening, so demanding the same set of
        # projects reports every resave as drift and trains you to ignore it.
        shared = set(x[4]) & set(y[4])
        for proj in sorted(shared):
            if x[4][proj] != y[4][proj]:
                out.append(f'symbol {uid[:8]}: instance[{proj}] '
                           f'{x[4][proj]!r} != {y[4][proj]!r}')
        if not shared and (x[4] or y[4]):
            out.append(f'symbol {uid[:8]}: no project in common '
                       f'({sorted(x[4])} vs {sorted(y[4])})')
    for k in ('wires', 'junctions', 'noconnect', 'labels'):
        if a[k] != b[k]:
            sa, sb = set(a[k]), set(b[k])
            out.append(f'{k}: {len(sa-sb)} only in expected, {len(sb-sa)} only in vendored')
    return out


# ---------------------------------------------------------------- lock + checks
def load_lock(path):
    with open(path) as f: return json.load(f)


def check_lock(lock, root, verbose=True):
    """Validate before generating anything. Fails closed."""
    errors, warnings = [], []
    symlibs = {}
    for name, spec in lock.get('blocks', {}).items():
        src = spec.get('source', {})
        sheet = os.path.join(root, src.get('sheet', ''))
        if not os.path.exists(sheet):
            errors.append(f'{name}: source sheet not found: {sheet}'); continue
        text = open(sheet).read()
        symlib_path = os.path.join(root, spec.get('symlib', ''))
        if spec.get('symlib') and os.path.exists(symlib_path):
            symlibs[name] = open(symlib_path).read()
        # part type of each reference in the sheet
        parts = {}
        top = balanced(text, text.index('(lib_symbols'))
        for st, en in blocks_of(text, r'symbol\s*\n', top):
            blk = text[st:en]
            r = re.search(r'\(property "Reference" "([^"]+)"', blk)
            l = re.search(r'\(lib_id "([^"]+)"', blk)
            if r and l: parts.setdefault(r.group(1), l.group(1).split(':')[-1])
        slotmap = spec.get('transform', {}).get('units', {})
        if slotmap:
            srcs = sorted(slotmap); dsts = sorted(slotmap.values())
            if srcs != dsts:
                errors.append(f'{name}: unit map is not a bijection over its own slots; '
                              f'{len(set(srcs) ^ set(dsts))} slot(s) unmatched')
            refs = {sl.split('.')[0] for sl in set(srcs) | set(dsts)}
            missing = [r for r in refs if r not in parts]
            if missing:
                errors.append(f'{name}: reference(s) {sorted(missing)} not in the block')
            kinds = {parts[r] for r in refs if r in parts}
            if len(kinds) > 1:
                errors.append(f'{name}: unit map mixes part types {sorted(kinds)}; '
                              f'a gate can only move to an identical package')
            elif kinds and name in symlibs:
                part = kinds.pop()
                legal = interchangeable_units(symlibs[name], part)
                if not legal:
                    errors.append(f'{name}: {part} has no interchangeable units, '
                                  f'so no permutation of it is legal')
                bad = sorted({sl for sl in set(srcs) | set(dsts)
                              if int(sl.split('.')[1]) not in legal})
                if bad:
                    errors.append(f'{name}: slot(s) {bad} are not interchangeable for '
                                  f'{part}. Legal units: {legal}')
            elif kinds:
                warnings.append(f'{name}: no symbol library given, cannot prove the '
                                f'unit map legal')
    if verbose:
        for w in warnings: print(f'  WARN  {w}')
        for e in errors: print(f'  ERROR {e}')
    return errors, warnings


def do_vendor(lock, root, write=True):
    made = {}
    for name, spec in lock.get('blocks', {}).items():
        src = os.path.join(root, spec['source']['sheet'])
        text = open(src).read()
        out, notes = transform(text, spec.get('transform', {}))
        dest = os.path.join(root, spec['vendored'])
        made[name] = (dest, out, notes)
        if write:
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            with open(dest, 'w') as f: f.write(out)
    return made


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('cmd', choices=['check', 'vendor', 'verify', 'units'])
    ap.add_argument('lock')
    ap.add_argument('part', nargs='?')
    a = ap.parse_args()

    if a.cmd == 'units':
        text = open(a.lock).read()
        print(f'  {a.part}: units {sorted(symbol_units(text, a.part))}')
        print(f'  interchangeable: {interchangeable_units(text, a.part)}')
        return 0

    root = os.path.dirname(os.path.abspath(a.lock))
    lock = load_lock(a.lock)
    errors, warnings = check_lock(lock, root)
    if a.cmd == 'check':
        print(f'  {len(lock.get("blocks", {}))} block(s), '
              f'{len(errors)} error(s), {len(warnings)} warning(s)')
        return 1 if errors else 0
    if errors:
        print('  refusing to proceed with an invalid lock')
        return 1

    if a.cmd == 'vendor':
        for name, (dest, out, notes) in do_vendor(lock, root).items():
            print(f'  {name}: -> {os.path.relpath(dest, root)}  ({"; ".join(notes) or "verbatim"})')
        return 0

    drift = 0
    for name, (dest, out, notes) in do_vendor(lock, root, write=False).items():
        rel = os.path.relpath(dest, root)
        if not os.path.exists(dest):
            print(f'  DRIFT {name}: {rel} has not been generated'); drift += 1; continue
        have = open(dest).read()
        if have == out:
            print(f'  ok    {name}: {rel}  (byte identical)')
            continue
        d = circuit_diff(circuit(out), circuit(have))
        if not d:
            print(f'  ok    {name}: {rel}  (same circuit, reformatted)')
        else:
            drift += 1
            print(f'  DRIFT {name}: {rel} is not the block plus its permutation')
            for line in d[:10]: print(f'        {line}')
    print(f'  {drift} block(s) drifted')
    return 1 if drift else 0


if __name__ == '__main__':
    sys.exit(main())

# --------------------------------------------------------------------- caveat
# verify compares bytes. That fails closed, which is the right default, but it
# means opening the module in Eeschema and saving will report drift: KiCad
# rewrites child sheets (instance data, formatting, pruned lib_symbols) whether
# or not the circuit changed. A semantic comparison — same components, same slot
# assignment, same connectivity — is the next step, and until it exists a DRIFT
# report means "look at this", not necessarily "something broke".
