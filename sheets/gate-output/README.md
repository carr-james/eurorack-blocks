# Gate output

Protects and drives a +5V Eurorack gate or trigger from a CMOS logic output.

Version 2.0.0

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
impedance, near 100k, and triggers near +2.5V. A CD4017 output sources about 1mA
at +5V, which is far more than the load needs.

+5V is the Doepfer gate level. Almost every module accepts it.

Use a different block if you need +10V. An op-amp or a transistor stage can
raise the level. Do not add one here.

## Protection

R1 alone is not enough. A patch cable can put +12V or -12V on the output. Through
1k that is 12mA into the CMOS pin, and the absolute maximum for a 4000 series pin
is 10mA.

D1 and D2 carry that current instead:

| Fault | Path |
|---|---|
| Output above +5.6V | D1 conducts to the +5V rail |
| Output below -0.6V | D2 conducts from GND |

The clamps sit on the CMOS side of R1. R1 then limits the fault current into the
diodes as well as into the chip. A 1N4148 passes 200mA, so it has a wide margin.

## Bill of materials

| Ref | Value | Part |
|---|---|---|
| R1 | 1k | DIN0207 |
| D1, D2 | 1N4148 | DO-35 |

All parts are in stock. The block holds no multi-unit part, so you can place it
as many times as you need. Eight per-step triggers cost eight copies.

## Limits

**The output is +5V, not +10V.** A module with a high trigger threshold may not
respond. Measure before you assume.

**R1 sets the output impedance.** 1k against a 100k input loses one percent. A
load below about 10k pulls the level down.

**The clamps protect the chip, not the patch.** A cable that shorts two outputs
together is survivable. A cable carrying a rail voltage is clamped. Neither case
is guaranteed safe for the module at the other end.

**ERC in this harness reports warnings, not errors.** `GATE_OUT` touches one pin
because it is an interface. See [docs/learnings.md](../../docs/learnings.md).

## Changelog

### 2.0.0

Removed the TL072. A +5V gate needs no op-amp, and the op-amp version wasted
half a package. Added D1 and D2 clamps, which the first version did not have.

Breaking: the block now consumes `+5V` instead of `+12VA` and `-12VA`.

### 1.0.0

First version. TL072 non-inverting gain of 2 for a +10V output.
