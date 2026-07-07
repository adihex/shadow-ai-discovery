import os
import tempfile

# Point the app at a throwaway database before anything imports app.database,
# so tests never touch the local dev database.db.
os.environ.setdefault(
    "SHADOW_AI_DATABASE_PATH",
    os.path.join(tempfile.mkdtemp(prefix="shadow-ai-test-"), "test.db"),
)
