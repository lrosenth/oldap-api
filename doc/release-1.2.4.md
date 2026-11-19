# oldap-api 1.2.4: inherited superproperty insertion fix

Requires oldaplib >=1.2.3,<2.0.0. Adding a new property use to an existing class
now preserves its insertion action when adopting already-defined superproperties.
This fixes the TGB import failure on schema:name without requiring its existing
rdfs:label parent to be repeated in the input. Shared hierarchy declarations
remain unchanged; subsequent local property edits still persist normally.

No HTTP/YAML contract change or data migration. The existing set-valued Python
superproperty contract remains in effect. Versioned images will include the fixed
library; existing pinned installations change only through explicit deployment.

Isolated source acceptance: 36 focused API regressions and OpenAPI validation
pass using the fixed library source with network sockets blocked. Image acceptance
and publication are separate release gates.
