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
| `XIC` | `0x39` | `B3:0/0` |
| `XIO` | `0x3A` | `B3:0/0` |
| `OTE` | `0x2F` | `B3:0/1` |
| `OTL` | `0x30` | `B3:0/1` |
| `OTU` | `0x31` | `B3:0/1` |
| `MOV` | `0x1C` | Source `N7:0`; destination `N7:1` |
| `TON` | `0xA7` | Timer `T4:0`; time base `1.0`; preset `5`; accumulator `0` |
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

The controlled TON record contains four consecutive length-prefixed fields:
timer, time base, preset, and accumulator. Preset-only (`5` to `7`) and
timer-only (`T4:0` to `T4:1`) comparisons changed only the expected ASCII
digit. Selector `0xA7`, selector offset 181, all other fields, and framing
remained fixed. The implemented profile currently requires the observed time
base `1.0` and offline accumulator `0`; other encodings remain uninterpreted
until controlled fixtures establish them.

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
