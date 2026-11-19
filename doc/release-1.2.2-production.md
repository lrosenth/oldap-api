# API 1.2.2 production promotion

Production https://api.oldap.org now runs the exact home-accepted 1.2.2 image with oldaplib 1.2.1. API and its identity consumer were replaced alongside the separately authorized FasnachtsPage 0.1.52 promotion. Database and other services were retained; no migration or content writes occurred.

Public/authenticated placement checks match ordinary media counts, including a 255-medium entry. History read returns 200; API health/readiness and frontend browser acceptance pass. See [deployment receipt and rollback](../../oldap-setup/docs/api-1.2.2-fasnacht-0.1.52-production.md). Rollback uses the previous immutable API 1.2.1 selection, preserving database/history contents.
