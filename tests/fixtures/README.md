# Synthetic CCW workbook fixture

The CCW workbook used by the automated tests is generated at test time by
`tests/fixture_factory.py`. It is not an export or modified copy of a Rockwell
Automation workbook.

The fixture was authored for this project on 18 August 2026. It contains only
fictional tags, a documentation-only IP address from `192.0.2.0/24`, minimal
Office Open XML package metadata, and the factual cell relationships required
to exercise the parser. It contains no vendor styling, logos, screenshots,
macros, binaries, or customer data.

The private CCW report was consulted only to verify parser interoperability.
It is ignored by Git and is not required to run the public tests.
