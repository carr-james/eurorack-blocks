# Learnings

Facts found while building, that cost time to find. Keep this current. If an
entry turns out to be wrong, correct it and say what replaced it. A wrong entry
here is worse than no entry.

## Verify against the datasheet before you commit a schematic

A block is copied into every module that uses it. A weak design does not stay in
one place, and the failure shows up as damaged hardware, not as a build error.
Recalled numbers are not analysis.

Check these before a block is committed, and put the source in the block README:

| Question | Source |
|---|---|
| What current can the driving pin supply? | datasheet, static characteristics |
| What is the absolute maximum current into any pin? | datasheet, maximum ratings |
| What happens when a patch cable applies a rail voltage? | trace the current path |
| Where does that fault current end up? | check the receiving rail can absorb it |
| Does the load pull the level below a threshold? | divider against the real load |

Name the document. `TI SCHS027C` is checkable. "About 1mA" is not.

This rule exists because it was broken. `gate-output` was committed with a 1k
series resistor sized from memory. The CD4017B datasheet gives `DC INPUT
CURRENT, ANY ONE INPUT` as ±10mA, and 12V through 1k is 12mA, over the limit.

## Pattern: jack interface

Every net that reaches a jack needs protection, whether it is an input or an
output. A patch cable can apply any voltage in the case to either.

The circuit is the same shape every time: a series resistor, and two clamp
diodes to the rails of the part being protected. An input adds a pull-down.

**The values are not the same every time.** Derive them per block:

1. **Series resistor.** Take the absolute maximum pin current from the
   datasheet. Divide the worst injected voltage by it. Assume the clamps do
   nothing. For an input you can go much higher, because an input draws no
   current, which also lowers the fault current.
2. **Clamps.** To the rails of the part you are protecting, not to whichever
   rail is nearby.
3. **Pull-down.** Inputs only, so an unpatched jack reads as a defined state.
   Keep it much larger than the series resistor, or the divider will drop a
   valid signal below the threshold.
4. **Cite the datasheet** in the block README, by document number.

Worked examples:

| Block | Series R | Clamps | Why |
|---|---|---|---|
| `gate-output` | 2k2 | +5V, GND | CD4017B pin limit is 10mA, so 12V needs 1k2 or more |
| `cv-output` | 1k | +12VA, -12VA | TL071 output is short-circuit protected, so R is only isolation |
| `clock-input` | 10k | +5V, GND | an input draws nothing, so a high value costs nothing |

### Do not factor this into a shared block

It looks repeated, and the instinct to remove the repetition is wrong here.

The values differ per part, and a KiCad hierarchical sheet cannot be
parameterised. There is no way to pass a resistor value or a rail into a sheet
instance, so a configurable protection block is not possible. Separate variants
per rail and per value would give the same number of artifacts with none of the
benefit.

A separate protection block would also make the library unsafe by default,
because it can be left out. A block that carries its own protection cannot be
assembled wrongly.

The reusable thing is this pattern, not the components. Do not copy values
between blocks. Copying the 2k2 from `gate-output` into `cv-output` would have
doubled the output impedance of a CV output for no reason.

## Protection diodes do not divert what you assume

An external 1N4148 across a CMOS pin sits in parallel with the on-chip
protection diode. Both have a similar forward voltage, so they share fault
current unpredictably. The chip can still take several mA.

Size the series resistor so the pin is safe **with the external clamps doing
nothing**. Treat the clamps as the second line.

A Schottky clamp such as a BAT54 has a lower forward voltage and does divert
predictably. Use one where the injected voltage is higher.

## Clamping to a rail pushes current into that rail

Fault current does not vanish. A clamp to +5V, or the on-chip diode to VDD,
drives current into the +5V rail.

A linear regulator cannot sink. A lightly loaded rail rises, and every logic
chip on it sees over-voltage.

Any rail that feeds a clamped output needs a minimum load. `regulator-5v`
carries a bleeder resistor for this reason.

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
