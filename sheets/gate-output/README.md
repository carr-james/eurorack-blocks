# Gate output

Drives a Eurorack gate or trigger output from a CMOS logic level.

Version 1.0.0

## What it does

The block takes a 0V to +5V logic signal and gives 0V to +10V at the output. A
series resistor protects the op-amp against a short to ground or to a rail. The
block does not invert, and it does not shape the edge.

## Interface

| Net | Direction | Notes |
|---|---|---|
| `GATE_IN` | in | 0V to +5V CMOS level |
| `GATE_OUT` | out | 0V to +10V through 1k |
| `+12VA` | in | global |
| `-12VA` | in | global |
| `GND` | in | global |

## How it works

U1 is a non-inverting amplifier. R1 and R2 set the gain:

```
gain = 1 + R1 / R2 = 1 + 100k / 100k = 2
```

A +5V input therefore gives +10V out. R3 sits in series with the output.

## Bill of materials

| Ref | Value | Part |
|---|---|---|
| U1 | TL072IP | DIP-8, one half used |
| R1, R2 | 100k | DIN0207 |
| R3 | 1k | DIN0207 |

All parts are in stock.

## Limits

**U1 has a spare half.** The block uses one of the two amplifiers. The module
owns the other. Give it to another block, or tie it as a follower with its input
at ground. Never leave the inputs floating: an unused half can oscillate and put
noise on the rails.

**The output is +10V, not +5V.** Most Eurorack gate inputs accept either. Change
R1 to match R2 for unity gain if a +5V gate is wanted.

**A TL072 does not reach the rails.** The output stops about 1.5V short, so +10V
from a +12V rail is close to the limit. It holds at light load. A heavy load
pulls it down.

**There is no output protection beyond R3.** R3 survives a short to ground. It
does not protect against a patch cable feeding a rail voltage back in. Add a
clamp if that risk matters.

**ERC in this harness reports warnings, not errors.** The rails, the input and
the interface labels come from the parent in real use. See
[docs/learnings.md](../../docs/learnings.md).

## Changelog

### 1.0.0

First version. Non-inverting gain of 2 with a series output resistor.
