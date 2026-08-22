# RSS instruction-decoding research

## Purpose

This note records the available documentation, current findings, and required
procedure for correlating binary records in an RSLogix 500 `.RSS` project with
ladder instructions such as `XIC`, `XIO`, `OTE`, `MOV`, and `TON`.

The objective is an evidence-backed instruction catalogue. It is not acceptable
to identify an opcode from appearance, frequency, byte position, or a single
project. Unknown bytes and records must remain preserved as unknown evidence.

## Current conclusion

No public Rockwell specification for the serialized instruction records inside
an `.RSS` file was found. Available documentation covers three related but
distinct layers:

1. Microsoft documents the OLE Compound File Binary container used to hold
   application-specific streams.
2. Rockwell documents the RSLogix 500 instruction set, operand forms, data-file
   addressing, and execution semantics.
3. Independent academic research documents a reverse-engineered binary ladder
   representation transferred between RSLogix 500 and a MicroLogix controller.

These sources are valuable, but none currently proves the mapping of a
particular RSS `CIns` record to a particular mnemonic.

## Authoritative documentation

### OLE compound-file container

Microsoft's [Compound File Binary File Format specification][ms-cfb] describes
the file-system-like container of storages and streams. It explains the header,
directory entries, FAT, mini FAT, sectors, and stream allocation.

It does not define the application-specific contents of Rockwell streams such
as `PROGRAM FILES`. Successfully opening the OLE container therefore proves
only that its streams can be located and extracted; it does not decode ladder
logic.

### Rockwell instruction semantics

Rockwell's [SLC 500 Instruction Set Reference Manual][slc-reference] is the
authoritative catalogue for instruction names, supported controllers, operand
forms, addressing, status behavior, and execution semantics. It should supply
the semantic definition after a binary instruction identity has been proven.

It does not document the `.RSS` binary serialization or provide an RSS opcode
table.

Rockwell's [RSLogix 500 release information][rslogix-release] confirms that a
project `.RSS` contains all database and project-related information and may
contain both online and offline project images. This matters when comparing
files: an edit may affect more than one internal representation or leave the
two images temporarily unsynchronized.

## Laddis research findings

The paper [Denial of Engineering Operations Attacks in Industrial Control
Systems][laddis-paper] describes **Laddis**, a decompiler developed using
RSLogix 500 and a MicroLogix 1400-B. The authors captured binary ladder logic
transferred over the PLC communication path and recovered its structure by
differential analysis.

The paper reports the following properties of that transferred representation:

- Rungs are contiguous.
- A rung starts with two zero bytes, followed by a two-byte rung signature and
  a two-byte rung size.
- Instructions begin at the seventh byte of the rung.
- A typical instruction includes a two-byte opcode, a one-byte data-file
  number, a two-byte word offset, and a two-byte bit address.
- Instruction lengths vary with instruction and operand structure. The paper
  gives `JMP`, `SUB`, and `ASC` as examples with different lengths.
- `END` is an example of an instruction without an operand.
- Branch structure is exceptional and uses distinct binary markers for branch
  start, continuation, and end rather than the typical instruction layout.
- Address reconstruction requires associated configuration data; the ladder
  bytes alone are not always sufficient to recover the displayed word index.
- The authors developed a mapping for 120 instruction types by changing one
  controlled instruction at a time and comparing the resulting binary data.

The paper describes a configuration table containing opcode, instruction size,
and address information, but the complete opcode-to-mnemonic mapping and the
Laddis source code were not found publicly.

### Important applicability boundary

Laddis decoded compiled ladder data uploaded from or downloaded to a
MicroLogix controller over PCCC. This is not proven to be the same
serialization as the `CIns`, `CRung`, and related records observed in an RSS
`PROGRAM FILES` payload.

Consequently, the Laddis structure is a source of testable hypotheses. It must
not be copied into the RSS parser as a claimed file-format specification.

Examples of valid tests inspired by the paper include:

- Does an RSS rung have a stable six-byte header with a declared size?
- Is the changing portion of a single-instruction fixture consistently a
  two-byte field?
- Are file number, word offset, and bit index represented independently?
- Do branch-only changes expose stable start, continuation, and end records?
- Does the RSS payload contain both offline and online forms of the change?

## Required differential procedure

