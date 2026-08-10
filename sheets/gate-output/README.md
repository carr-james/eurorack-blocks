# Gate output

Protects and drives a +5V Eurorack gate or trigger from a CMOS logic output.

Version 2.2.0

## What it does

The block passes a CMOS logic signal to a jack. R1 limits the current if the
output is shorted. D1 and D2 clamp the pin if a patch cable feeds a rail voltage
back in.

The block does not amplify, invert, or shape the edge. The output level equals
the +5V rail.

## Interface

| Net | Direction | Notes |
|---|---|---|
| `GATE_IN` | in | 0V to +5V from a CMOS output |
| `GATE_OUT` | out | 0V to +5V through 1k |
| `+5V` | in | global, sets the clamp level |
| `GND` | in | global |

## Why there is no op-amp

A CMOS output drives a Eurorack gate input directly. A gate input is high
impedance, near 100k, and triggers near +2.5V.

The CD4017B sources 0.51mA minimum and 1mA typical at +5V with the output at
4.6V, per TI SCHS027C. A 100k load needs 50uA, so there is a wide margin.

Through R1 the output still reaches:

| Load | Level |
|---|---|
| 100k, one input | 4.9V |
| 10k, ten inputs in parallel | 4.1V |

Both clear a 2.5V threshold.

+5V is the Doepfer gate level. Almost every module accepts it.

Use a different block if you need +10V. An op-amp or a transistor stage can
raise the level. Do not add one here.

## Protection

A patch cable can put +12V or -12V on the output.

The CD4017B datasheet, TI SCHS027C, gives `DC INPUT CURRENT, ANY ONE INPUT` as
**±10mA**. That current flows through the on-chip protection diodes, so it sets
the limit for any pin that is driven outside the rails.

R1 is sized so the pin stays inside that limit **even if D1 and D2 do nothing**:

```
12V / 2k2 = 5.5mA, against a 10mA limit
```

Do not fit 1k. 12V through 1k is 12mA, which is over the limit.

D1 and D2 then add margin and hold the voltage excursion down:

| Fault | Path |
|---|---|
| Output above +5.6V | D1 conducts to the +5V rail |
| Output below -0.6V | D2 conducts from GND |

**Do not rely on the clamps alone.** A 1N4148 and the on-chip protection diode
have a similar forward voltage, so they share the fault current in a way you
cannot predict. The series resistor is what guarantees safety. The clamps are
the second line.

A Schottky clamp, such as a BAT54, has a lower forward voltage and would divert
the current predictably. That is the upgrade if this block ever needs to survive
a higher injected voltage.

### This block pushes current into the +5V rail

Under positive injection the fault current ends up in the +5V rail, through D1
or through the on-chip diode. A linear regulator cannot sink current, so a
lightly loaded rail will rise above +5V and threaten every logic chip on it.

`regulator-5v` carries a bleeder resistor for this reason. Do not use this block
on a +5V rail that has no minimum load.

## Bill of materials

| Ref | Value | Part |
|---|---|---|
| R1 | 2k2 | DIN0207 |
| D1, D2 | 1N4148 | DO-35 |

All parts are in stock. The block holds no multi-unit part, so you can place it
as many times as you need. Eight per-step triggers cost eight copies.

## Limits

**The output is +5V, not +10V.** A module with a high trigger threshold may not
respond. Measure before you assume.

**R1 sets the output impedance.** 2k2 against a 100k input loses about two
percent. A load below about 10k pulls the level down further. This does not
matter for a gate, which is read against a threshold, but do not reuse this
block for a CV output.

**The clamps protect the chip, not the patch.** A cable that shorts two outputs
together is survivable. A cable carrying a rail voltage is clamped. Neither case
is guaranteed safe for the module at the other end.

**ERC in this harness reports warnings, not errors.** `GATE_OUT` touches one pin
because it is an interface. See [docs/learnings.md](../../docs/learnings.md).

## Changelog

### 2.2.0

`GATE_IN` and `GATE_OUT` are hierarchical labels. They were plain net labels,
which are scoped to the sheet and never become sheet pins, so a parent module
could not reach either of them. No circuit change.

Header version was 2.0.0 while the changelog said 2.1.0. Corrected.

### 2.1.0

R1 raised from 1k to 2k2 after checking the CD4017B datasheet. 12V injected
through 1k is 12mA, over the ±10mA input current limit. The first version
assumed the clamp diodes would divert that current, which they do not do
reliably, because their forward voltage is close to the on-chip diode.

### 2.0.0

Removed the TL072. A +5V gate needs no op-amp, and the op-amp version wasted
half a package. Added D1 and D2 clamps, which the first version did not have.

Breaking: the block now consumes `+5V` instead of `+12VA` and `-12VA`.

### 1.0.0

First version. TL072 non-inverting gain of 2 for a +10V output.
