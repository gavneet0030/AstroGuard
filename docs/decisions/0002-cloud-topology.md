# ADR 0002: Cloud Topology

Status: Proposed

- Vercel: Next.js frontend.
- Render: FastAPI backend container.
- Managed PostgreSQL: Neon or equivalent.

No cloud resource or billing commitment is created in Phase 1.

Production deployment requires verified CORS, secret management,
database migrations, backups, monitoring and rollback.