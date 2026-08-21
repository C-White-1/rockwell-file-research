# RSLogix 500 instruction coverage

This register tracks controlled RSS instruction-decoding work for the
RSLogix Micro Starter Lite MicroLogix 1100 Series B profile. It is a research
queue, not a claim that every listed instruction is supported by every
processor, firmware revision, or RSLogix edition.

## Status definitions

- **Confirmed**: a controlled fixture establishes the instruction identity,
  framing, selector, and currently documented operand roles.
- **Partial**: some structure is established, but another controlled fixture
  is required before the record can be promoted to confirmed.
- **Untested**: observed in the instruction palette or authoritative
  instruction catalogue, but no controlled fixture has been evaluated.
- **Unavailable**: the selected processor/profile prevents creation of a
  fixture. Record the observed reason rather than guessing an encoding.
- **Not applicable**: the entry is not a serialized ladder instruction for the
  selected profile.

Selectors are profile-scoped evidence. They are not treated as universal RSS
opcodes.

## Confirmed instruction records

| Instruction | Selector | Operand roles | Status |
| --- | ---: | --- | --- |
| `CTU` | `0x11` | counter, preset, accumulator | Confirmed |
| `CTD` | `0x12` | counter, preset, accumulator | Confirmed |
| `RES` | `0x13` | operand | Confirmed |
| `CLR` | `0x14` | destination | Confirmed |
| `NOT` | `0x1B` | source, destination | Confirmed |
| `MOV` | `0x1C` | source, destination | Confirmed |
| `NEG` | `0x1E` | source, destination | Confirmed |
| `AND` | `0x23` | source_a, source_b, destination | Confirmed |
| `OR` | `0x24` | source_a, source_b, destination | Confirmed |
| `XOR` | `0x25` | source_a, source_b, destination | Confirmed |
| `ADD` | `0x27` | source_a, source_b, destination | Confirmed |
| `SUB` | `0x28` | source_a, source_b, destination | Confirmed |
| `MUL` | `0x29` | source_a, source_b, destination | Confirmed |
| `DIV` | `0x2A` | source_a, source_b, destination | Confirmed |
| `OTE` | `0x2F` | operand | Confirmed |
| `OTL` | `0x30` | operand | Confirmed |
| `OTU` | `0x31` | operand | Confirmed |
| `EQU` | `0x32` | source_a, source_b | Confirmed |
| `NEQ` | `0x33` | source_a, source_b | Confirmed |
| `GRT` | `0x34` | source_a, source_b | Confirmed |
| `LES` | `0x36` | source_a, source_b | Confirmed |
| `LEQ` | `0x37` | source_a, source_b | Confirmed |
| `XIC` | `0x39` | operand | Confirmed |
| `XIO` | `0x3A` | operand | Confirmed |
| `SQR` | `0x46` | source, destination | Confirmed |
| `RTO` | `0xA3` | timer, time_base, preset, accumulator | Confirmed |
| `TOF` | `0xA6` | timer, time_base, preset, accumulator | Confirmed |
| `TON` | `0xA7` | timer, time_base, preset, accumulator | Confirmed |
| `ABS` | `0x98` | source, destination | Confirmed |

Confirmed total: **29**.

## Candidate backlog

These mnemonic labels were transcribed from the observed instruction palette.
They remain untested unless they appear in the confirmed table. Palette state,
processor support, and operand availability must be recorded while each
fixture is created.

- Comparison: `GEQ`, `MEQ`, `LIM`.
- Arithmetic and conversion: `DDV`, `SCP`, `SCL`, `SWP`, `TOD`, `FRD`,
  `DEG`, `RAD`, `XPY`.
- Mathematical: `ACS`, `ASN`, `ATN`, `COS`, `LN`, `LOG`, `SIN`, `TAN`.
- File and data: `COP`, `FLL`, `FFL`, `FFU`, `LFL`, `LFU`, `MVM`.
- Program control: `JMP`, `LBL`, `JSR`, `SBR`, `RET`, `MCR`, `SUS`, `TND`,
  `END`.
- Bit and edge control: `ONS`, `OSR`, `OSF`, `UIE`, `UID`, `UIF`.
- Shift and sequencer: `BSL`, `BSR`, `SQC`, `SQL`, `SQO`.
- Process and control: `PID`, `PTO`, `PWM`, `RMP`.
- Messaging and communications: `MSG`, `SVC`, `EEM`.
- High-speed and immediate I/O: `HSC`, `HSE`, `HSD`, `HSL`, `IIM`, `IOM`,
  `IIE`, `IID`.
- ASCII and string: `ACI`, `ACN`, `AEX`, `AHL`, `AIC`, `ARD`, `ARL`, `ASC`,
  `ASR`, `AWA`, `AWT`.
- Recipe, event, and specialised: `CEM`, `DCD`, `DDT`, `DEM`, `DLG`, `ENC`,
  `GCD`, `INT`, `LCD`, `RAC`, `RCP`, `REF`, `RHC`, `RPI`, `RTA`, `SOR`,
  `STE`, `STS`, `STD`.

The backlog is a working transcription. It must be reconciled against the
selected processor's instruction palette and Rockwell documentation before it
is declared complete.

## Fixture workflow

For each candidate:

1. Confirm whether it is enabled for the selected MicroLogix 1100 Series B
   profile.
2. Create one minimal fixture using the next sequential `pNN` filename.
3. Record every operand and any configuration choice.
4. Save the RSS file without descriptions or symbols unless those are the
   variables under test.
5. Compare the decompressed framed record with structurally similar confirmed
   fixtures.
6. Create operand-only variants when field roles or encodings are ambiguous.
7. Add a profile-scoped recognizer, tests, and research evidence.
8. Run the complete quality suite before promotion to **Confirmed**.

## Next fixture

The next planned comparison fixture is `GEQ`, using source A `N7:0`, source B
`N7:1`, and a following `OTE B3:0/1` to consume the rung condition.
