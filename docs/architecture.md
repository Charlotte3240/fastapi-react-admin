# UniBiz architecture

## Context

UniBiz begins as a single-company system for 10–50 employees. It deliberately
uses a modular monolith: one deployable API, one worker process and one database.
Module boundaries remain explicit so a future SaaS transition does not require
rewriting business rules.

## Modules

- Identity: bootstrap, authentication, sessions and service accounts
- Organization: departments, positions and users
- Authorization: roles, registered permissions and separate view/edit scopes
- CRM: organization/individual customers, contacts and follow-up history
- Notification: channels, templates and durable delivery jobs
- Integration: API keys, idempotency and external identifiers
- Audit: immutable security and business change records

## Authorization invariants

1. The API is the authority; UI visibility is never treated as enforcement.
2. Permissions from active, non-expired roles are combined by union.
3. View scope and edit scope are evaluated independently.
4. At least one active superuser must always remain.
5. System permission codes are registered by code; administrators select them
   but cannot invent permission codes from the UI.

## Data conventions

- UUID identifiers; timezone-aware timestamps; soft deletion for business data.
- PostgreSQL stores timestamps with timezone and JSONB only for reserved extension data.
- External writes are idempotent on `(source_system, external_id)`.
- Contact details are masked by the API unless the caller has the sensitive-view permission.
- Follow-ups are editable by their author for 24 hours, then corrected by append-only audit actions.

## Deployment

Local development uses PostgreSQL 18 in Docker. Production runs stateless API
and worker containers on Alibaba Cloud ECS in Shanghai, with RDS PostgreSQL 18
available only through the VPC. HTTPS terminates at the public reverse proxy.

