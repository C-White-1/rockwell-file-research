# RSS rung-comment research plan

## Status

Implemented from controlled RSLogix Micro Starter Lite fixtures. Rung comments
are decoded from `MEM DATABASE/ObjectData`, independently of printable text in
the ladder payload.

The inventory continues to preserve printable, non-operand PROGRAM FILES
regions as `application_text_candidate` evidence. It labels text as a verified
rung comment only when the separate MEM DATABASE attachment contract matches.

## Confirmed binary contract

`MEM DATABASE/ObjectData` uses the repository's observed 16-byte compressed
section envelope followed by zlib data. In its decompressed payload, a rung
comment record contains:

1. A one-byte comment length.
2. That many printable bytes; multiline text uses CRLF (`0D 0A`).
3. A NUL terminator.
4. The byte `11` (17 decimal), declaring the attachment-key length.
5. An ASCII key `RUNGdddddd-dddddd`.

The first six decimal digits are the RSLogix program-file number and the second
six are the zero-based rung number. Controlled fixtures confirmed short,
multiline, multiple-rung, and multiple-program-file comments. Record order in
MEM DATABASE is not rung order, so exported evidence is sorted after decoding.

RSLogix can alternatively attach a rung comment to an output address. A
controlled `B3:0/1` fixture established the fixed-width key
`B0003:000/01`; observed word addresses use forms such as `N0007:035` and
`F0008:055`. The decoder preserves the encoded key and emits a normalized
address such as `B3:0/1`, `N7:35`, or `F8:55`.

Comments shorter than 255 bytes use a one-byte length. A controlled
300-character comment confirmed that longer text uses `FF` followed by an
unsigned 16-bit little-endian length (`FF 2C 01` for 300). The two bytes before
either length form are zero; earlier record-identity bytes vary and are not
interpreted.

The fixture filename prefix is unrelated to the internal program-file number;
the encoded attachment key and RSLogix **File/Rung** comment fields are
authoritative.

Controlled File 2/File 3 testing also showed that MEM DATABASE can retain an
attachment for a program file that is no longer present in the decoded PROGRAM
FILES section. The inventory preserves such evidence but sets
`program_rung_corroborated` to `false`. Consumers must not treat an
uncorroborated attachment as proof that the referenced rung currently exists.

## Why stronger evidence is required

Observed rung-local strings include several different kinds of content:

- Numeric constants such as `0.01` and `32767.0`.
- Expressions such as `F8:11 + ( F8:11 * 0.1 )`.
- Message configuration such as `!06 Write Single Register (4xxxxx)`.
- Labels such as `Setup Screen`.
- Text that may be a genuine rung comment.

Physical location inside a rung therefore proves rung association, but does not
by itself prove the semantic purpose of a string.

## Preferred proof method

Create a controlled set of otherwise identical RSS projects:

1. A baseline containing a known rung with no comment.
2. A copy in which only that rung's comment is changed to a distinctive value,
   such as `TwinForge_RungComment_001`.
3. A copy in which only an instruction constant or expression is changed.
4. Additional copies containing short, long, empty, and multiline comments.

Compare the decompressed `PROGRAM FILES` payloads and establish that:

- The distinctive comment appears within the expected validated rung range.
- It is enclosed by a repeatable binary field structure.
- Changing the comment changes that field and any associated length metadata.
- Changing an instruction expression affects a different structure.
- Empty, short, long, and multiline comments use the same field contract.
- The result repeats across several rungs and more than one RSS project.

The fixture projects and decoded private-text reports must remain private unless
their licensing and provenance explicitly permit publication. Public tests
should use independently created synthetic evidence.

## Alternative corroborating evidence

The controlled experiment may be supplemented by:

- An RSLogix 500 project report that lists rung numbers and comments which
  exactly match strings recovered from the RSS payload.
- Published Rockwell documentation describing the serialized rung-comment
  field.
- An independent RSS parser that identifies the same field structure and can
  be validated against known projects.

A report correlation alone is useful evidence, but a controlled binary
difference remains preferable because it separates comments from expressions,
constants, labels, and message configuration.

## Acceptance criteria

Promote a candidate to `rung_comment` only when all of the following hold:

- Its containing program file and zero-based rung index are corroborated.
- Its byte boundaries and length encoding are repeatable.
- A controlled comment-only change modifies the identified field.
- A controlled non-comment change does not use that field.
- The rule succeeds across multiple comments and rungs.
- Unknown or malformed cases remain preserved without guessed classification.
- Redacted output exposes hashes and structural evidence but no private text.

## Intended classification model

Once sufficient evidence exists, refine `application_text_candidate` without
discarding the original evidence:

```text
application_text_candidate
├── rung_comment
├── expression
├── numeric_literal
├── message_configuration
└── unknown_application_text
```

Each refined record should retain its original offset, length, SHA-256, rung
identity, source classification, and optional private text. Classification
confidence and the evidence method should be explicit.

## Deferred implementation checklist

- Obtain suitable RSLogix 500 tooling, reports, or controlled RSS fixtures.
- Record source provenance and publication restrictions.
- Produce comment-only and expression-only fixture variants.
- Compare compressed and decompressed section evidence.
- Document the binary field contract.
- Implement a specification-driven classifier.
- Add synthetic positive, negative, malformed, and redaction tests.
- Validate against both PF4 and PF525 pump-control variants where applicable.
- Update the RSS inventory schema and migration notes.
- Revisit HMI-to-rung reports so verified comments can be displayed safely.
