import importlib
import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.database import session


class DatabaseSessionTests(unittest.TestCase):
    def test_falls_back_to_sqlite_when_postgres_is_unavailable(self):
        original_url = os.environ.get("DATABASE_URL")
        os.environ["DATABASE_URL"] = "postgresql://postgres:password@127.0.0.1:1/ao_db"

        try:
            module = importlib.reload(session)
            self.assertEqual(module.engine.url.get_backend_name(), "sqlite")
        finally:
            if original_url is None:
                os.environ.pop("DATABASE_URL", None)
            else:
                os.environ["DATABASE_URL"] = original_url
            importlib.reload(session)


if __name__ == "__main__":
    unittest.main()