The exact project settings, fixture names, instruction matrix, save discipline,
manifest, and delivery checks are defined in the
[controlled RSS instruction-fixture specification](RSS_CONTROLLED_INSTRUCTION_FIXTURES.md).
The current confirmed set and remaining research queue are maintained in the
[RSLogix 500 instruction coverage register](RSS_INSTRUCTION_COVERAGE.md).
That register also records instructions such as DDV, DEG, RAD, and the
greyed-out trigonometric family that are unavailable for the selected processor
profile. LN and LOG are also observed unavailable. Recording these constraints
prevents absence from being mistaken for an unknown encoding.
XPY is likewise greyed out for the selected profile.

### 1. Establish tooling and provenance

Use an authorized RSLogix 500 or RSLogix Micro installation that can create and
save `.RSS` projects. Record:

- software product and exact version;
- selected processor family and firmware target;
- fixture creator and date;
- whether the project was offline, uploaded, downloaded, or saved online;
- whether the online and offline images were synchronized;
- source licence and whether the fixture may be published.

Vendor samples and customer programs remain private unless their licence
explicitly permits redistribution. Public regression fixtures should be
independently created and minimal.

### 2. Create a baseline fixture

Create the smallest valid project containing:

- one known processor target;
- one ladder program file;
- one rung;
- one simple instruction with a distinctive operand;
- no unrelated comments, symbols, or optional configuration where avoidable.

Save, close, reopen, and save the project consistently. This reduces changes
caused by editor state or unsynchronized images.

### 3. Create one-variable variants

Copy the baseline and change exactly one property per variant. Recommended
initial matrix:

| Variant | Only intended change |
| --- | --- |
| `xic-a` | `XIC` with operand A |
| `xic-b` | Same `XIC`, operand B |
| `xio-a` | Change only `XIC` to `XIO` |
| `ote-a` | Change only instruction to `OTE` |
| `mov-a` | `MOV` with known source and destination |
| `ton-a` | `TON` with known timer and preset |
| `series-a` | Add a second serial instruction |
| `branch-a` | Put a controlled instruction in a branch |
| `empty-rung` | Valid empty or minimal rung, if supported |

Use distinctive operands whose file, element, and bit components differ. This
helps distinguish instruction identity from operand encoding.

### 4. Extract and validate the same payload layer

For every fixture:

1. Record the whole-file SHA-256.
2. Enumerate OLE storages and streams.
3. Extract the same `PROGRAM FILES` stream.
4. Validate its declared compression envelope and lengths.
5. Decompress it without altering the bytes.
6. Record the payload SHA-256.
7. Locate the same program file and corroborated rung boundary.
8. Retain all unknown bytes before, within, and after the candidate record.

Comparisons must be made at the decompressed application-payload level, not
against raw OLE file offsets alone. OLE sector allocation and compression can
make a small logical edit look like a large raw-file change.

### 5. Perform structured binary differences

For each pair, report:

- common prefix and suffix lengths;
- all changed byte ranges;
- inserted or removed lengths;
- containing program file and rung;
- nearby `CIns`, `CRung`, `CBranchLeg`, or unknown class evidence;
- little-endian integer interpretations where structurally justified;
- decoded operand strings and their offsets;
- hashes of the complete compared regions.

Do not discard unchanged bytes. They may contain record type, length, flags,
class references, or serialization metadata needed to interpret the change.

### 6. Separate identity from operands

An instruction mapping is credible only after two different comparisons:

1. Change the operand while keeping the mnemonic fixed. Candidate opcode bytes
   should remain unchanged while operand-related bytes change.
2. Change the mnemonic while keeping the operand as equivalent as the editor
   permits. Candidate opcode bytes should change while operand-related fields
   remain stable.

Multi-operand instructions require further variants changing one operand at a
time. Constants, indirect addresses, indexed addresses, timer/counter members,
and control structures must be treated as separate operand forms.

### 7. Corroborate using independent evidence

Where possible, retain an RSLogix-generated report showing the exact rung,
mnemonic, and operands for each fixture. The report establishes source intent;
the differential comparison establishes the serialized field.

A mapping should also repeat across:

- more than one rung;
- more than one program file;
- at least two independently saved projects;
- relevant RSLogix 500 versions or processor families when available.

The Laddis findings may corroborate a mapping, but similarity to its reported
PLC bytecode structure is not sufficient on its own.

## Evidence-backed opcode registry

### Confirmed controlled-profile simple-bit selectors

The first controlled RSLogix Micro Starter Lite fixtures used a MicroLogix
1100 Series B project. Each fixture contained one instruction and a direct
`B3` bit operand. After decompression, mnemonic-only comparisons changed one
selector byte while the operand and surrounding record bytes remained fixed.

