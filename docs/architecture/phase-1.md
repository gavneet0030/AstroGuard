# AstroGuard Phase 1 Architecture

## Core language responsibilities

Python:
- FastAPI application.
- API and configuration.
- Future pipeline orchestration.
- ML training and inference integration.

C++20:
- Native telemetry validation.
- Performance-sensitive numerical processing.
- Future high-throughput processing components.

TypeScript:
- Frontend browser application only.

## Initial topology

Next.js frontend
       |
       v
FastAPI backend
       |
       v
Python application services
       |
       v
C++20 native processing library

## Initial endpoints

GET /
GET /health
GET /ready
GET /api/v1/system/info

## Deployment target

Frontend: Vercel
Backend: Render
Database: Managed PostgreSQL

No cloud resources are created in Phase 1.