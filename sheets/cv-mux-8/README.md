# CV multiplexer, 8 way

Connects one of eight control voltages to a bus, chosen by a one hot select.

Version 1.0.0

## What it does

Eight analogue switches share one output. Each switch has its own control, so
the select comes straight from the one hot `STEP_0` to `STEP_7` outputs of
`step-counter` with no decoding.

The block does not buffer, scale or offset. It does not release the bus when the
module is inactive. See "The block does not release the bus".

## Interface

| Net | Direction | Notes |
|---|---|---|
| `CV_0` to `CV_7` | in | 0V to +5V, one per step |
| `STEP_0` to `STEP_7` | in | one hot, active high, CMOS level |
| `CV_BUS` | out | the selected CV, through about 1k |
| `+5V` | in | global |
| `GND` | in | global |

`STEP_k` closes the switch that connects `CV_k` to `CV_BUS`.

## Why the block runs on +5V

The control threshold scales with the supply. From TI SCHS051J:

| VDD | Control input high, VIHC |
|---|---|
| 5V | **3.5V** |
| 10V | 7V |
| 15V | 11V |

`step-counter` runs on +5V and its CD4017B gives at least 4.95V for a high. That
clears the 3.5V threshold by 1.45V. It does **not** clear the 7V threshold, so a
+10V supply here would need eight level shifters.

The block therefore runs on +5V, and **the CV range is 0V to +5V**. At 1V per
octave that is five octaves.

## The cost of +5V is on-resistance

| VDD | rON typ | rON max at 25 degC |
|---|---|---|
| 5V | 470 Ohm | **1050 Ohm** |
| 10V | 180 Ohm | 400 Ohm |
| 15V | 125 Ohm | 240 Ohm |

**This does not matter while the bus is unloaded.** Feed `CV_BUS` to an op-amp
input and nothing flows through the switch, so no voltage is dropped. A TL071
draws 200pA at most, which through 1050 Ohm is 0.21uV.

**It matters as soon as you load it.** Any current drawn from the bus meets up
to 1050 Ohm, and the value climbs to 1300 Ohm at 125 degC. Do not hang a
resistor divider, a passive filter or a panel jack on `CV_BUS`. Buffer it first.

Switch to switch matching is 15 Ohm maximum at 5V, so the eight steps stay
consistent with each other even where rON does matter.

## Verified figures

From TI SCHS051J, the CD4066B datasheet, at VDD = 5V and VSS = 0V.

| Parameter | Value |
|---|---|
| Control input high, VIHC | **3.5V** |
| Control input low, VILC | **1V** |
| Control input current | ±0.7uA max |
| rON | 470 Ohm typ, 1050 Ohm max at 25 degC |
| rON difference between switches | 15 Ohm max |
| Off-state leakage | 10pA typical at 10V, 25 degC |
| Quiescent current, all switches off | 6uA max |
| Propagation delay, signal in to signal out | 20ns typ, 40ns max |
| Input capacitance | 5pF typ |

Absolute maximum ratings:

| Parameter | Value |
|---|---|
| VDD − VSS | 20V |
| **Source or drain voltage** | **VSS − 0.5V to VDD + 0.5V** |
| Source or drain continuous current | ±20mA |
| Control input pin current | ±30mA |

Recommended operating conditions:

| Parameter | Value |
|---|---|
| VDD − VSS | 3V to 18V |
| Signal path voltage | VSS to VDD |
| Source or drain continuous current | ±10mA |

## The block does not release the bus

`CV_BUS` is driven whenever any `STEP_k` is high, and one of them always is.
A CD4017B sits on Q0 after a reset, so **a module waiting for its turn still
drives the bus with its step 0 voltage**.

Two chained modules would therefore fight over the bus. `step-counter` gives a
`HELD` output for exactly this, but the gate is not in this block:

- Gating each of the eight controls costs eight logic gates, which is two more
  packages.
- Gating the bus once costs one analogue switch.

One switch is the right answer, and a module needs the same gate for its gate
bus as well, so it belongs in its own block. Until that block exists, put a
`4066` switch between `CV_BUS` and the module CV buffer, with `HELD` on its
control.

**A single module does not need this.** With no chain there is nothing to fight
over.

## What happens between steps

The switches have no break before make. During a step change the outgoing and
incoming switches are both partly on for the length of a CD4017B output
transition, which is 100ns typical and 200ns maximum.

Two pot wipers are then joined through two switches. With 2k5 wiper impedance
and 1k05 per switch the worst case is about 0.7mA, far inside the ±10mA
recommended limit. The result is a sub-microsecond glitch on the bus.

The CD4066B matches its control to signal capacitance to keep charge injection
low, which the older CD4016B does not. Do not substitute a CD4016B here.

## Limits

**CV range is 0V to +5V.** Outside that the on-chip protection diodes conduct
into the rails. Anything wider needs a gain stage after the buffer, or a
different supply and level shifted controls.

**No input protection.** `CV_0` to `CV_7` expect pot wipers between `+5V` and
`GND`, which cannot leave the rails. If a module normals a jack into one of
them, condition it first. The absolute maximum on a signal pin is
VSS − 0.5V to VDD + 0.5V.

**No pull-down on the bus.** A pull-down would fight whichever module holds the
bus. `CV_BUS` floats when every switch is open, so the consumer must be an
op-amp input and nothing else.

**Buffer the bus.** See "The cost of +5V is on-resistance".

**Settling is slowest at 5V.** The datasheet curves put system settling at about
1.2us at VDD = 5V, improving sharply above 7.5V. This is irrelevant at a musical
clock rate and is recorded so the figure is not a surprise.

**+5V must exist.** The bus header carries no +5V. Pair this with
`regulator-5v`.

**ERC in this harness reports warnings, not errors.** See
[docs/learnings.md](../../docs/learnings.md).

## Bill of materials

| Ref | Value | Part |
|---|---|---|
| U1, U2 | 4066 | DIP-14, CD4066B quad bilateral switch |

`CD4066BM96` is in stock in SOIC-14. Use the `4066_SOIC` symbol for a surface
mount build.

## Changelog

### 1.0.0

First version. Two CD4066B packages, eight switches, one hot control straight
from `step-counter`. Verified against TI SCHS051J.
