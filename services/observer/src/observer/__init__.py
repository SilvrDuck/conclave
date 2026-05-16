"""Observer — Forum's API + Observation read-model writer + 3 reactors.

Service implementation lands in a follow-up PR. This scaffold gives the
compose stack a working healthcheck endpoint so the platform comes up.
"""

from observer.main import app

__all__ = ["app"]
