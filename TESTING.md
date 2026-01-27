# Test Suite Documentation

This document describes the comprehensive test suite for the Contacts project.

## Overview

The test suite includes 52 unit tests covering all major components:
- **Data Models** (25 tests): Validation logic for Contact model
- **API Endpoints** (22 tests): All FastAPI routes and error handling
- **Database Connection** (5 tests): MongoDB connection and configuration

## Test Files

### test_datamodels.py
Tests for the Pydantic Contact model validation:
- Required field validation (first name, last name)
- Name validation (letters, spaces, hyphens, apostrophes only)
- Email validation (must contain @ and .)
- Phone number validation (digits, spaces, hyphens, parentheses only)
- Field trimming and filtering
- Edge cases (empty strings, whitespace, special characters)

### test_api.py
Tests for FastAPI endpoints:
- `GET /` - Serves index.html
- `GET /users/` - Retrieves all users
- `GET /users/names` - Retrieves sorted user names
- `POST /contacts` - Creates new contact
- `GET /contacts/search` - Searches contacts by name
- `PUT /contacts/{id}` - Updates existing contact
- `DELETE /contacts/{id}` - Deletes contact
- Background task: Duplicate contact checking

All endpoints tested for:
- Success cases
- Validation errors
- Invalid IDs
- Not found scenarios
- Empty results

### test_connection.py
Tests for database connection logic:
- Successful connection to MongoDB
- Connection failure handling
- Missing environment variables
- MongoDB Atlas SRV URI support
- Environment variable loading

## Running Tests

### Run All Tests
```bash
make test
```
or
```bash
python -m pytest -v
```

### Run Specific Test File
```bash
python -m pytest test_datamodels.py -v
python -m pytest test_api.py -v
python -m pytest test_connection.py -v
```

### Run Specific Test Class
```bash
python -m pytest test_api.py::TestCreateContact -v
python -m pytest test_datamodels.py::TestContactModel -v
```

### Run Specific Test
```bash
python -m pytest test_api.py::TestCreateContact::test_create_contact_success -v
```

### Run with Coverage
```bash
python -m pytest --cov=. --cov-report=html
```

## Test Configuration

### pytest.ini
Configures pytest behavior:
- Test discovery patterns
- Async mode configuration
- Warning filters
- Output formatting

### conftest.py
Provides shared fixtures:
- Event loop for async tests
- Application state reset

## Dependencies

The test suite requires:
- `pytest` - Test framework
- `pytest-asyncio` - Async test support
- `httpx` - HTTP client for FastAPI TestClient
- `unittest.mock` - Mocking support (built-in)

Install with:
```bash
pip install -r requirements.txt
```

## Test Structure

### Fixtures
- `client`: FastAPI TestClient instance
- `mock_collection`: Mocked MongoDB collection
- `setup_mock_db`: Auto-used fixture to inject mock DB

### Mocking Strategy
- MongoDB collections are mocked to avoid requiring a database
- Async operations are properly mocked with AsyncMock
- FastAPI TestClient handles the application lifecycle

### Naming Conventions
- Test files: `test_*.py`
- Test classes: `Test*`
- Test methods: `test_*`

## Coverage

The test suite provides comprehensive coverage:
- **Data validation**: All Pydantic validators
- **API endpoints**: All CRUD operations
- **Error handling**: Validation errors, not found, invalid IDs
- **Edge cases**: Empty data, whitespace, special characters
- **Background tasks**: Duplicate checking logic
- **Database**: Connection, error handling, configuration

## Best Practices

1. **Isolation**: Each test is independent and can run in any order
2. **Mocking**: External dependencies (DB) are mocked
3. **Clarity**: Test names describe what they test
4. **Organization**: Tests grouped by component in classes
5. **Assertions**: Multiple assertions verify expected behavior
6. **Documentation**: Docstrings explain test purpose

## Continuous Integration

To integrate with CI/CD:
```yaml
# Example GitHub Actions
- name: Run tests
  run: |
    pip install -r requirements.txt
    pytest -v --tb=short
```

## Troubleshooting

### Tests fail with "collection not found"
The mock setup in `test_api.py` initializes the collection. Ensure fixtures are properly applied.

### Async tests fail
Ensure `pytest-asyncio` is installed and `pytest.ini` has correct async configuration.

### Import errors
Run tests from the project root directory where all modules are accessible.

## Future Enhancements

Potential test improvements:
- Integration tests with real MongoDB (using testcontainers)
- End-to-end tests for the complete user flow
- Performance tests for large datasets
- Load testing for concurrent requests
- Mutation testing to verify test quality
