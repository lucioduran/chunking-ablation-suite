# Contributing

Use Python 3.11. Install `requirements-dev.txt`, run Ruff checks and formatting,
Mypy, unittest under coverage, and both saved-report replay commands from the
README. Keep code comments sparse and explain design decisions in `docs/`.

Add meaningful regression tests for changed behavior. New experiments must keep
source and query splits separate, freeze settings before evaluation, record model
and input hashes, and preserve unfavorable outcomes. Never overwrite published
reports to improve scores. Store new reports under a new versioned directory.

Use focused English commits with no em dash characters. Do not commit model
weights, caches, secrets, virtual environments, or generated build directories.
The reference experiment requires only local hardware and free model downloads.