| Mnemonic | Selector | Controlled operand comparison |
| --- | ---: | --- |
| `MCR` | `0x08` | No operands |
| `RET` | `0x09` | No operands |
| `TND` | `0x0B` | No operands |
| `XIC` | `0x39` | `B3:0/0` |
| `XIO` | `0x3A` | `B3:0/0` |
| `LBL` | `0x3B` | Label `Q2:1` |
| `SBR` | `0x3D` | No operands |
| `OTE` | `0x2F` | `B3:0/1` |
| `OTL` | `0x30` | `B3:0/1` |
| `OTU` | `0x31` | `B3:0/1` |
| `CLR` | `0x14` | Destination `N7:0` |
| `JSR` | `0x15` | Subroutine file `U:3` |
| `JMP` | `0x16` | Label `Q2:1` |
| `MOV` | `0x1C` | Source `N7:0`; destination `N7:1` |
| `NEG` | `0x1E` | Source `N7:0`; destination `N7:1` |
| `SUS` | `0x1F` | Suspend ID `1` |
| `SQR` | `0x46` | Source `N7:0`; destination `N7:1` |
| `ABS` | `0x98` | Source `N7:0`; destination `N7:1` |
| `ONS` | `0xAB` | Storage bit `B3:0/1` |
| `OSR` | `0x9E` | Storage bit `B3:0/1`; output bit `B3:0/2` |
| `PID` | `0x9F` | PID file `PD9:0`; process `N7:0`; control `N7:1` |
| `PTO` | `0xA0` | PTO number `0` |
| `PWM` | `0xA1` | PWM number `0` |
| `SVC` | `0xA5` | Channel select `0000h` |
| `MSG` | `0xB3` | MSG file `MG10:0`; setup payload unresolved |
| `OSF` | `0x9D` | Storage bit `B3:0/1`; output bit `B3:0/2` |
| `NOT` | `0x1B` | Source `N7:0`; destination `N7:1` |
| `AND` | `0x23` | Source A `N7:0`; source B `N7:1`; destination `N7:2` |
| `OR` | `0x24` | Source A `N7:0`; source B `N7:1`; destination `N7:2` |
| `XOR` | `0x25` | Source A `N7:0`; source B `N7:1`; destination `N7:2` |
| `MVM` | `0x26` | Source `N7:0`; mask `00FFh`; destination `N7:1` |
| `ADD` | `0x27` | Source A `N7:0`; source B `N7:1`; destination `N7:2` |
| `SUB` | `0x28` | Source A `N7:0`; source B `N7:1`; destination `N7:2` |
| `MUL` | `0x29` | Source A `N7:0`; source B `N7:1`; destination `N7:2` |
| `DIV` | `0x2A` | Source A `N7:0`; source B `N7:1`; destination `N7:2` |
| `BSR` | `0x2B` | File `#B3:1`; control `R6:0`; bit `B3:0/1`; length `16` |
| `BSL` | `0x2C` | File `#B3:1`; control `R6:0`; bit `B3:0/1`; length `16` |
| `SQO` | `0x2D` | File, mask, destination, control, length, and position |
| `SQC` | `0x2E` | File, mask, source, control, length, and position |
| `SQL` | `0x40` | File, source, control, length, and position |
| `EQU` | `0x32` | Source A `N7:0`; source B `N7:1` |
| `NEQ` | `0x33` | Source A `N7:0`; source B `N7:1` |
| `GRT` | `0x34` | Source A `N7:0`; source B `N7:1` |
| `GEQ` | `0x35` | Source A `N7:0`; source B `N7:1` |
| `LES` | `0x36` | Source A `N7:0`; source B `N7:1` |
| `LEQ` | `0x37` | Source A `N7:0`; source B `N7:1` |
| `MEQ` | `0x38` | Source `N7:0`; mask `N7:1`; compare `N7:2` |
| `LIM` | `0x3F` | Low limit `N7:0`; test `N7:1`; high limit `N7:2` |
| `SCP` | `0x95` | Six scaling fields `N7:0` through `N7:5` |
| `HSL` | `0x9B` | HSC `HSC0`; high/low and output sources `N7:0`-`N7:3` |
| `SCL` | `0x45` | Source, rate, offset, destination `N7:0` through `N7:3` |
| `SWP` | `0x96` | File source `#N7:0`; length `3` |
| `COP` | `0x22` | File source `#N7:0`; destination `#N7:10`; length `3` |
| `FLL` | `0x21` | Source `N7:0`; file destination `#N7:10`; length `3` |
| `FFL` | `0x41` | Source, FIFO, control, length, and position |
| `FFU` | `0x42` | FIFO, destination, control, length, and position |
| `LFL` | `0x43` | Source, LIFO, control, length, and position |
| `LFU` | `0x44` | LIFO, destination, control, length, and position |
| `TOD` | `0x17` | Source `N7:0`; destination `N7:1` |
| `FRD` | `0x18` | Source `N7:0`; destination `N7:1` |
| `TON` | `0xA7` | Timer `T4:0`; time base `1.0`; preset `5`; accumulator `0` |
| `UID` | `0xA8` | Interrupt types `1` |
| `UIE` | `0xA9` | Interrupt types `1` |
| `UIF` | `0xAA` | Interrupt types `1` |
| `RTO` | `0xA3` | Timer `T4:0`; time base `1.0`; preset `5`; accumulator `0` |
| `TOF` | `0xA6` | Timer `T4:0`; time base `1.0`; preset `5`; accumulator `0` |
| `RES` | `0x13` | Timer `T4:0` or counter `C5:0` |
| `CTU` | `0x11` | Counter `C5:0`; preset `3`; accumulator `0` |
| `CTD` | `0x12` | Counter `C5:0`; preset `3`; accumulator `0` |

