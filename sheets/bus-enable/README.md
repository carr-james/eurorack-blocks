# Bus enable

Connects up to four signals to shared buses, and disconnects them all when the
module is not the active one.

Version 1.0.0

## What it does

Four analogue switches, one common control. When `EN` is high all four channels
pass. When `EN` is low all four are open and the module is invisible to the
buses.

This is what makes a chained module safe. `step-counter` gives an `EN` signal
ready made: its `HELD` output is high on exactly one module in a chain.

The block does not select, buffer or scale. It only connects or disconnects.

## Interface

| Net | Direction | Notes |
|---|---|---|
| `EN` | in | active high, CMOS level. Drive from `HELD` |
| `CH1_IN` to `CH4_IN` | in | module side, 0V to +5V |
| `CH1_BUS` to `CH4_BUS` | bidirectional | shared bus side |
| `+5V` | in | global |
| `GND` | in | global |

The switches are bidirectional, so `IN` and `BUS` are naming, not direction.
`IN` means the module side and `BUS` means the shared side.

## Intended use in a step sequencer

| Channel | Carries |
|---|---|
| CH1 | `CV_BUS` from `cv-mux-8` |
| CH2 | the gate bus |
| CH3, CH4 | spare, for a second CV row |

Leave unused channels unconnected at module level and put a no-connect flag on
the sheet pins. An open analogue pin on a CD4066B is harmless, unlike a floating
logic input.

## Where it goes in the chain

```
pots -> cv-mux-8 -> bus-enable -> CV_BUS -> cv-scale-offset -> cv-output -> jack
```

**`bus-enable` must come before `cv-scale-offset`, not after.** The switch runs
on +5V and passes 0V to +5V only. `cv-scale-offset` can put out ±10V, which is
outside the signal range and would be clamped into the rails.

Every module in a chain carries its own `cv-scale-offset` and `cv-output`, so
every module has a working output jack showing the whole sequence. Use one of
them. If you want them to agree, the trimmers have to be set the same.

## A single module does not need this block

With no chain there is nothing to arbitrate. Take `CV_BUS` straight from
`cv-mux-8`. Fit `bus-enable` when a second module is added.

## Verified figures

From TI SCHS051J, the CD4066B datasheet, at VDD = 5V and VSS = 0V.

| Parameter | Value |
|---|---|
| Control input high, VIHC | **3.5V** |
| Control input low, VILC | 1V |
| Control input current | ±0.7uA per switch |
| rON | 470 Ohm typ, 1050 Ohm max at 25 degC |
| Off-state leakage | 10pA typical at 10V, 25 degC |
| Signal path voltage | VSS to VDD |
| Source or drain continuous current | ±10mA recommended, ±20mA absolute max |
| Propagation delay | 20ns typ, 40ns max |

A `HELD` output from a CD4011B gives at least 4.95V, against the 3.5V threshold.
It drives four control inputs, which is 2.8uA against a 0.51mA minimum drive.
Both have a wide margin.

## Series resistance adds up

A CV that passes through `cv-mux-8` and then this block sees two switches, so up
to **2100 Ohm** in the worst case.

That costs nothing while the bus feeds only an op-amp input. `cv-scale-offset`
draws 200pA at most, which through 2100 Ohm is 0.42uV.

It would cost something if you loaded the bus. Do not.

## What happens at the handover

At the clock edge that passes the token, one module's `EN` falls and the next
module's `EN` rises. Both signals come from the same clock edge through the same
number of gates, so the mismatch is the difference between two packages, which
is tens of nanoseconds.

During any overlap two CV sources are joined through four switches, about 4k2.
The worst case is 5V across that, or 1.2mA, well inside the ±10mA limit. During
any gap the bus floats for the same tens of nanoseconds.

Neither matters at a musical clock rate.

## Limits

**The bus floats when every module is disabled.** There is no pull-down, and
that is deliberate: a pull-down would sit across up to 2100 Ohm of switch
resistance and put a permanent error on every CV. A float is transient, because
one module always holds the token once the chain is running.

At power on, before the first reset, the bus can float for a few milliseconds
and an op-amp downstream will drift. Nothing is damaged. If that matters, put
1M to `GND` at the consumer and accept a 0.2 percent scale error.

**A digital channel does need a pull-down.** A floating CMOS logic input is a
fault, not an untidiness. If a channel carries a gate, put a pull-down at the
consumer, where it costs nothing.

**Signal range is 0V to +5V.** Set by the supply. See "Where it goes in the
chain".

**No input protection.** Every pin here is internal. The absolute maximum on a
signal pin is VSS − 0.5V to VDD + 0.5V.

**+5V must exist.** The bus header carries no +5V. Pair this with
`regulator-5v`.

**ERC in this harness reports warnings, not errors.** See
[docs/learnings.md](../../docs/learnings.md).

## Bill of materials

| Ref | Value | Part |
|---|---|---|
| U1 | 4066 | DIP-14, CD4066B quad bilateral switch |
| C1 | 100nF | ceramic, 2.5mm, supply decoupling |

`CD4066BM96` is in stock in SOIC-14. Use the `4066_SOIC` symbol for a surface
mount build.

C1 is local supply decoupling across the package. **This is the first block to
carry it.** The earlier logic blocks have none, which is a gap rather than a
decision, and matters most on a milled two layer board with no ground plane.

## Changelog

### 1.0.0

First version. One CD4066B, four switches, one common enable. Verified against
TI SCHS051J.
