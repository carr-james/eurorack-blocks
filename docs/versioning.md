# Versioning

A board built last year must stay explicable this year.

## The risk

A placed design block can be a copy, not a link. If it is a copy:

- An improvement does not reach boards that already use the block.
- The board keeps no record of the version it used.

Hierarchical sheets do not have this risk. They stay linked to the sheet file.

Assume the risk until you test it. See "Open question".

## Scheme

Each circuit has its own semver. Circuits change at different rates.

| Bump | When |
|---|---|
| major | Pins change, or the host board needs rework |
| minor | New pins or features. Existing wiring stays correct |
| patch | Value fix, layout tidy, or footprint swap with the same pinout |

Put the version in three places:

1. `<name>.json` — the value KiCad shows.
2. Text in the schematic fragment, for example `vca-linear v1.2.0`. This text
   travels into the host board. If the link breaks, this is the only record.
3. `CHANGELOG.md` in the circuit folder.

Tag the repo `blocks-v<n>` for a release. A project pins this repo as a
submodule. The meta-repo commit then records the exact versions.

## Update a circuit in a board

A hierarchical sheet updates when you update the submodule pin.

A design block has no automatic path:

1. Read `CHANGELOG.md` between the stamped version and the current version.
2. For a patch or minor change, delete the old fragment and place the new one.
3. For a major change, expect rework. The changelog says what moved.
4. Update the version text on the board.

## Breakout boards

Put the version in copper, not silkscreen. Laser silkscreen prints small text
badly.

## Open question

KiCad 10.0.x does not document whether a placed design block stays linked.

Test it before the library grows. Make a block. Place it. Edit the library copy.
Look at the placed instance. Record the answer here.

If instances stay linked, points 2 and 3 become a safety net, and more circuits
can move from sheets to blocks.
