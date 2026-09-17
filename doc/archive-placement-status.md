# Archive placement summaries

`POST /archive/{project}/placement-status` takes `targets`, a list of 1–500
objects with `iri` and `kind` (`entry` or `media`). It returns `items` with the
original `iri`, `mediaCount`, and `unassignedCount`. Hidden targets are omitted.
The endpoint is authenticated, read-only and sends `Cache-Control: no-store`.

One aggregate query handles each batch, using COUNT(DISTINCT) so multiple role
or class matches do not inflate counts. Entry targets expand through the
server-configured publication `mediaToRootPropertyIri`; media targets refer to
themselves. Configured root/media classes restrict matches. There are no
project-specific namespaces or caller-supplied relation predicates in the service.

Target and media visibility use ordinary role read grants, not an admin bypass.
Placement existence checks all ArchiveUnits in the same project, including
unreadable ones, but never returns hidden unit identifiers or labels. This keeps
readable media in hidden destinations from being offered as unassigned.
Zero counts mean no readable matching media, not proof of global emptiness.

Counts are advisory snapshots. Clients must recheck before writing and retain
server-side mutation validation. The FasnachtsPage uses summaries for card
checkboxes, page/all-result selection and dialog verification. Failures disable
selection and offer a retry; existing assignments are never silently moved.

Deploy this API before the updated frontend. Existing policy configuration is
reused; no ontology migration or oldaplib release is required. SALSAH-2 can use
the same endpoint for its generic content workflows.
