# Power input

Eurorack power entry with reverse polarity protection and rail bulk decoupling.

Version 1.0.1

## What it does

The block connects a Eurorack bus cable to the module. It passes +12V and -12V
through a series Schottky diode each, and holds each rail with a bulk capacitor.
It does not regulate, filter, or provide +5V.

## Interface

The block uses global power symbols. A parent sheet needs no sheet pins.

| Net | Direction | Notes |
|---|---|---|
| `+12VA` | out | +12V minus one diode drop |
| `-12VA` | out | -12V plus one diode drop |
| `GND` | out | six header pins tied together |

`+12V_IN` and `-12V_IN` are local labels. They stay inside this sheet.

## Connector

J1 is a 10-pin Doepfer bus header. The pinout is the first 10 pins of the 16-pin
standard.

| Pins | Net |
|---|---|
| 1, 2 | -12V (red stripe) |
| 3, 4 | GND |
| 5, 6 | GND |
| 7, 8 | GND |
| 9, 10 | +12V |

The red stripe of the ribbon goes to pin 1. Check the cable before you connect
it. Some cables do not follow the standard.

## Protection

D1 and D2 are 1N5817 Schottky diodes in series with each rail.

D1 passes current into the module: the anode faces the header, the cathode feeds
`+12VA`.

D2 passes current out of the module: the cathode faces the header, the anode
feeds `-12VA`. Current flows from ground, through the load, into the negative
supply.

ERC cannot check diode direction. Read the schematic if you change this block.

## Bill of materials

| Ref | Value | Part |
|---|---|---|
| J1 | — | `Eurorack_Power_Header_(10_pin)` |
| D1, D2 | 1N5817 | DO-41, P7.62mm |
| C1, C2 | 10uF | 50V radial, D5mm |

All parts are in stock. See `preferred-values.md` in eurorack-common-library.

## Limits

Know these before you use the block.

**The diodes cost headroom.** Each diode drops about 0.2V at light load and up
to 0.45V at 1A. The rails reach the module at about +/-11.7V. Circuits that
swing close to the rails lose that margin.

**Schottky diodes leak.** Reverse leakage is higher than a silicon diode. The
protection is not perfect.

**A keyed header also prevents reversal.** A shrouded header stops a reversed
cable by shape, and costs no headroom. If you fit one, the diodes protect
against a fault the connector already prevents.

**There is no fuse.** A short in this module pulls down the rails for every
module in the case.

**There is no rail filter.** All modules share the rails. A series ferrite bead
would stop this module from putting noise on the bus.

**10uF is small.** It suits a few op-amps. Raise it for a larger analogue load.

**There is no HF decoupling here.** Put 100nF at each IC power pin, in the block
that holds the IC.

**A 10-pin header has no +5V and no CV or gate bus.** Use a 16-pin header if you
need them.

## Changelog

### 1.0.1

Assigned footprints. Every part was committed without one, so the block could
not reach a board. No circuit change.

### 1.0.0

First version. Header, series Schottky protection, and rail bulk capacitors.
