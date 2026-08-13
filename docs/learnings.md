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

Set these five rules to `warning` in a harness `.kicad_pro`:

| Rule | Why it fires |
|---|---|
| `pin_not_driven` | the parent drives the input |
| `isolated_pin_label` | an interface label touches one pin, which is correct |
| `missing_unit` | a spare op-amp unit belongs to the module, not the block |
| `missing_input_pin` | same reason |
| `pin_not_connected` | a hierarchical label has no parent sheet in a harness |

`pin_not_connected` is the widest of the five, because it also covers a pin that
is genuinely left dangling. Put a no-connect flag on every pin a block does not
use, so the relaxation hides nothing.

**Do not add a `PWR_FLAG` for a rail the block only consumes.** It satisfies the
harness and then collides with every other block in a module. Only the block
that sources a rail should flag it. See "PWR_FLAG belongs to the harness, not to
the block", and expect `power_pin_not_driven` in a consuming block's harness.

**Do not copy this profile into a module project.** In a module these four are
real faults. The harness is the only place the relaxation is correct.

## A block interface needs hierarchical labels

A plain net label is scoped to its sheet. It does not become a sheet pin, so a
parent cannot reach it. A block whose interface uses plain labels has no
interface at all once it is instantiated.

Use `hierarchical_label` for every net that crosses the block boundary, with a
shape of `input`, `output` or `bidirectional`. The parent then imports them as
sheet pins.

Two exceptions stay as they are:

- Global rails such as `+5V` and `GND`. A power symbol crosses the boundary on
  its own.
- Internal nets. A plain label is correct there, and scoping is what you want.

`gate-output`, `cv-output` and `clock-input` were built with plain labels and
have been converted. `power-input` needed no change, because its interface is
the header and the global rails, and its two labels sit between the header and
the diodes. `regulator-5v` has no labels at all.

This is proven, not assumed. A scratch parent linked `clock-input` as a
hierarchical sheet, `import_sheet_pins` produced `CLK_IN` and `CLK_OUT`, and the
parent netlist listed the child components with the two nets scoped as
`/Clock input/CLK_IN` and `/Clock input/CLK_OUT`. The same test on the plain
label version produced no sheet pins.

Annotate in the parent afterwards. Linking a sheet re-paths every symbol
instance, and a power flag comes through with a `?` reference until you do.

## A self-terminating pulse is not a pulse

The classic way to shorten a CD4017B is to wire a decoded output back to
`RESET`. The reset clears the output, and the output was the reset, so the pulse
ends itself.

The pulse width is then one propagation delay. TI SCHS027C gives that delay as
265ns typical and 530ns maximum, and gives **no minimum**. The part needs a
reset pulse of up to 260ns. Nothing in the datasheet guarantees the loop makes
one.

Inside one package it works, because the internal clear happens before the
output moves. Do not extend it across packages, and never across a chain, where
one device has to reset several others with a pulse it cuts short itself.

Generate a reset whose width you set. An RC into a Schmitt inverter gives
microseconds against a requirement of hundreds of nanoseconds.

**A datasheet minimum you cannot find is not zero.** If the timing you depend on
is a delay with no specified minimum, the design has no margin.

## Blocks collide on references when a module uses several

Every block numbers its own parts from `U1`, `R1`, `C1`. Instantiate nine of
them in one module and KiCad sees nine symbols claiming `U1` and treats them as
units of one component. The module ERC filled with `different_unit_net` and
`different_unit_footprint`, 47 errors that mean nothing about the circuit.

This is not a fault in the blocks. A child sheet's own reference is a default,
and KiCad stores the real one per parent project and sheet path:

```
(instances
  (project "main"
    (path "/<root-uuid>/<sheet-uuid>"
      (reference "U4")
      (unit 1))))
```

**Annotate the module across the whole hierarchy before its ERC means
anything.** Use Eeschema, Tools then Annotate, whole schematic, reset existing
annotation. `kicad-cli` has no annotate subcommand in KiCad 10, and Konnect's
`annotate_schematic` only fills references that are already `?`, so neither
fixes a collision.

The block keeps its own numbering for its own harness. Each parent gets its own,
so two modules using the same block do not fight.

## PWR_FLAG belongs to the harness, not to the block

Nine blocks that each flag `+5V` give nine `Power output` pins on one net, and
the module ERC reports `pin_to_pin` for every pair. 19 errors, again meaning
nothing about the circuit.

