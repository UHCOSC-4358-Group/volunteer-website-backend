# Make fixtures from tests/database available to all tests
pytest_plugins = ["src.tests.database.conftest"]
