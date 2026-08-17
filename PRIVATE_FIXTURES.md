# Private fixtures and publication policy

This repository may be used to develop parsers for industrial automation file
formats. Some local inputs were obtained from vendor websites that required an
authenticated account. Authentication does not grant permission to
redistribute those files.

## Files that remain local

Do not commit or publish:

- vendor-supplied project files, examples, drawings, archives, or manuals;
- migrated or re-exported copies of those files;
- CCW projects created by importing vendor-supplied applications;
- reports, screenshots, JSON, CSV, or other extracts derived from private
  source material; or
- customer, site, controller, HMI, or network data.

The `.gitignore` file protects the current private input, experiment, and output
directories. Keep additional private inputs under `private-fixtures/` and their
derived results under `private-outputs/`.

## Files suitable for publication

The following may be committed after review:

- independently written parser and reporting code;
- general documentation that does not reproduce protected content;
- fixtures created entirely from scratch for this project; and
- expected outputs generated exclusively from those synthetic fixtures.

Every published fixture should include a short provenance note stating who
created it, how it was created, and that it contains no vendor or customer
source material. Do not use `git add -f` merely to bypass an ignore rule.

## Local use

Private fixture paths should be supplied to tools at runtime. Tests requiring
those fixtures should skip gracefully when the files are absent. Public CI must
use synthetic fixtures only.

This policy is a conservative project practice, not legal advice. Obtain
permission from the relevant rights holder before publishing material whose
licence or provenance is uncertain.
