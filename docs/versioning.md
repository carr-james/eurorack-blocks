# Versioning

Blocks change. A board built last year should still be explicable this year, and
that is harder than it sounds for design blocks specifically.

## The problem

A placed design block may be a **copy**, not a live link. If it is, then:

- improving a block does **not** fix boards that already use it
- a board carries no inherent record of *which* version it was built from

Until that is confirmed either way (see "Open question" below), assume the worst
case and design for provenance.

## Scheme

**Per-block semver.** Each block versions independently — they change at
different rates and have no shared release cycle.

| bump | when |
|---|---|
| **major** | pin-incompatible: pins renamed/removed, or behaviour changed such that a host board needs rewiring |
| **minor** | new pins or features, existing wiring still correct |
| **patch** | value corrections, layout tidy-ups, footprint swaps with identical pinout |

**Three places the version lives**, deliberately redundant:

1. `<block-name>.json` — the canonical value, and what KiCad shows in the chooser.
2. **Visible text in the schematic fragment**, e.g. `vca-linear v1.2.0`. This is
   the load-bearing one. It travels into any board that places the block, so the
   board itself records its provenance even if the link is severed.
3. `CHANGELOG.md` in the block folder — because consumers cannot auto-update,
   they need to be able to read what changed and decide.

**Git tags** mark library-wide releases: `blocks-v<n>`. Consuming projects pin
this repo as a submodule, so the parent meta-repo commit records exactly which
block versions a module was built against.

## Updating a block in an existing board

There is no automatic path. The procedure is:

1. Read the block's `CHANGELOG.md` between the version stamped in your board and the current one.
2. For patch/minor: usually delete the old fragment and place the new one, then re-verify connections.
3. For major: expect to rewire. The changelog should say what moved.
4. Update the version text on the board so the next person sees the truth.

If a circuit is one you expect to revise *often* across many boards, a
**hierarchical sheet** may serve better than a design block — sheets stay linked
to their file, so edits propagate. Design blocks buy layout reuse; hierarchical
sheets buy live updates. Use the right one per circuit rather than forcing all
of them into one mechanism.

## Breakout boards

Breakouts carry their block's version **in copper**, not silkscreen. Laser-cured
silkscreen text on the Carvera renders poorly at small sizes; milled copper text
is legible and costs nothing extra.

## Open question

Whether a placed design block stays linked to its library is **not yet
confirmed** for KiCad 10.0.x — the release notes and docs do not say, and the
feature is new enough that forum reports are still shaking out.

Resolve it empirically before the library grows: make a block, place it, edit
the library copy, and see whether the placed instance changes. Record the answer
here. If instances *are* linked, points 2 and 3 above become belt-and-braces
rather than essential, and more circuits can move from hierarchical sheets to
blocks.