An operand-only XIC comparison changed `B3:0/0` to `B3:1/2`. Only the two
corresponding ASCII operand digits changed; selector `0x39`, selector offset,
record length, and all observed framing bytes remained fixed. Together with
the XIC-to-XIO mnemonic-only comparison, this satisfies both identity and
operand-separation controls for XIC within the named profile.

A serial-rung fixture containing `XIC B3:0/0` followed by `OTE B3:0/1`
preserved both standalone instruction records unchanged and in source order.
Their selector offsets were 156 and 175, a 19-byte interval. This supports
direct concatenation for these two framed records. An earlier structural byte
changed from `0x03` in each standalone fixture to `0x04` in the serial fixture;
its meaning remains unresolved and it is not exposed as an instruction count.

A three-instruction serial control was then compared with a parallel fixture
containing the same two XIC operands and OTE operand. The parallel payload was
95 bytes longer, introduced the serialized class name `CBranch`, and retained
all three known instruction records. Selector offsets changed from
156/175/194 in series to 199/246/289 in parallel because branch framing occurs
around and between the records.

Swapping only the upper and lower branch operands exchanged the corresponding
operand digits at offsets 196 and 243. All framing bytes, selectors, offsets,
payload lengths, and the OTE record remained unchanged. This confirms that
recognized instruction byte order follows displayed top-to-bottom branch-leg
order for the controlled profile. Full branch-boundary semantics remain
unimplemented; `CBranch` evidence is preserved without inferring a generic
branch graph.

The controlled MOV record stores source before destination. Source-only
(`N7:0` to `N7:2`) and destination-only (`N7:1` to `N7:3`) comparisons changed
only the expected ASCII digit. Selector `0x1C`, selector offset 182, operand
offsets 167 and 174, qualifiers, and all surrounding bytes remained fixed.
MOV is therefore exposed with ordered `source` and `destination` operands under
profile `rslogix-micro-starter-lite/ml1100-series-b/mov/v1`.

The controlled CLR record uses header `02 00` followed by one `01 3F`-qualified
word operand, destination `N7:0`, and selector `0x14`. CLR therefore extends
the qualified-word structural recognizer to a single ordered destination field
under its own evidence profile.

The field-identical MOV and NEG instruction records differ only at their
selectors: MOV uses `0x1C`, while NEG uses `0x1E`. NEG's surrounding file
serialization moves the record from offset 164 to 162, but its isolated
framing and ordered source/destination fields are unchanged. NEG therefore
uses the shared qualified two-word recognizer under its own evidence profile.

The field-identical SQR and MOV instruction records also differ only at their
selectors: SQR uses `0x46`, while MOV uses `0x1C`. SQR therefore uses the same
qualified two-word recognizer and ordered source/destination roles under its
own evidence profile.

The field-identical TOD and FRD instruction records differ only at their
selectors: TOD uses `0x17`, while FRD uses `0x18`. FRD therefore uses the same
qualified two-word recognizer and ordered source/destination roles under its
own evidence profile.

The field-identical ABS and MOV instruction records differ only at their
selectors: ABS uses `0x98`, while MOV uses `0x1C`. ABS therefore uses the same
qualified two-word recognizer and ordered source/destination roles under its
own evidence profile.

The field-identical NOT and MOV instruction records differ only at their
selectors: NOT uses `0x1B`, while MOV uses `0x1C`. NOT therefore uses the same
qualified two-word recognizer and ordered source/destination roles under its
own evidence profile.

