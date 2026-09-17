# Administrative StagingArea provisioning

`POST /data/{project}/staging-system-folders` accepts only
`{"stagingAreaIri": "urn:uuid:..."}` and returns `{"ready": true}`.

Use this after creating an area, or when saving an existing area to complete
interrupted setup. Project `ADMIN_RESOURCES` or system `ADMIN_OLDAP` is required
and checked against the administrative graph inside the transaction. Organisation
role membership is not required. This operation neither assigns roles nor adds
administrator/public folder ACLs, and returns no private folder data.

The server discovers reserved folders directly in the project's data graph.
Visibility-filtered resource searches are unsuitable: an empty result does not
prove that a private folder is absent. The existing staging mutation lock and
resource transaction cover discovery, insertion, audit and verification. Only
missing `top`, `top/Trash`, and `top/Mobile` are inserted. Existing folders and
permissions remain unchanged; ambiguous/misplaced topology is rejected.

This narrow administrative command writes the fixed Shared folder shape directly,
with creator/modification metadata and structural audit records. Ordinary resource
creation traverses parent resources through permission-filtered reads, which cannot
serve an administrator without private membership. No general read/permission
bypass is introduced. New top/Trash ACLs use the area's stored default role with
DATA_DELETE; Mobile uses DATA_VIEW, matching the established workspace contract.
The area itself is created in a separate request; failed provisioning is safely
resumable by saving that same area again. A lost success response is also safe to retry.

Deploy the API before the frontend that uses this endpoint. No ontology migration,
oldaplib release, or CaptureApp contract change is required. Workspace member
folder loading and existing generic folder endpoints retain their contracts.
