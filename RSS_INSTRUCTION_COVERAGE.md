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
- **Normalized**: a separately selected palette entry produces a record
  byte-identical to another confirmed instruction, so the RSS evidence cannot
  preserve a distinct mnemonic identity.
- **Not applicable**: the entry is not a serialized ladder instruction for the
  selected profile.

Selectors are profile-scoped evidence. They are not treated as universal RSS
opcodes.

## Confirmed instruction records

| Instruction | Selector | Operand roles | Status |
| --- | ---: | --- | --- |
| `MCR` | `0x08` | none | Confirmed |
| `RET` | `0x09` | none | Confirmed |
| `TND` | `0x0B` | none | Confirmed |
| `CTU` | `0x11` | counter, preset, accumulator | Confirmed |
| `CTD` | `0x12` | counter, preset, accumulator | Confirmed |
| `RES` | `0x13` | operand | Confirmed |
| `CLR` | `0x14` | destination | Confirmed |
| `JSR` | `0x15` | subroutine | Confirmed |
| `JMP` | `0x16` | label | Confirmed |
| `TOD` | `0x17` | source, destination | Confirmed |
| `FRD` | `0x18` | source, destination | Confirmed |
| `NOT` | `0x1B` | source, destination | Confirmed |
| `MOV` | `0x1C` | source, destination | Confirmed |
| `NEG` | `0x1E` | source, destination | Confirmed |
| `SUS` | `0x1F` | suspend_id | Confirmed |
| `DCD` | `0x20` | source, destination | Confirmed |
| `AND` | `0x23` | source_a, source_b, destination | Confirmed |
| `OR` | `0x24` | source_a, source_b, destination | Confirmed |
| `XOR` | `0x25` | source_a, source_b, destination | Confirmed |
| `MVM` | `0x26` | source, mask, destination | Confirmed |
| `ADD` | `0x27` | source_a, source_b, destination | Confirmed |
| `SUB` | `0x28` | source_a, source_b, destination | Confirmed |
| `MUL` | `0x29` | source_a, source_b, destination | Confirmed |
| `DIV` | `0x2A` | source_a, source_b, destination | Confirmed |
| `BSR` | `0x2B` | file, control, bit_address, length | Confirmed |
| `BSL` | `0x2C` | file, control, bit_address, length | Confirmed |
| `SQO` | `0x2D` | file/mask/destination/control/length/position | Confirmed |
| `SQC` | `0x2E` | file, mask, source, control, length, position | Confirmed |
| `OTE` | `0x2F` | operand | Confirmed |
| `OTL` | `0x30` | operand | Confirmed |
| `OTU` | `0x31` | operand | Confirmed |
| `EQU` | `0x32` | source_a, source_b | Confirmed |
| `NEQ` | `0x33` | source_a, source_b | Confirmed |
| `GRT` | `0x34` | source_a, source_b | Confirmed |
| `GEQ` | `0x35` | source_a, source_b | Confirmed |
| `LES` | `0x36` | source_a, source_b | Confirmed |
| `LEQ` | `0x37` | source_a, source_b | Confirmed |
| `MEQ` | `0x38` | source, mask, compare | Confirmed |
| `LIM` | `0x3F` | low_limit, test, high_limit | Confirmed |
| `IIM` | `0x5D` | slot, mask, length | Confirmed |
| `IOM` | `0x5E` | slot, mask, length | Confirmed |
| `ENC` | `0x64` | source, destination | Confirmed |
| `ACI` | `0x7A` | string source, integer destination | Confirmed |
| `ACN` | `0x7B` | source_a, source_b, string destination | Confirmed |
| `AEX` | `0x7D` | source, index, number, destination | Confirmed |
| `AHL` | `0x7E` | channel, masks, control, automatic status/error | Confirmed |
| `AIC` | `0x7F` | integer source, string destination | Confirmed |
| `ARD` | `0x80` | channel, destination, control, length, status | Confirmed |
| `ARL` | `0x81` | channel, destination, control, length, status | Confirmed |
| `ASC` | `0x82` | source, index, string_search, result | Confirmed |
| `ASR` | `0x85` | source_a, source_b | Confirmed |
| `AWA` | `0x83` | channel, source, control, length, status | Confirmed |
| `SQL` | `0x40` | file, source, control, length, position | Confirmed |
| `XIC` | `0x39` | operand | Confirmed |
| `XIO` | `0x3A` | operand | Confirmed |
| `LBL` | `0x3B` | label | Confirmed |
| `SBR` | `0x3D` | none | Confirmed |
| `SQR` | `0x46` | source, destination | Confirmed |
| `REF` | `0x48` | none | Confirmed |
| `INT` | `0x4B` | none | Confirmed |
| `RTO` | `0xA3` | timer, time_base, preset, accumulator | Confirmed |
| `TOF` | `0xA6` | timer, time_base, preset, accumulator | Confirmed |
| `TON` | `0xA7` | timer, time_base, preset, accumulator | Confirmed |
| `UID` | `0xA8` | interrupt_types | Confirmed |
| `UIE` | `0xA9` | interrupt_types | Confirmed |
| `UIF` | `0xAA` | interrupt_types | Confirmed |
| `DLG` | `0xAC` | queue_number | Confirmed |
| `GCD` | `0xAF` | source, destination | Confirmed |
| `RCP` | `0xB0` | file, recipe, operation | Confirmed |
| `LCD` | `0xB2` | six display sources, display_with_input | Confirmed |
| `ABS` | `0x98` | source, destination | Confirmed |
| `ONS` | `0xAB` | storage_bit | Confirmed |
| `OSF` | `0x9D` | storage_bit, output_bit | Confirmed |
| `OSR` | `0x9E` | storage_bit, output_bit | Confirmed |
| `PID` | `0x9F` | pid_file, process_variable, control_variable | Confirmed |
| `PTO` | `0xA0` | pto_number | Confirmed |
| `PWM` | `0xA1` | pwm_number | Confirmed |
| `RAC` | `0xA2` | counter, source | Confirmed |
| `SVC` | `0xA5` | channel_select | Confirmed |
| `MSG` | `0xB3` | msg_file; setup payload unresolved | Confirmed |
| `SCP` | `0x95` | six ordered scaling fields | Confirmed |
| `HSL` | `0x9B` | HSC number and four load sources | Confirmed |
| `SCL` | `0x45` | source, rate, offset, destination | Confirmed |
| `SWP` | `0x96` | file source, literal length | Confirmed |
| `COP` | `0x22` | file source, file destination, length | Confirmed |
| `FLL` | `0x21` | scalar source, file destination, length | Confirmed |
| `FFL` | `0x41` | source, FIFO, control, length, position | Confirmed |
| `FFU` | `0x42` | FIFO, destination, control, length, position | Confirmed |
| `LFL` | `0x43` | source, LIFO, control, length, position | Confirmed |
| `LFU` | `0x44` | LIFO, destination, control, length, position | Confirmed |