The controlled AND instruction record uses the same qualified three-word
framing and ordered source A, source B, and destination roles as ADD. Its
selector is `0x23`; the field-identical ADD record uses `0x27`. AND therefore
uses the shared three-word recognizer under its own evidence profile.

The field-identical AND and OR instruction records differ only at their
selectors: AND uses `0x23`, while OR uses `0x24`. OR therefore uses the same
qualified three-word recognizer and ordered operand roles under its own
evidence profile.

The controlled GRT instruction uses selector `0x34` with the same qualified
two-word comparison framing and `source_a`/`source_b` roles as EQU and NEQ.

The field-identical GRT and GEQ instruction records differ only at their
selectors: GRT uses `0x34`, while GEQ uses `0x35`. Together with EQU, NEQ,
LES, and LEQ, this establishes the contiguous comparison selector family
`0x32` through `0x37` for the controlled profile.

The controlled MEQ instruction uses selector `0x38` and the shared qualified
three-word framing. Its ordered roles are `source`, `mask`, and `compare`, not
the arithmetic source/source/destination roles. The following OTE remains a
separate simple-bit instruction record.

The controlled LIM instruction uses selector `0x3F` and the shared qualified
three-word framing. Its serialized order matches its entry fields: `low_limit`,
`test`, then `high_limit`. The following OTE remains a separate record.

The controlled SCP instruction uses selector `0x95` and extends the shared
qualified-word framing to header `0C 00` with six ordered fields: `input`,
`input_min`, `input_max`, `scaled_min`, `scaled_max`, and `output`. Each field
uses the same length-prefixed `01 3F` qualification observed in shorter word
instructions.

The controlled SCL instruction uses selector `0x45` and extends the shared
qualified-word framing to header `08 00` with four ordered fields: `source`,
`rate`, `offset`, and `destination`.

The controlled SWP instruction uses selector `0x96` and a distinct header
`02 00` record. Its two consecutive length-prefixed fields are file source
`#N7:0` and literal length `3`; they do not carry the `01 3F` qualification
used by ordinary word operands. The leading `#` is preserved because it marks
a file-range source rather than a scalar address.

The controlled COP instruction uses selector `0x22` and generalizes the
unqualified file-operation framing to header `03 00`. Its ordered fields are
file source `#N7:0`, file destination `#N7:10`, and literal length `3`.

The controlled FLL instruction uses selector `0x21` and header `03 00`. It
shares the unqualified three-field file-operation framing with COP, but its
source is scalar `N7:0`; only destination `#N7:10` is a file address. The last
field is literal length `3`.

The controlled FFL instruction uses selector `0x41` and header `05 00`. Its
five unqualified fields are scalar source `N7:0`, FIFO file `#N7:10`, control
address `R6:0`, literal length `3`, and literal position `0`. The recognizer
requires the observed address families for each role.

The controlled FFU instruction uses selector `0x42`, immediately following
FFL `0x41`, and the same header `05 00`. Its fields are FIFO file `#N7:10`,
scalar destination `N7:0`, control `R6:0`, length `3`, and position `0`. This
reverses the first two data-flow roles relative to FFL without changing the
remaining control fields.

The field-identical FFL and LFL instruction records differ only at their
selectors: FFL uses `0x41`, while LFL uses `0x43`. LFL retains the scalar
source, file collection, control, length, and position structure, with the
collection role identified as `lifo`.

The field-identical FFU and LFU instruction records likewise differ only at
their selectors: FFU uses `0x42`, while LFU uses `0x44`. LFU names its file
collection role `lifo` and retains the destination and control-field roles.

The field-identical TOD and MOV instruction records differ only at their
selectors: TOD uses `0x17`, while MOV uses `0x1C`. TOD therefore uses the same
qualified two-word recognizer and ordered source/destination roles under its
own evidence profile.

The controlled LES instruction uses selector `0x36` with the same qualified
two-word comparison framing and `source_a`/`source_b` roles as EQU and NEQ.

The field-identical LES and LEQ instruction records differ only at their
selectors: LES uses `0x36`, while LEQ uses `0x37`. LEQ therefore uses the same
qualified two-word comparison recognizer and operand roles under its own
evidence profile.

The field-identical XOR, AND, and OR records establish an adjacent bitwise
selector family: AND uses `0x23`, OR uses `0x24`, and XOR uses `0x25`. XOR's
surrounding serialization moves its record by one byte, but its isolated
framing and operands are unchanged. XOR therefore uses the shared qualified
three-word recognizer under its own evidence profile.

The controlled MVM instruction uses selector `0x26` and the qualified
three-field frame `06 00`, immediately preceding ADD `0x27`. RSLogix
normalized the entered decimal mask `255` to serialized text `00FFh`; the
evidence model preserves that observed representation as the `mask` operand.

