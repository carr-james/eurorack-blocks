# 5V regulator

Makes a +5V logic rail from +12VA, and holds it down when a jack pushes current
back into it.

Version 1.0.0

## What it does

U1 regulates +12VA to +5V. C1 and C2 hold the input and output. C3 handles high
frequency. R1 keeps a minimum load on the rail. D1 clamps the rail if something
pushes it above +5.6V.

The Eurorack bus header carries no +5V, so any module with CMOS logic needs
this block.

## Interface

| Net | Direction | Notes |
|---|---|---|
| `+12VA` | in | global |
| `+5V` | out | global |
| `GND` | in | global |

## Verified figures

From TI SLVS582L, the LP2950 datasheet.

| Parameter | Value |
|---|---|
| Input voltage, recommended | 2.0V to 30V |
| Output current | 0 to 100mA |
| **Minimum load current** | **0mA** |
| Dropout, new chip | 340mV typical |
| COUT | 1uF min, 2.2uF nominal, 100uF max |
| **COUT ESR, legacy chip** | **30mOhm to 5Ohm** |
| COUT ESR, new chip | 0 to 2Ohm |
| CIN | 1uF |
| RthJA, LP package (TO-92) | **140 degC/W** |

## The real current limit is about 50mA

The datasheet says 100mA. That figure does not survive a +12V input.

U1 drops 12V minus 5V, which is 7V. At 100mA that is 700mW. With RthJA of
140 degC/W the junction rises 98 degC, which reaches the 125 degC maximum before
you allow for a warm case.

| Load | Dissipation | Junction rise |
|---|---|---|
| 40mA | 280mW | 39 degC |
| 50mA | 350mW | 49 degC |
| 100mA | 700mW | 98 degC |

**Keep the 5V load under about 50mA.** CMOS logic draws far less, so this is
rarely a problem, but check before adding anything that switches hard or drives
LEDs.

## Why R1 is here

Not for stability. The datasheet gives a minimum load current of 0mA, so the
regulator is stable with nothing connected.

R1 exists because **a linear regulator cannot sink current**. Blocks such as
`gate-output` and `clock-input` clamp their jacks to +5V, so a patch cable
carrying +12V pushes current into this rail. With no load, the rail rises and
every logic chip on it sees over-voltage.

R1 at 1k draws 5mA, which absorbs a single injected jack:

| Source | Injected current |
|---|---|
| `gate-output`, 2k2 from +12V | 2.9mA |
| `clock-input`, 10k from +12V | 0.64mA |

## Why D1 is here

R1 alone cannot absorb several faults at once. Eight gate outputs all fed +12V
would push over 20mA, far past what R1 sinks.

D1 is a 5.6V Zener across the rail. It conducts above the rail voltage and holds
it there whatever the current, so protection does not depend on counting faults.

R1 and D1 together: R1 handles the small continuous case and keeps the rail
defined, D1 catches the rest.

## The capacitor trap

C2 is an electrolytic, not a ceramic, and this is deliberate.

The legacy die needs output capacitor ESR of **at least 30mOhm**. A modern
ceramic sits below that, so fitting a "better" capacitor can make the regulator
oscillate. An electrolytic sits inside the window for both the legacy and the
new die.

The `LP2950CZ-5.0` part number does not say which die is inside. The
electrolytic is safe either way.

C3 covers what the electrolytic does not at high frequency.

## Bill of materials

| Ref | Value | Part |
|---|---|---|
| U1 | LP2950-5.0 | TO-92 |
| C1, C2 | 10uF | 50V radial, D5mm |
| C3 | 100nF | ceramic, 2.5mm |
| R1 | 1k | DIN0207 |
| D1 | 1N5232B | 5.6V Zener, DO-35 |

D1 is not in stock. Everything else is.

## Limits

**Keep the load under about 50mA.** See above.

**R1 wastes 5mA continuously.** That is 35mW in U1 and 25mW in R1. Raise R1 if a
module is tight on current, but then D1 carries more of the protection.

**D1 is a Zener, not a TVS.** It has a soft knee and leaks slightly below 5.6V.
That is acceptable here. Use a TVS if the rail feeds something intolerant of a
few tens of microamps.

**No reverse protection on +12VA.** This block assumes `power-input` has already
done that.

## Changelog

### 1.0.0

First version. Verified against TI SLVS582L.
