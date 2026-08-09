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

All new work uses `eurorack-common-library/design-rules/house-mill.kicad_dru`.

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

1. Use a part you have in stock. See `eurorack-common-library/docs/preferred-values.md`.
2. If the value is not in stock, choose SMD.

Through-hole resistors and capacitors are well stocked, so they stay in use.
SMD is also easier on a milled board: an SMD pad solders from one face, and an
unplated through-hole pad does not.

Boards are double sided. Route on both layers.

Nothing is plated at home, so each via is a rivet you set or a wire you solder
on both faces. Count vias, not layers.

Leave the board corners clear. Double-sided milling needs four 2mm dowel holes,
3mm in from the edges, to align the two sides.

## After Konnect creates a file

Konnect writes new files in an older format. It stamps `version 20250610` and
`generator "konnect"`, while KiCad 10 writes `20260306` for schematics and
`20260206` for boards.

Upgrade any new file once, before you commit it:

```bash
kicad-cli sch upgrade <name>.kicad_sch
kicad-cli pcb upgrade <name>.kicad_pcb
```

Konnect keeps the version it finds in an existing file, so one upgrade holds for
every later edit.

Editing an existing file is safe. A round trip over a migrated board kept the
version, the generator, and every symbol, wire, label, junction and no-connect.
The output reformats, so expect a large diff with no change in content.

## Conventions

- One function per block. Two words must name it.
- No connectors. Connectors belong to the breakout.
- Name in `kebab-case` by function: `vca-linear`, not `lm13700-vca`.
- Version every circuit. See [docs/versioning.md](docs/versioning.md).
- Write a `README.md` next to every block. See below.

## Block documentation

Each block holds its own `README.md`. Write it in ASD-STE100 Simplified
Technical English: short sentences, active voice, present tense, one instruction
per sentence.

Use these headings:

| Heading | Content |
|---|---|
| What it does | One paragraph. State what the block does not do. |
| Interface | Every net that crosses the boundary, and its direction. |
| Bill of materials | Reference, value, part. Say if a part is not in stock. |
| Limits | What the block does not handle, and what it costs you. |
| Changelog | One entry per version. |

Add other headings when the circuit needs them. The power input block adds
Connector and Protection.

**The Limits section matters most.** A reader can see the circuit from the
schematic. They cannot see the trade you made, or the failure you did not guard
against. Record facts that ERC cannot check, such as diode direction.

[sheets/power-input/README.md](sheets/power-input/README.md) is the reference
example.
