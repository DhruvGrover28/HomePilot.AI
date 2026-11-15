import os
import pytest

# Default unit/integration test suite to fast local test SQLite to avoid network latency over WAN
# Neon PostgreSQL connectivity and CRUD are verified via integration tests
if not os.environ.get("RUN_ON_NEON"):
    os.environ["DATABASE_URL"] = "sqlite:///./test_homepilot.db"
