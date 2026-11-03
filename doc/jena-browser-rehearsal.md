# FasnachtsPage browser rehearsal against Jena (2026-10-31)

The real Fasnacht export and complete migration model were loaded into an owned
Jena dataset with actual isolated Redis. A separate Vite process used only this
API through process environment overrides; no frontend `.env` or running GraphDB
service was changed. Source accounts were not restored.

## Verified in the browser

- Anonymous login succeeds with the public `oldap:Unknown` role.
- Archive overview shows 1,102 public entries: 665 media, 422 objects, 15 events.
- “Weitere Medien” expands the visible list from 48 to 96 records.
- Event title sorting changes from A–Z to Z–A with the expected first entry.
- “Fasnacht 1912” shows exactly “BMG Fasnacht 1912” and “Laterne BMG Stamm 1912”.
- Following the lantern link displays its parent and own child relationship.
- One synthetic private child is denied anonymously (404), appears as a third
  alphabetically sorted child to the audit user, and opens successfully for that
  user. After browser logout, the parent again shows only its two public children.

No frontend runtime fix was required. Evidence: `jena-browser-results.json`;
private screenshots and logs remain in the owned `browser-fasnacht-02` output.

## Fixture correction retained for migration

The exported resources include a `chama:Curator` role, but the instance export
does not include its administrative project namespace registration. Adding that
raw role to the audit actor without registering the namespace produced a token
that the existing QName-based role decoder rejected. The fixture now provisions
the source Chama namespace before issuing new browser tokens. This is not an
authentication format change or full Chama/account restoration. Production
migration must provision namespaces for every retained role before issuing tokens.

The public identity receives only `oldap:Unknown`; it is not given the audit
actor's nine source-role identities. One clearly named private child is added
through the ordinary API for the identity contrast; imported objects/grants stay
unchanged. The original real-export comparison runs before that synthetic insert.

## Reproduction

Run the API rehearsal with `--fasnacht-only --fasnacht-export <native-export>
--browser-preview --java <java> --jar <jar> --output <new-private-directory>`.
It writes `browser-ready.json` with the private API origin and holds owned services
for at most 20 minutes. Creating `browser-stop` in that directory closes them.
The fixture allows credentialed browser requests from `http://127.0.0.1:5179`.

Start FasnachtsPage separately with `PUBLIC_API_URL` and `SERVER_API_URL` set to
the ready API origin and `npm run dev -- --host 127.0.0.1 --port 5179 --strictPort`.
Media/upload origins must point to an isolated media fixture, not a live service.
This run intentionally used an unavailable local media origin because binary
migration was not provisioned. Fixture-only login: actor / owned-fixture-password.
Never use that account or setup outside the disposable target.

## Open acceptance gates

This is metadata/navigation/permission acceptance, not the complete production
application. The initial run had no isolated binary service. A subsequent
[signed-image rehearsal](jena-media-browser.md) verifies actual image display,
zoom and capability enforcement. PDF/other delivery paths remain untested.
Fulltext is not activated by the export runner. Twenty archive units are readable,
but the original export contains zero direct `fasnacht:archiveUnit` assignments,
so assignment UI acceptance needs a representative fixture. Browser denied-detail
wording currently exposes “Request failed with status code 404”; no data leaks,
but the message can be improved separately. Real account provisioning, production
load and administrative assignment workflows remain open.
