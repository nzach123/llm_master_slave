# Run tests using the virtual environment's pytest
# Usage: .\run_tests.ps1 [pytest arguments]
# Example: .\run_tests.ps1 -v tests/test_specific.py

.venv\Scripts\pytest.exe $args
