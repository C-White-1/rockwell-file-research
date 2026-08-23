# Security policy

## Supported versions

This is an early research project. Security fixes are applied to the latest
revision on the default branch; older revisions are not maintained separately.

## Reporting a vulnerability

Do not disclose a vulnerability, credential, sensitive industrial endpoint,
or private project data in a public issue.

Use GitHub's **Report a vulnerability** link in the repository Security tab to
submit a private report. If private vulnerability reporting is not available,
open a public issue containing no technical details and ask the maintainer to
provide a private reporting channel.

Include, where safe:

- the affected command or component;
- the security impact;
- minimal reproduction steps using synthetic data;
- the affected revision; and
- any suggested mitigation.

Do not attach customer files, controller projects, packet captures, secrets,
or vendor material to a report. Create a synthetic reproduction or describe
how an authorized maintainer can reproduce the issue locally.

## Operational safety

The project is designed for read-only, authorized analysis. Treat generated
reports as potentially sensitive because they may expose program structure,
addresses, device identities, or network information. Keep private inputs and
derived outputs outside source control and review all exports before sharing.
