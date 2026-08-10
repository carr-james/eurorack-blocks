# Clock input

Conditions an external clock, gate or trigger into a clean CMOS logic level.

Version 1.1.1

## What it does

The block accepts a signal from a jack and gives a clean 0V to +5V logic signal
with the same polarity. It tolerates any voltage present in a Eurorack case,
including negative swings from an LFO.

U1A and U1B are Schmitt-trigger inverters in series. Two inversions give a
non-inverting output, and the hysteresis rejects a slow or noisy edge.

## Interface

| Net | Direction | Notes |
|---|---|---|
| `CLK_IN` | in | from a jack, any Eurorack level |
| `CLK_OUT` | out | 0V to +5V, same polarity as the input |
| `+5V` | in | global |
| `GND` | in | global |

## Verified figures

From TI SCHS097F, the CD40106B datasheet, at VDD = 5V.

| Parameter | Min | Typ | Max |
|---|---|---|---|
| Positive trigger threshold, VT+ | 2.2V | 2.9V | **3.6V** |
| Negative trigger threshold, VT- | **0.9V** | 1.9V | 2.8V |
| DC input current, any one input | | | **±10mA** |
| Input voltage, all inputs | -0.5V | | VDD + 0.5V |

Design to the worst case: a high must exceed **3.6V**, and a low must fall below
**0.9V**.

## Why a divider does not work

A plain divider cannot satisfy both ends:

- A +5V gate must still pass 3.6V, so the ratio must be above 0.72.
- A +12V signal must stay under VDD + 0.5V, which is 5.5V, so the ratio must be
  below 0.46.

There is no ratio that does both. The block therefore uses a series resistor
with clamp diodes, which limits current instead of dividing voltage.

## Component values

R1 is 10k. An input draws no current, so a high value costs nothing and lowers
the fault current.

R2 is 100k, ten times R1, so the divider it forms barely attenuates.

| Case | Voltage at the pin | Current | Verdict |
|---|---|---|---|
| +5V gate | 4.55V | — | above VT+ max of 3.6V |
| +10V gate | clamped, 5.6V | 440uA | inside ±10mA |
| +12V injected | clamped, 5.6V | 640uA | inside ±10mA |
| -12V injected | clamped, -0.6V | 1.14mA | inside ±10mA |
| Nothing patched | 0V | — | below VT- min of 0.9V |

## Hysteresis handles a sloppy source

Some equipment does not return its gate output to 0V. An "off" state sitting
near 0.6V is common.

VT- is 0.9V minimum, so 0.6V still reads as a low. The typical hysteresis of
about 1V at VDD = 5V keeps a noisy edge from producing several transitions.

## Spare gates

The CD40106B holds six inverters and this block uses two. U1C to U1F have their
inputs tied to GND and their outputs marked no-connect.

**A floating CMOS input is a fault, not an untidiness.** It drifts to the
transition region, both transistors conduct, and the device draws current and
oscillates. The block ties them so it cannot be assembled wrongly.

## Bill of materials

| Ref | Value | Part |
|---|---|---|
| U1 | 40106 | DIP-14, hex Schmitt inverter |
| R1 | 10k | DIN0207 |
| R2 | 100k | DIN0207 |
| D1, D2 | 1N4148 | DO-35 |
| C1 | 100nF | ceramic, 2.5mm, supply decoupling |

## Limits

**Four of six gates are unused.** A module needing two or three conditioned
inputs should not place this block two or three times, because each copy is a
whole package. Build a multi-channel variant instead. The sequencer needs a
clock and a reset, so that variant is worth having.

**The threshold is not adjustable.** It sits wherever the CD40106B puts it,
between 2.2V and 3.6V. A source whose high is below 3.6V may not trigger. Use a
comparator with a divider if you need to set the threshold.

**+5V must exist.** The bus header carries no +5V. Pair this with
`regulator-5v`.

**Fault current reaches the +5V rail.** D1 pushes injected current into +5V, and
a linear regulator cannot sink it. `regulator-5v` carries a bleeder for this.

**ERC in this harness reports warnings, not errors.** See
[docs/learnings.md](../../docs/learnings.md).

## Changelog

### 1.1.1

C1 is local supply decoupling across U1. No circuit change.

### 1.1.0

`CLK_IN` and `CLK_OUT` are hierarchical labels. They were plain net labels,
which are scoped to the sheet and never become sheet pins, so a parent module
could not reach either of them.

Assigned the DIP-14 footprint to U1, which was committed without one.

No circuit change.

### 1.0.0

First version. Series resistor with clamps, pull-down, and two Schmitt inverters
for a non-inverting output. Verified against TI SCHS097F.