A `PWR_FLAG` asserts "this net is driven by something ERC cannot see". In a
module that is only true of the block that actually sources the rail:
`power-input` for `+12VA` and `-12VA`, `regulator-5v` for `+5V`. Everywhere else
the rail *is* driven and the flag is a lie ERC believes.

The earlier entry under "Block harness ERC" said to add a flag for each rail a
block consumes, and not to downgrade `power_pin_not_driven`. **That was wrong**,
and it was wrong because it was only ever tested against a harness. See
Corrections.

`add_schematic_component` does not copy the `Footprint` property from the
library symbol. Every placed instance arrives with an empty footprint.

This defeats the pre-linked footprints the shared library is built on, and with
them the 3D models.

Set the footprint after every placement:

```
edit_schematic_component(reference=..., footprint="Eurorack Common:...")
```

Two blocks were committed without it and nobody noticed, because ERC does not
check footprints. `power-input` had none on any part, and `clock-input` had none
on U1.

Check the exported netlist, not the schematic. A multi-unit part carries the
footprint on unit 1 only, so the schematic looks half empty while the netlist is
correct:

```bash
kicad-cli sch export netlist --format kicadsexpr -o out.net <name>.kicad_sch
grep -A6 '(comp' out.net | grep -E 'ref|footprint'
```

A `PWR_FLAG` has no footprint, and that is correct. Everything else needs one.

## Do not annotate a schematic with kicad-cli

`annotate_schematic` runs `kicad-cli sch annotate`, which gave the `PWR_FLAG`
symbols the references `1`, `2` and `3`. Eeschema would have written `#FLG01`.

**The `#` prefix is what keeps a symbol out of the bill of materials and off the
board.** Without it a power flag is a real component with no footprint, and
Update PCB From Schematic tries to place it.

ERC does not catch this. The check is the netlist:

```bash
kicad-cli sch export netlist --format kicadsexpr -o out.net <name>.kicad_sch
grep -A1 '(comp' out.net | grep '(ref'
```

Every reference listed there should be a real part. Five blocks were committed
with power flags in the bill of materials before this was found.

Annotate in Eeschema, or set the reference through the API when you place the
symbol.

## A Konnect project has no root sheet instance

`create_project` writes a schematic with no `(sheet_instances)` block. A flat
schematic does not need one. The moment the project gains a child sheet it does,
and KiCad opens it with:

> An error was found when loading the schematic that has been automatically
> fixed. Please save the schematic to repair the broken file.

Every valid root schematic ends with:

```
	(sheet_instances
		(path "/"
			(page "1")
		)
	)
```

`add_hierarchical_sheet` numbers the children from page 2 and never adds the
root's own entry. Add it before opening a module in Eeschema.

`kicad-cli sch upgrade` does not repair this, so it is not a check for it. Grep
for the block instead:

