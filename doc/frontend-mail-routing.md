# Trusted frontend mail routing


`templates/frontends.json.j2` serializes `oldap_frontends` to a read-only API mount.
Each ID defines `origin`, `display_name`, and all three `routes`:
`password_reset`, `import_status` (`{import_id}`), `export_status` (`{export_id}`).
Optional `origins` lists exact browser origins that select this canonical target;
without it, `origin` is the sole selector. Production targets require HTTPS.

The API uses the browser Origin; no URL or new JSON field is accepted from clients.
Origin is routing metadata, not authentication. Unknown origins fail before creating
jobs/reset tokens when the registry is enabled. Requests without Origin and legacy
jobs retain the existing OLDAP_PUBLIC_APP_URL / OLDAP_PASSWORD_RESET_FRONTEND_URL
fallbacks. A stored ID missing from the registry fails closed at delivery.

Existing client request and public response schemas remain unchanged. Jobs persist
only an internal frontend ID in the existing durable JSON payload; project RDF
schemas and worker HTTP contracts do not change. The registry controls destinations,
not project permissions. SALSAH is a generic frontend for authorized project members.


Deployment orchestration is documented in sibling oldap-setup/docs/salsah-deployment.md.

Example JSON (the environment variable names the server-side file):

```json
{
  "salsah": {
    "origin": "https://salsah.org",
    "display_name": "SALSAH",
    "routes": {
      "password_reset": "/password-reset",
      "import_status": "/imports/{import_id}",
      "export_status": "/exports/{export_id}"
    }
  }
}
```

Configure every participating browser origin before enabling the file. Exact
aliases can be supplied as `origins: ["https://alias.example", "https://canonical.example"]`.
Destinations cannot contain credentials, queries, fragments, backslashes or a base
path. Routes must be local absolute paths with only the documented placeholders.
Unknown keys, missing route types, overlapping origins and invalid files fail closed.
Do not use `Origin` as proof of identity: non-browser clients can forge it, but can
only select server-approved destinations. Normal job ownership remains mandatory.
