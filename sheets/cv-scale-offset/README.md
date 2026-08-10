# CV scale and offset

Sets the range of a control voltage with two board trimmers.

Version 1.0.1

## What it does

U1A buffers the input so the block loads nothing. RV1 attenuates that by a
factor of 0 to 1. U1B amplifies by 2 and subtracts an offset taken from RV2.

```
CV_OUT = 2 k CV_IN - V_offset

k         = RV1 wiper fraction, 0 to 1
V_offset  = RV2 wiper voltage, 0V to +5V
```

Both controls are trimmers on the board. **Nothing here reaches the panel.** The
range is a build-time decision, not a performance control.

The block does not drive a jack. Follow it with `cv-output`.

## Interface

| Net | Direction | Notes |
|---|---|---|
| `CV_IN` | in | high impedance, internal |
| `CV_OUT` | out | low impedance, internal |
| `+12VA` | in | global |
| `-12VA` | in | global |
| `+5V` | in | global, the offset reference |
| `GND` | in | global |

## Settings

For a 0V to +5V input, which is what `cv-mux-8` gives:

| Range wanted | RV1 | RV2 | Notes |
|---|---|---|---|
| 0V to +10V | full | at `GND` | at the op-amp ceiling, see Limits |
| 0V to +8V | 0.8 | at `GND` | a common Eurorack pitch range |
| 0V to +5V | 0.5 | at `GND` | pass through |
| −5V to +5V | full | at `+5V` | bipolar, for modulation |
| −2.5V to +2.5V | 0.5 | mid | |

Set RV1 first with RV2 at `GND`, then set RV2. Measure, do not count turns.

## How U1B works

U1B is a non-inverting amplifier with the offset injected at its inverting node.
With `V+` held at the scaled signal Vs, and the inverting node at the same
voltage:

```
(Vs - V_offset) / R1 = (V_out - Vs) / R2

V_out = Vs (1 + R2/R1) - (R2/R1) V_offset
```

R1 and R2 are both 47k, so the gain is 2 and the offset passes at unity.
Changing the gain therefore changes how much offset reaches the output, which is
why RV1 is set first.

## Why U1A is here

RV1 is a 10k divider. Hung straight on `cv-mux-8`, it would sit across a CD4066B
switch of up to 1050 Ohm and lose up to 9.5 percent of the signal, by an amount
that changes with the trimmer setting.

U1A removes that. A TL07x input draws 200pA at most, so the source sees nothing.

It also fills the package. A TL072 is two amplifiers, this block uses both, and
nothing is wasted.

## The offset only shifts downward

RV2 spans `GND` to `+5V`, so `V_offset` is never negative and `CV_OUT` can only
move down. A positive shift needs a negative reference, which means a −5V
regulator this library does not have.

Both ranges a sequencer wants are reachable: unipolar up to +10V with the offset
at zero, and symmetric ±5V with the offset at +5V.

## Trimmer interaction

RV2's wiper impedance adds to R1, so it changes the gain slightly. Worst case is
mid-track, where a 10k trimmer presents 2.5k:

| RV2 position | Wiper impedance | Effective gain |
|---|---|---|
| at `GND` | 0 | 2.00 |
| mid | 2.5k | 1.95 |
| at `+5V` | 0 | 2.00 |

**Both useful settings sit at an end of the track, where the error is zero.** In
between it is 2.4 percent, and both trims are set by measurement anyway.

RV1 has no such problem. Its wiper drives an op-amp input.

## Verified figures

From TI SLOS080, the TL07x datasheet.

| Parameter | Value | Effect here |
|---|---|---|
| Input bias current | 200pA max at 25 degC | 200pA through 47k is 9uV |
| Common-mode input range | (VCC-) + 1.5V to (VCC+) | −10.5V to +12V here |
| Signal input pin current, absolute max | ±10mA | `CV_IN` is internal, see Limits |
| Output swing, RL >= 10k | ±12V at a ±15V supply | see below |
| Output short-circuit duration | continuous | |

## Limits

**Output swing is about ±10V, and 0 to +10V sits on that ceiling.** The datasheet
quotes swing at a ±15V supply only. On ±12V expect roughly two volts inside each
rail. Check the top of the range on the bench, and back RV1 off if it flattens.

**Gain doubles what comes in.** Noise and error from the source are amplified by
up to 2. From `cv-mux-8` that is microvolts, so it does not matter. From a noisy
source it would.

**`CV_IN` has no protection.** It expects an internal source. Do not wire a jack
to it. The TL07x input pins have a ±10mA absolute maximum and the common-mode
range stops 1.5V above the negative rail.

**`CV_OUT` has no protection either.** Follow this block with `cv-output`, which
carries the series resistor and the clamps. That adds a second buffer, which is
deliberate: it isolates the clamp diodes and their fault current from this
stage. If board space matters more, take `CV_OUT` through a 1k resistor and two
clamp diodes yourself, but then the protection is no longer guaranteed by a
block.

**The offset tracks the +5V rail.** `V_offset` comes from the LP2950 output, not
a precision reference. If the CV source is also derived from `+5V`, as sequencer
pots are, both drift together and the result is a scale error rather than an
offset error. That is tunable. A CV from any other source will not track.

**No feedback capacitor is fitted.** 47k around a JFET op-amp is modest, but if
the output rings, add a few tens of pF across R2. The right value depends on the
layout, so it is not in the bill of materials.

**RV2 draws 500uA from +5V continuously.** `regulator-5v` is good for about
50mA, so this is 1 percent of the budget.

**ERC in this harness reports warnings, not errors.** See
[docs/learnings.md](../../docs/learnings.md).

## Bill of materials

| Ref | Value | Part |
|---|---|---|
| U1 | TL072IP | PDIP-8, dual JFET op-amp |
| RV1, RV2 | 10k | Bourns `3296W-1-103LF`, vertical trimmer |
| R1, R2 | 47k | DIN0207 |
| C1, C2 | 100nF | ceramic, 2.5mm, supply decoupling, one per rail |

Everything is in stock.

There is no SOIC symbol for a dual op-amp in the library yet. `TL082HIDDFR` is
in stock in SOIC-8 with the same pinout, and needs a symbol before this block
can be built surface mount.

## Changelog

### 1.0.1

C1 and C2 are local supply decoupling, one per rail. No circuit change.

### 1.0.0

First version. TL072 buffer, trimmed attenuator, gain of 2 with a subtracted
offset. Verified against TI SLOS080.