The controlled JMP instruction uses selector `0x16`, header `01 00`, and one
unqualified label operand. RSLogix normalized the entered label number `1` to
`Q2:1`; the recognizer therefore requires the observed `Q`-file address form
and reports it with role `label`.

The controlled LBL record uses the same header and normalized `Q2:1` operand
as JMP, but selector `0x3B`. The two instructions share the label-record
recognizer while retaining separate evidence profiles.

The controlled JSR instruction uses selector `0x15`, header `01 00`, and one
unqualified subroutine-file operand. RSLogix normalized the entered file
number `3` to `U:3`. The shared program-control scanner applies a distinct
`U`-file grammar and `subroutine` role rather than treating it as a jump label.

The controlled SBR instruction is a zero-operand subroutine-entry marker. Its
record uses selector `0x3D`, a zero operand header, and the standard instruction
trailer; no textual operand is present.

The controlled RET instruction uses the same zero-operand frame and standard
trailer as SBR, but selector `0x09`. It is retained as a distinct
subroutine-return profile rather than inferred from SBR's semantics.

The controlled MCR instruction uses the same zero-operand frame with selector
`0x08`. This confirms record identity only: an isolated fixture does not prove
MCR zone pairing, nesting, or execution semantics.

The controlled SUS instruction uses selector `0x1F`, header `01 00`, and one
unqualified decimal identifier. The entered value `1` remained serialized as
`1`; it is reported with role `suspend_id` and an integer-only operand grammar.

The controlled TND instruction uses selector `0x0B` and the shared
zero-operand frame. The evidence confirms its temporary-end identity and lack
of operands, but does not independently prove runtime scan-cycle semantics.

`END` is not a selectable instruction in the observed MicroLogix 1100 Series B
instruction palette. RSLogix displays it automatically after the final rung,
so it is tracked as a ladder-file structural marker rather than assigned a
guessed instruction selector.

The controlled ONS instruction uses selector `0xAB`, header `01 00`, and the
same unqualified `B`-bit framing as XIC, XIO, and output coils. Its operand is
reported as `storage_bit` under a separate profile because its semantic role
is not interchangeable with the generic bit operand role.

The controlled OSR instruction uses selector `0x9E`, header `02 00`, and two
unqualified `B`-bit fields. Their observed order and roles are `storage_bit`
followed by `output_bit`; this two-field record has its own edge-output profile.

The controlled OSF record is field-identical to OSR but uses selector `0x9D`.
It shares the strict two-bit edge-output recognizer while retaining a separate
falling-edge evidence profile.

The controlled UIE instruction uses selector `0xA9`, header `01 00`, and one
unqualified decimal interrupt-type mask. The entered value `1` remained
serialized as `1` and is reported with role `interrupt_types`.

The controlled UID record is field-identical to UIE but uses selector `0xA8`.
It shares the integer-only `interrupt_types` grammar while retaining a separate
interrupt-disable evidence profile.

The controlled UIF record uses selector `0xAA` with the same header, literal
mask, grammar, and operand role. Together the fixtures establish the contiguous
UID/UIE/UIF selector sequence `0xA8`/`0xA9`/`0xAA` without relying on that
sequence to infer any untested instruction.

The controlled BSL instruction uses selector `0x2C`, header `04 00`, and four
unqualified fields ordered `file`, `control`, `bit_address`, and `length`.
RSLogix displays EN and DN status indicators for the instruction, but they are
not additional textual operands in the observed record.

The controlled BSR record is field-identical to BSL but uses selector `0x2B`.
It shares the strict bit-file shift recognizer while retaining a separate
right-shift evidence profile.

The controlled SQC instruction uses selector `0x2E`, header `06 00`, and six
unqualified fields ordered `file`, `mask`, `source`, `control`, `length`, and
`position`. RSLogix normalized mask `255` to serialized text `00FFh`, which is
preserved as observed evidence.

The controlled SQL instruction uses selector `0x40`, header `05 00`, and five
unqualified fields ordered `file`, `source`, `control`, `length`, and
`position`. Its record uses the same strict address-family validation as the
other controlled sequencer records, without inferring any untested selectors.

The controlled SQO instruction uses selector `0x2D`, header `06 00`, and six
unqualified fields ordered `file`, `mask`, `destination`, `control`, `length`,
and `position`. RSLogix normalized the entered mask `255` to `00FFh`. The
destination role is retained distinctly from SQC's source role.

