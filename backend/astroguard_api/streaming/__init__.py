"""
AstroGuard streaming package.

Submodules are intentionally imported explicitly by consumers.

This package initializer avoids eager imports so that the event,
broker, topic registry, topic administration and producer modules
remain independently importable without package-level circular
dependency or missing-symbol failures.
"""