Confirmed total: **90**.

## Normalized palette entries

| Palette entry | Serialized evidence | Status |
| --- | --- | --- |
| `AWT` | Byte-identical to confirmed AWA selector `0x83` record | Normalized |

## Unavailable instruction records

| Instruction | Observed constraint | Status |
| --- | --- | --- |
| `DDV` | Greyed out for MicroLogix 1100 Series B | Unavailable |
| `DEG` | Greyed out for MicroLogix 1100 Series B | Unavailable |
| `RAD` | Greyed out for MicroLogix 1100 Series B | Unavailable |
| `ACS` | Trigonometric instruction greyed out | Unavailable |
| `ASN` | Trigonometric instruction greyed out | Unavailable |
| `ATN` | Trigonometric instruction greyed out | Unavailable |
| `COS` | Trigonometric instruction greyed out | Unavailable |
| `SIN` | Trigonometric instruction greyed out | Unavailable |
| `TAN` | Trigonometric instruction greyed out | Unavailable |
| `LN` | Mathematical instruction greyed out | Unavailable |
| `LOG` | Mathematical instruction greyed out | Unavailable |
| `XPY` | Arithmetic instruction greyed out | Unavailable |
| `RMP` | Greyed out for MicroLogix 1100 Series B | Unavailable |
| `EEM` | Greyed out for MicroLogix 1100 Series B | Unavailable |
| `HSC` | Greyed out for MicroLogix 1100 Series B | Unavailable |
| `HSE` | Greyed out for MicroLogix 1100 Series B | Unavailable |
| `HSD` | Greyed out for MicroLogix 1100 Series B | Unavailable |
| `IIE` | Greyed out for MicroLogix 1100 Series B | Unavailable |
| `IID` | Greyed out for MicroLogix 1100 Series B | Unavailable |
| `CEM` | Greyed out for MicroLogix 1100 Series B | Unavailable |
| `DDT` | Greyed out for MicroLogix 1100 Series B | Unavailable |
| `DEM` | Greyed out for MicroLogix 1100 Series B | Unavailable |
| `RHC` | Greyed out for MicroLogix 1100 Series B | Unavailable |
| `RPI` | Greyed out for MicroLogix 1100 Series B | Unavailable |
| `STD` | Greyed out for MicroLogix 1100 Series B | Unavailable |
| `STE` | Greyed out for MicroLogix 1100 Series B | Unavailable |
| `END` | Automatic ladder-file marker; not selectable in palette | Structural |

## Candidate backlog

These mnemonic labels were transcribed from the observed instruction palette.
They remain untested unless they appear in the confirmed table. Palette state,
processor support, and operand availability must be recorded while each
fixture is created.

- Recipe, event, and specialised: `RTA`, `SOR`, `STS`.

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

The next planned fixture candidate is `AIC`. Its availability and operand
fields must first be confirmed in the selected processor's instruction
palette before assigning a filename.