The controlled PID instruction uses selector `0x9F` and a distinct `04 00`
frame containing PID file `PD9:0`, process variable `N7:0`, and control
variable `N7:1`. A trailing `01 3F` qualifier occurs after the three fields,
not after every operand. The PID Setup dialog exposes tuning, scaling, mode,
limit, alarm, and status values, but those values do not appear as printable
operands in the PROGRAM FILES record. Their binary DATA FILES representation
remains separate, unresolved evidence and is not inferred by this recognizer.

The controlled PTO instruction uses selector `0xA0`, header `01 00`, and one
unqualified decimal field. The entered PTO number `0` remained serialized as
`0` and is reported with role `pto_number`; no separate setup dialog appeared
for this fixture.

The field-identical PWM record uses selector `0xA1`, immediately following PTO
`0xA0`, and retains header `01 00` with literal value `0`. Its operand has the
distinct role `pwm_number`; selector adjacency is recorded as evidence but is
not used to infer untested instructions.

The controlled SVC instruction uses selector `0xA5`, header `01 00`, and one
unqualified channel-selection field. Its default is serialized exactly as
`0000h` and is reported with role `channel_select`; the representation is
preserved rather than converted to an integer.

The controlled MSG instruction prefix uses selector `0xB3`, header `04 00`,
and visible message-file operand `MG10:0`. Three `01 3F` markers precede the
selector. Unlike ordinary instructions, the selector is followed by an
extended setup payload in PROGRAM FILES; the controlled default fixture
contains printable `500CPU Read` and `CLIENT` evidence. Those bytes are
preserved in the source payload but are not assigned guessed configuration
roles. Controlled setup-field changes are required before that binary layout
can be decoded.

`RMP` is greyed out in the observed MicroLogix 1100 Series B instruction
palette. No controlled fixture can therefore be created under this processor
profile, and no selector or operand structure is assigned.

`EEM` is likewise greyed out for the controlled MicroLogix 1100 Series B
profile. It remains unavailable rather than being assigned a selector from
documentation or selector adjacency.

`HSC`, `HSE`, and `HSD` are greyed out for the controlled MicroLogix 1100
Series B profile. HSL is separately supported by controlled evidence; no
relationship among their selectors or operand layouts is inferred.

The controlled HSL instruction uses selector `0x9B`, header `05 00`, and five
unqualified fields: HSC number `HSC0`, high preset `N7:0`, low preset `N7:1`,
output-high source `N7:2`, and output-low source `N7:3`. The HSC instance uses
its own grammar rather than being treated as an ordinary word address.

The controlled ADD record uses the same `01 3F`-qualified word operands as
MOV, with three ordered fields: Source A, Source B, and destination. Independent
changes to each field altered only its expected ASCII digit. Selector `0x27`,
selector offset 189, qualifiers, other operands, and framing remained fixed.
MOV and ADD therefore share a qualified-word structural recognizer while
retaining separate evidence profiles.

The field-identical ADD, SUB, MUL, and DIV instruction records differ only at
their selectors: ADD uses `0x27`, SUB uses `0x28`, MUL uses `0x29`, and DIV
uses `0x2A`. DIV's record begins at offset 162 rather than 164 because its
surrounding file serialization differs by two bytes, but the isolated record
has the same framing and fields. All four therefore use the same qualified
three-word recognizer and operand roles under their own evidence profiles.
This adjacency is evidence of a related selector family, but it is not used to
infer untested instructions.

The controlled EQU record uses the shared qualified two-word framing with
selector `0x32`. Unlike MOV-family records, both fields are comparison inputs:
`source_a` and `source_b`; neither is a destination. The following OTE in the
controlled rung remains a separate simple-bit instruction record.

The field-identical EQU and NEQ instruction records differ only at their
selectors: EQU uses `0x32`, while NEQ uses `0x33`. NEQ therefore uses the same
qualified two-word comparison recognizer and operand roles under its own
evidence profile.

The controlled TON record contains four consecutive length-prefixed fields:
timer, time base, preset, and accumulator. Preset-only (`5` to `7`) and
timer-only (`T4:0` to `T4:1`) comparisons changed only the expected ASCII
digit. Selector `0xA7`, selector offset 181, all other fields, and framing
remained fixed. The implemented profile currently requires the observed time
base `1.0` and offline accumulator `0`; other encodings remain uninterpreted
until controlled fixtures establish them.

The field-identical TON and RTO fixtures differ only at selector offset 181:
TON uses `0xA7`, while RTO uses `0xA3`. Both instructions therefore share one
four-field structural recognizer while retaining separate evidence profiles.
The field-identical TOF fixture likewise differs only at that selector offset,
using `0xA6`.