```bash
grep -c sheet_instances <root>.kicad_sch
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

## Do not hand-edit a schematic s-expression

`delete_schematic_component` with `all_units` removed one unit of a five unit
part and left four behind. Editing the file with a script to remove the rest
truncated it to zero bytes, and the whole project had to be rebuilt.

A KiCad schematic is not a text file with brackets. Symbol instances, the
`lib_symbols` cache and the instance paths all reference each other.

Delete the project and rebuild it. A block is twenty API calls, and a rebuild is
faster than repairing a corrupt file.

Field text is the one safe exception. Moving a `(at x y rot)` inside a single
`(property ...)` touches nothing else, and it is the only way to fix overlapping
Reference and Value text without opening Eeschema.

## The Konnect lock file is transient

`find <project> -name '*.lck'` can report a lock that belongs to Konnect's own
write, not to an open editor. Konnect takes the lock, writes and releases it, so
a scan run at the wrong moment gives a false positive.

The rule against writing a file that KiCad has open still stands. Check whether
the schematic editor is actually open, not whether a lock file existed once.

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

**Add a PWR_FLAG for each rail the block consumes.** Wrong. It was tested only
against a harness, where a block stands alone and the flag is the only way to
tell ERC the rail is fed. In a module the rail is fed by `power-input` or
`regulator-5v`, and every other block's flag becomes a second driver on the same
net. Nine blocks gave 19 `pin_to_pin` errors. Only the block that sources a rail
flags it.

**A block harness proves a block is correct.** Overstated. A harness cannot see
anything that only appears when blocks are combined: reference collisions,
duplicate power flags, or an interface that never becomes a sheet pin. All three
got through a clean harness ERC. Assemble a module early, and treat its ERC as
the real one.

**Blender is needed to make WRL models.** Wrong for anything KiCad ships. The
upstream `kicad-packages3D` repository still publishes the WRL files that the
installer drops. Download them. FreeCAD is only needed for parts KiCad does not
ship, and for custom variants.

## A submodule is a different checkout, not a view

`eurorack-common-library/` and `step-sequencer-8/hardware/shared/` are two
working copies of the same repository. Editing the first does nothing for a
project that reads the second.

Symbols vendored into the parent copy produced

```
[lib_symbol_issues]: Symbol 'Conn_02x07_Odd_Even' not found in symbol
library 'Eurorack Common'
```

while the file on disk plainly contained the symbol. The project's
`sym-lib-table` resolves `${KIPRJMOD}/../shared/`, which is the submodule.

The proper sequence is commit in the library repo, push, then move the
submodule pin. Copying the files across the two checkouts unblocks the work but
leaves the submodule dirty, and the pin still has to move before anyone else
can build the board.

**Check which copy a project reads before editing a shared library.** ERC will
tell you, but only after you have already done the work twice.

## Count pins from the file, never from the pitch

Widening a connector from 1x14 to 1x18, I worked out where the four new pins
were by adding 2.54mm steps to pin 1. That put pins 15 to 18 at the
coordinates of pins **13 to 16**, because the symbol had already been replaced
and re-centred underneath me.

Three of the four collisions were harmless, since those pins were ground
already. The fourth grounded `GATE_JACK`. The schematic looked right, ERC
passed the connection, and the fault only appeared as a net that had silently
vanished from the netlist: `GATE_JACK` was gone because it had merged into
`GND`.

Query the pin positions back from the file after any symbol swap. A net that
disappears from a netlist is as much a defect as one that appears wrong, so
check for absences and not only for errors.

## Registration features need board_only, or parity calls them errors

Fiducials and mill dowel holes are on the board and deliberately not in the
schematic. They are for the machine, not the module. So DRC with schematic
parity enabled reports every one of them:

```
Found 7 schematic parity issues
  7 [extra_footprint]     FID1..3, MH1..4
```

The fix is not to disable the check. Mark them `board_only` in the footprint's
attributes, which is KiCad's way of saying "this exists on the board by design
and has no symbol":

```
(attr smd board_only exclude_from_bom)
(attr board_only exclude_from_pos_files exclude_from_bom allow_missing_courtyard)
```

`exclude_from_bom` alone is not enough — that only keeps them out of the parts
list. Parity is a separate question and needs its own answer.

Do this when the registration features are added, not after. Seven spurious
errors is enough noise to make people switch parity off, and parity is the check
that would catch a real mismatch between board and schematic.

**The same attribute protects them from deletion.** Update PCB from Schematic
offers "Delete footprints with no symbols", which without `board_only` would
remove every fiducial and dowel hole and take the double-sided milling
registration with them.

## `\s` matches newlines, and that will eat your schematic

Repositioning 40 symbols with

    re.search(r'\n(\s*)\(at ([-\d.]+) ([-\d.]+)(?: ([-\d.]+))?\)', block)

produced a file KiCad refused to load, with balanced parens and no visible
damage. `\s` includes `\n`, so `\n\s*\(at` can skip past the symbol's own
position and match a nested `(at ...)` inside a property several lines down.
The edit then lands in the wrong element.

Use `[ \t]*` when you mean indentation. `\s*` means "any whitespace including
line breaks", which is almost never what you want in a line-oriented format.

Two things made this expensive to find:

- **`kicad-cli` says only "Failed to load schematic".** No line, no token, no
  reason. Balanced parens and a clean-looking diff tell you nothing.
- The obvious suspects were all innocent. Duplicate uuids, instance paths,
  no-connect formatting and the library symbols were each checked and cleared
  before the actual cause was reached.

**Bisect by construction, not by inspection.** Rebuilding from a known-good file
and adding one element at a time found it in a single pass, after inspection had
failed repeatedly. When a generated file breaks, stop reading it and start
halving it.

