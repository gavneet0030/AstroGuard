# ADR 0001: Language Architecture

Status: Accepted

## Decision

Use Python 3.12 and C++20 as the core implementation languages.

Use TypeScript only for the Next.js web application.

## Rationale

Python provides efficient API, data engineering and ML development.

C++ provides a native environment for performance-sensitive telemetry
processing and systems engineering.

Next.js requires JavaScript or TypeScript for the browser frontend.

## Consequences

The C++ library is initially independently buildable and testable.
Python/C++ bindings will be introduced only when a real integration
requirement is established.