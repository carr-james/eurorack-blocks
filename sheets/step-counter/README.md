# Step counter

Counts eight steps from a clock, and passes a token to the next counter so that
two or more modules make one longer sequence.

Version 1.0.0

## What it does

U1 is a decade counter. It advances one step on each rising clock edge and
raises one of `STEP_0` to `STEP_7`. When the eighth step finishes, U1 reaches Q8
and stops. Q8 leaves the block as `TOKEN_OUT`.

U2 holds the token logic. It stops the counter when the module does not hold the
token, and it stops the counter again when the module has finished its eight
steps.

The block does not hold the CV for a step, and it does not drive a jack. Pair it
with `cv-mux-8` and `gate-output`.

The block does not close the loop at the end of a chain. See "The wrap is not in
this block".

## Interface

| Net | Direction | Notes |
|---|---|---|
| `CLK` | in | CMOS level. Counts on the rising edge |
| `RESET_IN` | in | active high. Sets the counter to step 0 |
| `TOKEN_IN` | in | active high. Tie to `+5V` on the first module |
| `TOKEN_OUT` | out | high after the eighth step. Drives the next `TOKEN_IN` |
| `HELD` | out | high while this module is the active one |
| `STEP_0` to `STEP_7` | out | one hot, active high |
| `+5V` | in | global |
| `GND` | in | global |

## How chaining works

The chain passes a token. A module counts only while it holds the token.

1. Every module shares `CLK` and `RESET_IN`.
2. The first module ties `TOKEN_IN` to `+5V`, so it always holds the token
   until it finishes.
3. Each module wires its `TOKEN_OUT` to the `TOKEN_IN` of the next module.
4. A module that reaches Q8 raises `TOKEN_OUT` and freezes. The next module
   starts on the following clock edge.

Two modules give sixteen steps. Three give twenty four.

**The token is a level, not a pulse.** A level cannot be missed, and there is no
race between the clock edge and the token edge. Each module is either enabled or
not on any given edge, so no step is lost or repeated at the join.

### The logic

`CLOCK INHIBIT` on the CD4017B stops the counter when it is high.

```
CLK_INHIBIT  = NOT (TOKEN_IN AND NOT Q8)
HELD         = NOT CLK_INHIBIT
```

Three of the four NAND gates build it:

| Gate | Function |
|---|---|
| U2A | inverts `TOKEN_OUT` (Q8) |
| U2B | NAND of `TOKEN_IN` and NOT Q8, which is `CLK_INHIBIT` |
| U2C | inverts `CLK_INHIBIT`, which is `HELD` |

| `TOKEN_IN` | Q8 | `CLK_INHIBIT` | State |
|---|---|---|---|
| 0 | 0 | 1 | waiting for the token |
| 0 | 1 | 1 | cannot occur |
| 1 | 0 | 0 | counting steps 0 to 7 |
| 1 | 1 | 1 | finished, frozen on Q8 |

Q9 and the carry output are never reached, because the counter freezes on Q8.
Both carry a no-connect flag.

## Why `HELD` exists

**A module that does not hold the token still drives a step output.** After a
reset it sits on Q0, so `STEP_0` is high on every module in the chain at once.

`HELD` is the signal that fixes this. It is high only on the module that is
counting. Use it to gate whatever the step outputs drive, so that one module at
a time reaches a shared CV or gate bus.

Gate the bus once, not eight times. One analogue switch in series with the mux
output costs one switch. Gating each of the eight step outputs costs eight
gates.

## The wrap is not in this block

The last module in a chain has to return the sequence to step 0. Do not do this
by wiring `TOKEN_OUT` back to `RESET_IN`.

That loop cuts its own reset short. The reset clears Q8, which removes the
reset. The pulse it makes is one propagation delay wide, and TI SCHS027C gives
that delay as 265ns typical and 530ns maximum **with no minimum**. The counter
needs a reset pulse of up to 260ns. There is no guaranteed margin, and a chain
makes it worse, because one module has to reset every other module with a pulse
it terminates itself.

Inside a single package the trick is safe, because the internal clear happens
before the output moves. Across a chain it is not.

Give the module a reset with a width you set:

| Requirement | Figure at VDD = 5V |
|---|---|
| Minimum reset pulse width | 260ns |
| Minimum reset removal time before a clock edge | 400ns |

