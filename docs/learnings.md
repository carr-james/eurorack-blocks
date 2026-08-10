# Learnings

Facts found while building, that cost time to find. Keep this current. If an
entry turns out to be wrong, correct it and say what replaced it. A wrong entry
here is worse than no entry.

## Block harness ERC

A block harness reports errors that are not faults. The rails, the inputs and
the interface labels all come from the parent in real use.

Set these four rules to `warning` in a harness `.kicad_pro`:

| Rule | Why it fires |
|---|---|
| `pin_not_driven` | the parent drives the input |
| `isolated_pin_label` | an interface label touches one pin, which is correct |
| `missing_unit` | a spare op-amp unit belongs to the module, not the block |
| `missing_input_pin` | same reason |

Add a `PWR_FLAG` for each rail the block consumes. Do not downgrade
`power_pin_not_driven`. A flag is explicit and shows intent.

**Do not copy this profile into a module project.** In a module these four are
real faults. The harness is the only place the relaxation is correct.

## Konnect drops the footprint

`add_schematic_component` does not copy the `Footprint` property from the
library symbol. Every placed instance arrives with an empty footprint.

This defeats the pre-linked footprints the shared library is built on, and with
them the 3D models.

Set the footprint after every placement:

```
edit_schematic_component(reference=..., footprint="Eurorack Common:...")
```

## Konnect writes an old file format

Files it creates carry `version 20250610` and `generator "konnect"`. KiCad 10
writes `20260306` for schematics and `20260206` for boards.

Run `kicad-cli sch upgrade` and `pcb upgrade` on every new file before you
commit it. Konnect keeps the version it finds when editing, so one upgrade holds.

## Never write a KiCad file that KiCad has open

A `git checkout` of a schematic that Eeschema held in memory was undone the next
time the editor saved. The restore looked fine on disk and then vanished.

Check for a lock first:

```
find <project> -name '*.lck'
```

A lock on `.kicad_pro` alone means the project manager is open and the editors
are closed. That is safe. A lock on the document is not.

## Konnect over-inserts junctions

`batch_add_wire` inserted 185 junctions into a seven component sheet. Opening
and saving in Eeschema normalised them to 11.

Open and save in Eeschema after a Konnect wiring session.

## Layout belongs in Eeschema

Konnect places and moves symbols but cannot move a symbol's Reference or Value
text. Field text is what collides, so label overlap cannot be fixed through the
API. Dragging in Eeschema takes seconds and several API passes did not.

## Multi-unit parts and block size

A block that uses half a dual op-amp wastes the other half. Packing the spare
from another block does not work: two sheets each declare unit A, annotation
gives `U1A` and `U2A`, and pairing them by hand makes the sheets share a
reference. They stop being independently reusable, and every consuming module
has to redo the pairing.

Rules that avoid the problem:

1. Match the block to the package. A dual op-amp wants a two channel block. A
   quad wants four.
2. If one function needs its own block, use a single channel part. Block equals
   package equals function.
3. Never leave an unused op-amp input floating. It oscillates and puts noise on
   the rails.

A block built only from discrete parts has no package to share, so this does not
apply. Place it as many times as you like. Prefer discrete or single channel
parts in small blocks.

Surface mount helps. A single op-amp in SOT-23-5 takes less area than half a
SOIC-8, so a single channel part costs less board space than a packed dual.

## Ask what the circuit needs before reaching for an op-amp

The first gate output used a TL072 to reach +10V. It did not need one. A CMOS
output drives a Eurorack gate input directly, because the input is near 100k and
the standard level is +5V.

Removing the op-amp removed the spare half problem with it, and the block became
three discrete parts that can be placed eight times for per-step triggers.

Series resistance alone is not protection. A patch cable can inject a rail
voltage. Clamp diodes to the rail and to ground carry that current instead of the
chip pin.

## Update the submodule after you change the library

Adding a symbol to `eurorack-common-library` does not reach a project. Projects
resolve the library through `sheets/shared`, which is pinned to a commit.

ERC reports `Symbol not found in symbol library`. This has happened three times.

Commit and push the library, then pull in the submodule, then re-run ERC.

## Corrections

Entries that were wrong, kept so the same mistake is not repeated.

**`add_hierarchical_sheet` corrupts a shared sheet.** Wrong. One run left the
child with two ERC errors, and that was reported as tool damage. A later run on
the same file left ERC at zero. The first failure was probably the editor
overwrite described above. The tool links the existing file correctly and
reports `reused_existing_file`.

**19 junctions were destroyed.** Wrong. Junction counts move with the writer:
Konnect over-inserts and Eeschema normalises. Counting junctions does not
measure damage. Use ERC.

**KiCad 10 is blocked by pcb2blender.** Wrong. That claim came from grepping the
`main` branches, where Blender is unused. The `dev` branches do use it, and
pcb2blender constrains the architecture, not the KiCad version.

**Blender is needed to make WRL models.** Wrong for anything KiCad ships. The
upstream `kicad-packages3D` repository still publishes the WRL files that the
installer drops. Download them. FreeCAD is only needed for parts KiCad does not
ship, and for custom variants.
