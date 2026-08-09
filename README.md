# Eurorack Blocks

Reusable circuits shared across Eurorack projects. Each circuit is defined once,
in this repo.

This repo holds circuits. Parts live in
[eurorack-common-library](https://github.com/carr-james/eurorack-common-library).
Physical test boards live in
[eurorack-breakouts](https://github.com/carr-james/eurorack-breakouts).

Requires KiCad 10.

## Two reuse mechanisms

Use the mechanism that fits the circuit.

| | hierarchical sheet | design block |
|---|---|---|
| Reuses | schematic | schematic and layout |
| Link to source | stays linked | may be a copy |
| Edit propagates | yes | possibly not |
| Use for | circuits you expect to revise | circuits whose layout you want back |

A hierarchical sheet keeps one definition. Projects reference the sheet file
through this repo as a submodule. An edit reaches every project that updates the
submodule pin.

A design block also returns the layout. It may paste a copy instead of a link,
so an edit may not reach existing boards. Prefer sheets for circuits you revise
often. Prefer blocks when the layout is the valuable part.

## Layout

```
sheets/                             hierarchical sheets, one per circuit
blocks/eurorack.kicad_blocks/       design block library
design-rules/house-mill.kicad_dru   default rules
docs/                               conventions
```

## Register the design block library

Open Preferences. Select Manage Design Block Libraries. Add a library.

| Field | Value |
|---|---|
| Nickname | `Eurorack Blocks` |
| Library Path | `<repo>/blocks/eurorack.kicad_blocks` |
| Library Format | `KiCad` |

Use `${KIPRJMOD}` relative paths when you consume this repo as a submodule.

## Design rules

All new work uses `design-rules/house-mill.kicad_dru`.

| | Mill (Carvera Air) | JLCPCB |
|---|---|---|
| Track and clearance | 0.2mm | 0.127mm |
| Via | 0.9mm, unplated | 0.3mm, plated |
| Layers | 2 | 4 or more |

Mill rules are stricter. A board that obeys them is also fabbable at JLCPCB. The
opposite is not true.

Two limits that DRC cannot check:

- Home fabrication gives 2 layers only.
- Home silkscreen is laser-cured. Small text prints badly. Do not depend on it.

## Part selection

1. Use a part you have in stock. Check PartsBox.
2. If the value is not in stock, choose SMD.

Through-hole resistors and capacitors are well stocked, so they stay in use.
SMD is also easier on a milled board: an SMD pad solders from one face, and an
unplated through-hole pad does not.

Boards are double sided. Route on both layers.

Nothing is plated at home, so each via is a rivet you set or a wire you solder
on both faces. Count vias, not layers.

Leave the board corners clear. Double-sided milling needs four 2mm dowel holes,
3mm in from the edges, to align the two sides.

## Conventions

- One function per block. Two words must name it.
- No connectors. Connectors belong to the breakout.
- Name in `kebab-case` by function: `vca-linear`, not `lm13700-vca`.
- Version every circuit. See [docs/versioning.md](docs/versioning.md).
