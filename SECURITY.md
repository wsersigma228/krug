# Security and privacy

Krug is a work in progress. Public deployment requires HTTPS, private environment
configuration and your own mail credentials; see docs/development.md.

Report vulnerabilities using this repository's private vulnerability reporting
feature in the Security tab. Do not post credentials or private user data in issues.

The public repository starts from a reviewed source snapshot with a fresh Git
history. Examples and automated checks use synthetic accounts and data. Local
environment files, uploaded media, database dumps and design-tool workspaces are
excluded from Git and the container build context. The source snapshot and commit
metadata were checked before publication; a clean scanner result is not a guarantee
that every possible secret or privacy issue has been detected.

Treat the database, media volume and private environment as one deployment backup.
If a real credential is ever committed, revoke or rotate it before removing it
from Git history.
