# Eurorack Blocks

Reusable circuit blocks — schematic *and* layout — shared across Eurorack module
projects, plus the house design rules every project inherits.

This repo holds **circuits**. Parts (symbols, footprints, 3D models, SPICE) live
in [eurorack-common-library](https://github.com/carr-james/eurorack-common-library),
and physical breadboard-friendly versions of these circuits live in
[eurorack-breakouts](https://github.com/carr-james/eurorack-breakouts).

## Requires KiCad 10

PCB design blocks were added in KiCad 10 — v9 had schematic blocks only. This
library is not usable on KiCad 9.

## Layout

```
blocks/eurorack.kicad_blocks/   the design block library (the folder IS the library)
  <block-name>/                 one folder per block
    <block-name>.kicad_sch      schematic fragment
    <block-name>.kicad_pcb      layout fragment
    <block-name>.json           KiCad's block description — carries the version
    CHANGELOG.md                what changed, per version
design-rules/house-mill.kicad_dru   the rules every board here is designed to
templates/                      starting points for new blocks
docs/                           conventions, in detail
```

## Registering the library

Preferences → Manage Design Block Libraries → add:

| field | value |
|---|---|
| Nickname | `Eurorack Blocks` |
| Library Path | `<this repo>/blocks/eurorack.kicad_blocks` |
| Library Format | `KiCad` |

Prefer a project-relative path (`${KIPRJMOD}/...`) when consuming this repo as a
submodule, so projects stay portable — the same approach the parts library uses.

## Design rules: mill-safe by default

Everything here is designed to `design-rules/house-mill.kicad_dru`, which
targets in-house milling on the Makera Carvera Air:

| | mill (house rules) | JLCPCB |
|---|---|---|
| track / clearance | 0.2mm | ~0.127mm |
| via diameter | 0.9mm (0.6mm drill) | 0.3mm |
| plated through-holes | **no** | yes |

Mill rules are stricter, so a block that passes them is also fabbable at JLCPCB.
The reverse is not true — a JLC-dense block cannot be milled.

Two consequences worth internalising:

**Vias are labour.** Nothing is plated in-house; every via is a rivet you set by
hand or a wire you solder both sides of. Minimise them. Prefer single-layer
routing with a back-side pour and a few deliberate stitches over a via-happy
two-layer layout.

**SMD is easier than through-hole here.** With no plated barrels a through-hole
pad is only reliably solderable from one face, and you cannot reach the top pad
under a DIP body. Surface-mount parts solder from one side and need no plating.
New blocks should be SMD-first; the existing through-hole parts in
eurorack-common-library remain correct for externally-fabbed Eurorack modules.

## Conventions

- **One function per block.** If you cannot name it in two words, it is probably two blocks.
- **No connectors.** A block is absorbed into a host board. Connectors belong to the breakout.
- **Name in `kebab-case`**, describing function not implementation: `vca-linear`, not `lm13700-vca`.
- **Version every block.** See [docs/versioning.md](docs/versioning.md).

## Versioning in one line

Blocks are versioned individually with semver, the version is stamped both in
the block's JSON and as visible text in the schematic fragment, and each block
keeps its own `CHANGELOG.md`. The stamp matters: a placed block may be a *copy*
rather than a live link, so the text in the schematic can be the only surviving
record of which version a board was built from.
