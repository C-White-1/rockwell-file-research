# RSS instruction coverage closeout audit

Audit date: 2026-08-22

## Scope

This audit closes the first controlled RSLogix Micro Starter Lite instruction
palette pass for the MicroLogix 1100 Series B profile. It evaluates serialized
RSS evidence and decoder coverage; it does not claim universal selector values
or runtime semantics across other processors, firmware, or software editions.

## Reconciled classification

| Classification | Count |
| --- | ---: |
| Confirmed serialized instructions | 92 |
| Unavailable for the controlled profile | 26 |
| Normalized palette entries | 1 |
| Structural entries | 1 |
| Unresolved transcribed candidates | 0 |
| Total classified palette entries | 120 |

The 92 confirmed instructions have unique selectors within this profile. AWT
is not counted as a second confirmed instruction because its decompressed
PROGRAM FILES payload is byte-identical to AWA. END is structural rather than
a selectable serialized instruction.

## Aggregate reachability

The aggregate instruction scanner was run across every ignored controlled RSS
fixture in `private-fixtures/RSLogix_Lite_tests`.

- All 92 confirmed mnemonics were discovered.
- No fixture failed container reading or PROGRAM FILES decompression.
- No discovered mnemonic mapped to more than one selector.
- Private fixture contents remain ignored and are not publication artifacts.

The public test suite also verifies individual recognizers and representative
aggregate ordering. A ledger-integrity test now checks the declared confirmed
total, mnemonic uniqueness, selector uniqueness, and empty backlog statement.

## Confidence boundaries

**Strongly established:** controlled-profile selectors, recognized framing,
ordered printable operand fields, preserved evidence offsets, and aggregate
scanner reachability.

**Profile-scoped:** instruction availability and selector values. An
instruction unavailable for MicroLogix 1100 Series B is not declared
unsupported by other controllers.

**Not fully established:** complete runtime behavior, every legal operand
form, and binary setup data that does not appear as a printable PROGRAM FILES
operand.

## Follow-up evidence priorities

1. Decode the extended MSG setup payload using one-field-at-a-time fixtures.
2. Correlate PID setup-dialog values with their DATA FILES representation.
3. Create RCP variants for every editor-supported file operation.
4. Create an LCD `Display with Input: Yes` variant.
5. Establish RTA runtime configuration and behavior from authoritative
   documentation or controlled execution evidence.
6. Vary automatic/read-only ASCII status fields where executable evidence can
   safely produce nonzero values.
7. Repeat the palette audit for another processor profile without reusing
   MicroLogix 1100 selectors as assumptions.

## Closeout result

The controlled palette transcription is fully classified and the decoder can
reach every confirmed serialized instruction. Future work should strengthen
semantic depth and cross-profile coverage rather than add guessed mnemonics to
this completed profile.