The controlled RES comparison changed only its operand from timer `T4:0` to
counter `C5:0`. Selector `0x13`, selector offset 173, length prefix, and all
framing remained fixed. RES is therefore recognized for these two operand
families under profile
`rslogix-micro-starter-lite/ml1100-series-b/res/v1`.

The controlled CTU record contains three consecutive length-prefixed fields:
counter, preset, and accumulator. Preset-only (`3` to `5`) and counter-only
(`C5:0` to `C5:1`) comparisons changed only the expected ASCII digit.
Selector `0x11`, selector offset 177, all other fields, and framing remained
fixed. The profile requires the observed offline accumulator `0`; other
accumulator encodings remain uninterpreted.

The field-identical CTU and CTD fixtures differ only at selector offset 177:
CTU uses `0x11`, while CTD uses `0x12`. Both instructions therefore share one
three-field structural recognizer while retaining separate evidence profiles.

These are implemented as the profile
`rslogix-micro-starter-lite/ml1100-series-b/simple-bit/v1`. The recognizer
requires the observed length-prefixed `B` bit operand and invariant record
framing; it does not interpret the selector byte in isolation or generalize
the mapping to untested operand families and RSS producers.

The future registry should preserve both conclusions and their proof. Suggested
fields are:

| Field | Meaning |
| --- | --- |
| `record_signature` | Exact bytes or masked structure used for recognition |
| `mnemonic` | Rockwell instruction name, when established |
| `record_length` | Fixed length or documented length rule |
| `operand_schema` | Ordered fields and addressing forms |
| `processor_family` | Processor targets on which the mapping was observed |
| `software_versions` | RSLogix versions used to create fixtures |
| `confidence` | `confirmed`, `probable`, or `unknown` |
| `evidence_ids` | Fixture pairs, reports, offsets, and SHA-256 values |
| `source_layer` | `rss-program-files` or `pccc-plc-bytecode` |
| `notes` | Exceptions, branches, flags, or unresolved bytes |

Confidence meanings:

- `confirmed`: controlled mnemonic-only and operand-only differences repeat
  across independent fixtures and are corroborated by source reports.
- `probable`: several observations support the mapping, but one required axis
  of controlled or independent evidence is missing.
- `unknown`: preserved binary evidence without a semantic assignment.

The parser must continue to emit unknown records. Registry growth must refine
preserved evidence rather than replace or discard it.

## Acceptance criteria for one instruction

Promote an RSS record to a confirmed mnemonic only when:

- its record boundaries are repeatable and length handling is understood;
- a mnemonic-only change isolates the proposed identity field;
- operand-only changes isolate the proposed operand fields;
- the rule succeeds on multiple rungs and independently saved projects;
- an RSLogix report or equivalent authoritative source confirms source intent;
- processor and software-version applicability are recorded;
- unknown flags and trailing bytes remain preserved;
- malformed and unsupported records fail closed without shifting later record
  boundaries;
- private fixture text is redacted from public evidence.

## Recommended first implementation increment

Start with `XIC`, `XIO`, and `OTE`. They have a simple bit-address operand and
permit strong pairwise comparisons. Then add:

1. branch structure;
2. `MOV`, to establish two-operand records and constants;
3. `TON`, to establish timer addressing and structured instruction data;
4. `ONS`, latches, and unlatches;
5. comparisons and arithmetic;
6. program-control and communication instructions.

Until these gates are satisfied, reports should continue to state that operand
occurrence and rung scope are known while instruction type, execution order,
and runtime semantics remain uninterpreted.

## References

- Rockwell Automation, [SLC 500 Instruction Set Reference Manual,
  publication 1747-RM001G-EN-P][slc-reference].
- Rockwell Automation, [RSLogix 500 release information][rslogix-release].
- Microsoft, [Compound File Binary File Format specification][ms-cfb].
- Senthivel et al., [Denial of Engineering Operations Attacks in Industrial
  Control Systems][laddis-paper], CODASPY 2018.

[laddis-paper]: https://ahmirf.github.io/publications/acm-codaspy-2018.pdf
[ms-cfb]: https://learn.microsoft.com/en-us/openspecs/windows_protocols/ms-cfb/53989ce4-7b05-4f8d-829b-d08d6148375b
[rslogix-release]: https://compatibility.rockwellautomation.com/GeneratedReleaseNote.aspx?o=&pdf=0&v1=54949&v2=54949
[slc-reference]: https://literature.rockwellautomation.com/idc/groups/literature/documents/rm/1747-rm001_-en-p.pdf
