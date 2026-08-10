# Clock input, 3 channel

Conditions up to three external clocks, gates or triggers into clean CMOS logic
levels.

Version 1.0.0

## What it does

Three copies of `clock-input` sharing one package. Each channel takes a signal
from a jack and gives a clean 0V to +5V logic signal with the same polarity. It
tolerates any voltage present in a Eurorack case, including negative swings from
an LFO.

The circuit per channel is identical to `clock-input`. Read that block for the
analysis; this one only changes the channel count.

## Why three

A CD40106B holds six Schmitt inverters. A conditioned non-inverting channel
takes two, so **three channels use the whole package and leave nothing tied
off.**

`clock-input` is the right block for a module that conditions one signal. It
leaves four gates unused, which is a whole package wasted if a module places it
twice.

| Module needs | Use |
|---|---|
| 1 conditioned input | `clock-input` |
| 2 or 3 | this block |
| 4 or more | this block twice, or a different part |

A step sequencer needs a clock and a reset, which is what prompted this variant.

## Interface

| Net | Direction | Notes |
|---|---|---|
| `IN_1` to `IN_3` | in | from a jack, any Eurorack level |
| `OUT_1` to `OUT_3` | out | 0V to +5V, same polarity as the input |
| `+5V` | in | global |
| `GND` | in | global |

Leave an unused channel's `IN` and `OUT` unconnected at module level and put a
no-connect flag on the sheet pins. **Do not leave the inverter input floating**
— it is not floating here, because the 100k pulldown holds it at `GND`.

That is worth stating plainly: an unused channel of this block is safe, unlike
an unused gate of a bare CD40106B, because each channel carries its own
pulldown.

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

Per channel, with R at 10k and the clamps to `+5V` and `GND`:

| Case | Voltage at the pin | Current | Verdict |
|---|---|---|---|
| +5V gate | 4.55V | — | above VT+ max of 3.6V |
| +10V gate | clamped, 5.6V | 440uA | inside ±10mA |
| +12V injected | clamped, 5.6V | 640uA | inside ±10mA |
| -12V injected | clamped, -0.6V | 1.14mA | inside ±10mA |
| Nothing patched | 0V | — | below VT- min of 0.9V |

## Bill of materials

| Ref | Value | Part |
|---|---|---|
| U1 | 40106 | DIP-14, hex Schmitt inverter |
| R1, R3, R5 | 10k | DIN0207, series |
| R2, R4, R6 | 100k | DIN0207, pulldown |
| D1 to D6 | 1N4148 | DO-35, clamps |
| C1 | 100nF | ceramic, 2.5mm, supply decoupling |

`40106_SOIC` is in the library for a surface mount build.

## Limits

**The threshold is not adjustable.** It sits wherever the CD40106B puts it,
between 2.2V and 3.6V. A source whose high is below 3.6V may not trigger. Use a
comparator with a divider if you need to set the threshold.

**+5V must exist.** The bus header carries no +5V. Pair this with
`regulator-5v`.

**Fault current reaches the +5V rail.** Each channel's upper clamp pushes
injected current into `+5V`, and a linear regulator cannot sink it. Three
channels can inject three times as much as `clock-input` does.
`regulator-5v` carries a bleeder and a Zener for this, and the Zener is what
covers the multi-channel case.

**ERC in this harness reports warnings, not errors.** See
[docs/learnings.md](../../docs/learnings.md).

## Changelog

### 1.0.0

First version. Three channels of `clock-input` in one CD40106B, all six gates
used. Verified against TI SCHS097F.