A spare Schmitt inverter from `clock-input` with an RC gives a pulse of a few
microseconds, which clears both figures by three orders of magnitude. Do this at
module level, where the spare gate lives.

## Verified figures

From TI SCHS027C, the CD4017B datasheet, at VDD = 5V.

| Parameter | Value |
|---|---|
| Clock edge | **rising** |
| `CLOCK INHIBIT` | **high inhibits** |
| `RESET` | **high clears to zero** |
| Clock input | **Schmitt trigger, unlimited rise and fall time** |
| DC input current, any one input | **±10mA** |
| Input voltage, all inputs | -0.5V to VDD + 0.5V |
| VIH min / VIL max | 3.5V / 1.5V |
| VOH min / VOL max | 4.95V / 0.05V |
| IOH / IOL min | 0.51mA |
| Maximum clock frequency | 2.5MHz min |
| Minimum clock pulse width | 200ns |
| Clock inhibit setup time | 230ns |
| Minimum reset pulse width | 260ns |
| Minimum reset removal time | 400ns |
| Propagation delay, clock to decode out | 325ns typ, **650ns max** |
| Propagation delay, reset to decode out | 265ns typ, 530ns max |

From TI SCHS021D, the CD4011B datasheet, at VDD = 5V.

| Parameter | Value |
|---|---|
| DC input current, any one input | **±10mA** |
| Recommended supply | 3V to 18V |
| VIH min / VIL max | 3.5V / 1.5V |
| VOH min / VOL max | 4.95V / 0.05V |
| IOH / IOL min | 0.51mA |
| Propagation delay | 125ns typ, **250ns max** |

Logic levels agree with room to spare. A CD4017B output gives at least 4.95V for
a high and at most 0.05V for a low, against a 3.5V and 1.5V CD4011B threshold.
That is 1.45V of noise margin in both directions.

## Maximum clock rate

`CLK_INHIBIT` has to settle before the next clock edge:

| Step | Worst case |
|---|---|
| Clock edge to Q8 | 650ns |
| Q8 through U2A | 250ns |
| U2A through U2B | 250ns |
| Clock inhibit setup | 230ns |
| **Total** | **1380ns** |

That gives about **720kHz**. The chain path is shorter, because `TOKEN_IN`
reaches U2B directly and skips U2A.

**Keep the clock below 100kHz.** A musical clock is far below this, and the
margin covers wiring between modules.

## Spare gate

U2D is unused. Its inputs are tied to `GND` and its output carries a no-connect
flag.

**A floating CMOS input is a fault, not an untidiness.** It drifts to the
transition region, both transistors conduct, and the device draws current and
oscillates.

## Bill of materials

| Ref | Value | Part |
|---|---|---|
| U1 | 4017 | DIP-16, CD4017B decade counter |
| U2 | 4011 | DIP-14, CD4011B quad 2 input NAND |

**Neither part is in stock.** Both are needed before this block can be built.
`4011_SOIC` is in the library for the SOIC-14 version. There is no SOIC symbol
for the 4017 yet.

## Limits

**Eight steps, not ten.** The CD4017B decodes ten outputs. Q8 is spent on the
token and Q9 is unreachable. A ten step variant would need a different token
scheme.

**No input protection.** `CLK`, `RESET_IN` and `TOKEN_IN` are internal CMOS
nets. The CD4017B and CD4011B inputs both have a ±10mA absolute maximum and stop
0.5V outside the rails. Do not wire a jack to any of them. Put a `clock-input`
block in front of anything that reaches a panel.

**Chain wiring is not protected either.** `TOKEN_OUT` between modules is a bare
CMOS output. A ribbon between adjacent modules is fine. A patch cable is not,
and needs the jack interface treatment at both ends.

**Consumers must gate with `HELD`.** See "Why `HELD` exists". A module that is
waiting still holds `STEP_0` high.

**The wrap belongs to the module.** See "The wrap is not in this block".

**+5V must exist.** The bus header carries no +5V. Pair this with
`regulator-5v`.

**ERC in this harness reports warnings, not errors.** The interface labels are
hierarchical, and a hierarchical label has no parent in a harness. See
[docs/learnings.md](../../docs/learnings.md).

## Changelog

### 1.0.0

First version. CD4017B counter with CD4011B token logic, level based chaining,
and a `HELD` output for bus arbitration. Verified against TI SCHS027C and TI
SCHS021D.
