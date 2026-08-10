# CV output

Buffers a control voltage and drives it to a jack.

Version 1.0.0

## What it does

U1 buffers a high impedance source, such as a potentiometer wiper or the output
of an analogue switch, at unity gain. R1 isolates the output. D1 and D2 clamp
the op-amp output if a patch cable applies a voltage beyond the rails.

The block does not scale, offset, or invert. Put those in a separate block.

## Interface

| Net | Direction | Notes |
|---|---|---|
| `CV_IN` | in | high impedance, internal to the module |
| `CV_OUT` | out | through 1k |
| `+12VA` | in | global |
| `-12VA` | in | global |

## Verified figures

From TI SLOS080, the TL07x datasheet.

| Parameter | Value | Effect here |
|---|---|---|
| Output short-circuit duration | **continuous** | a short to ground or a rail does not damage U1 |
| Supply voltage, absolute max | 42V total | +/-12V is well inside |
| Signal input pin current, absolute max | **+/-10mA** | matters for the input, see Limits |
| Common-mode input range | (VCC-) + 1.5V to (VCC+) | do not drive `CV_IN` to the negative rail |
| Output swing, RL >= 10k | +/-12V at +/-15V supply | expect about +/-10V on a +/-12V supply |
| Output swing, RL >= 2k | +/-10V at +/-15V supply | a heavy load costs swing |

## Why R1 is 1k and not 2k2

`gate-output` uses 2k2 because a CMOS output has a hard +/-10mA limit and no
internal current limiting, so the resistor alone has to keep injected current
inside that limit.

The TL071 output is different. It is short-circuit protected **continuously**,
so it defends itself. R1 is here to isolate capacitive load and to limit current
into the clamps, not to save the part.

That lets R1 stay low, which matters for a CV output:

| R1 | Error into a 100k input |
|---|---|
| 1k | 1% |
| 2k2 | 2.2% |

A scale error of this kind is constant, so a VCO with a scale trim absorbs it.
It is still worth keeping small.

**Do not copy the 2k2 value from `gate-output` into this block.** The parts fail
differently.

## Limits

**`CV_IN` has no protection.** The block expects an internal source. The TL071
input pins have a +/-10mA absolute maximum, and the common-mode range stops
1.5V above the negative rail. Do not wire a jack straight to `CV_IN`. Use an
input block with a series resistor and clamps.

**Output swing is about +/-10V, not +/-12V.** A TL07x does not reach its rails.
The datasheet quotes +/-12V minimum with a +/-15V supply and a load of 10k or
more, so expect roughly two volts less at each rail here. Enough for a 0V to
+8V sequencer CV, not enough for a full +/-12V swing.

**A load below 10k costs swing.** The datasheet drops to +/-10V at 2k, again on
+/-15V. Several patched destinations in parallel will show this.

**Fault current reaches the rails.** D1 and D2 push injected current into
+12VA or -12VA. Those rails feed the whole module and are held by the power
input capacitors, so the effect is smaller than on the +5V logic rail, but the
path exists.

**ERC in this harness reports warnings, not errors.** The rails, the input and
the interface labels come from the parent in real use. See
[docs/learnings.md](../../docs/learnings.md).

## Bill of materials

| Ref | Value | Part |
|---|---|---|
| U1 | TL071CP | PDIP-8. `TL071CD` is the SOIC-8 variant |
| R1 | 1k | DIN0207 |
| D1, D2 | 1N4148 | DO-35 |

## Changelog

### 1.0.0

First version. TL071 unity buffer, 1k series output, clamps to both rails.
Verified against TI SLOS080.
