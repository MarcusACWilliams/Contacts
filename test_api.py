"""Unit tests for FastAPI endpoints in main.py"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock, patch
from bson.objectid import ObjectId
from main import app


@pytest.fixture
def client():
    """Create a test client"""
    return TestClient(app)


@pytest.fixture
def mock_collection():
    """Create a mock MongoDB collection"""
    collection = MagicMock()
    collection.find = MagicMock()
    collection.find_one = AsyncMock()
    collection.insert_one = AsyncMock()
    collection.update_one = AsyncMock()
    collection.delete_one = AsyncMock()
    return collection


@pytest.fixture(autouse=True)
def setup_mock_db(mock_collection):
    """Setup mock database for all tests"""
    # Initialize collection as None first, then patch it
    import main as main_module
    if not hasattr(main_module, 'collection'):
        main_module.collection = None
    
    with patch.object(main_module, "collection", mock_collection):
        yield mock_collection


class TestRootEndpoint:
    """Tests for the root endpoint"""

    def test_root_returns_index_html(self, client):
        """Test that root returns the index.html file"""
        response = client.get("/")
        assert response.status_code == 200
        # Should return HTML content
        assert "text/html" in response.headers.get("content-type", "")


class TestGetUsers:
    """Tests for GET /users/ endpoint"""

    @pytest.mark.asyncio
    async def test_get_users_success(self, client, mock_collection):
        """Test successful retrieval of users"""
        # Mock the database response
        mock_cursor = MagicMock()
        mock_cursor.to_list = AsyncMock(return_value=[
            {"_id": ObjectId("507f1f77bcf86cd799439011"), "first": "John", "last": "Doe"},
            {"_id": ObjectId("507f1f77bcf86cd799439012"), "first": "Jane", "last": "Smith"}
        ])
        mock_collection.find.return_value = mock_cursor

        response = client.get("/users/")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["first"] == "John"
        assert data[1]["first"] == "Jane"
        # Check that ObjectIds are converted to strings
        assert isinstance(data[0]["_id"], str)
        assert isinstance(data[1]["_id"], str)

    @pytest.mark.asyncio
    async def test_get_users_empty(self, client, mock_collection):
        """Test retrieval when no users exist"""
        mock_cursor = MagicMock()
        mock_cursor.to_list = AsyncMock(return_value=[])
        mock_collection.find.return_value = mock_cursor

        response = client.get("/users/")
        assert response.status_code == 200
        assert response.json() == []


class TestGetUserNames:
    """Tests for GET /users/names endpoint"""

    @pytest.mark.asyncio
    async def test_get_user_names_success(self, client, mock_collection):
        """Test successful retrieval of user names"""
        mock_cursor = MagicMock()
        mock_cursor.to_list = AsyncMock(return_value=[
            {"_id": ObjectId("507f1f77bcf86cd799439011"), "first": "John", "last": "Doe"},
            {"_id": ObjectId("507f1f77bcf86cd799439012"), "first": "Alice", "last": "Smith"},
            {"_id": ObjectId("507f1f77bcf86cd799439013"), "first": "Bob", "last": "Jones"}
        ])
        mock_collection.find.return_value = mock_cursor

        response = client.get("/users/names")
        assert response.status_code == 200
        data = response.json()
        assert "names" in data
        # Check that names are sorted
        assert data["names"] == ["Alice Smith", "Bob Jones", "John Doe"]

    @pytest.mark.asyncio
    async def test_get_user_names_empty(self, client, mock_collection):
        """Test retrieval when no users exist"""
        mock_cursor = MagicMock()
        mock_cursor.to_list = AsyncMock(return_value=[])
        mock_collection.find.return_value = mock_cursor

        response = client.get("/users/names")
        assert response.status_code == 200
        data = response.json()
        assert data["names"] == []


class TestCreateContact:
    """Tests for POST /contacts endpoint"""

    @pytest.mark.asyncio
    async def test_create_contact_success(self, client, mock_collection):
        """Test successful contact creation"""
        mock_result = MagicMock()
        mock_result.inserted_id = ObjectId("507f1f77bcf86cd799439011")
        mock_collection.insert_one.return_value = mock_result

        # Mock the find for the background task duplicate check
        mock_cursor = MagicMock()
        mock_cursor.to_list = AsyncMock(return_value=[])
        mock_collection.find.return_value = mock_cursor

        contact_data = {
            "first": "John",
            "last": "Doe",
            "email": ["john@example.com"],
            "phone": ["123-456-7890"]
        }

        response = client.post("/contacts", json=contact_data)
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert "message" in data
        assert data["message"] == "Contact created successfully"
        # Verify insert_one was called
        mock_collection.insert_one.assert_called_once()

    def test_create_contact_invalid_first_name(self, client):
        """Test that invalid first name is rejected"""
        contact_data = {
            "first": "John123",
            "last": "Doe"
        }

        response = client.post("/contacts", json=contact_data)
        assert response.status_code == 422
        data = response.json()
        assert "error" in data
        assert data["error"] == "Validation failed"
        assert "details" in data

    def test_create_contact_empty_first_name(self, client):
        """Test that empty first name is rejected"""
        contact_data = {
            "first": "",
            "last": "Doe"
        }

        response = client.post("/contacts", json=contact_data)
        assert response.status_code == 422
        data = response.json()
        assert "error" in data

    def test_create_contact_invalid_email(self, client):
        """Test that invalid email is rejected"""
        contact_data = {
            "first": "John",
            "last": "Doe",
            "email": ["invalidemail"]
        }

        response = client.post("/contacts", json=contact_data)
        assert response.status_code == 422
        data = response.json()
        assert "error" in data

    def test_create_contact_invalid_phone(self, client):
        """Test that invalid phone is rejected"""
        contact_data = {
            "first": "John",
            "last": "Doe",
            "phone": ["ABC-DEF-GHIJ"]
        }

        response = client.post("/contacts", json=contact_data)
        assert response.status_code == 422
        data = response.json()
        assert "error" in data

    def test_create_contact_missing_required_fields(self, client):
        """Test that missing required fields are rejected"""
        contact_data = {
            "first": "John"
            # Missing 'last' field
        }

        response = client.post("/contacts", json=contact_data)
        assert response.status_code == 422


class TestSearchContacts:
    """Tests for GET /contacts/search endpoint"""

    @pytest.mark.asyncio
    async def test_search_contacts_no_query(self, client, mock_collection):
        """Test search without query returns all contacts"""
        mock_cursor = MagicMock()
        mock_cursor.to_list = AsyncMock(return_value=[
            {"_id": ObjectId("507f1f77bcf86cd799439011"), "first": "John", "last": "Doe"},
            {"_id": ObjectId("507f1f77bcf86cd799439012"), "first": "Jane", "last": "Smith"}
        ])
        mock_collection.find.return_value = mock_cursor

        response = client.get("/contacts/search")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2

    @pytest.mark.asyncio
    async def test_search_contacts_with_query(self, client, mock_collection):
        """Test search with query filters results"""
        mock_cursor = MagicMock()
        mock_cursor.to_list = AsyncMock(return_value=[
            {"_id": ObjectId("507f1f77bcf86cd799439011"), "first": "John", "last": "Doe"}
        ])
        mock_collection.find.return_value = mock_cursor

        response = client.get("/contacts/search?query=John")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["first"] == "John"

    @pytest.mark.asyncio
    async def test_search_contacts_empty_result(self, client, mock_collection):
        """Test search returns empty array when no matches"""
        mock_cursor = MagicMock()
        mock_cursor.to_list = AsyncMock(return_value=[])
        mock_collection.find.return_value = mock_cursor

        response = client.get("/contacts/search?query=NonExistent")
        assert response.status_code == 200
        assert response.json() == []


class TestUpdateContact:
    """Tests for PUT /contacts/{contact_id} endpoint"""

    @pytest.mark.asyncio
    async def test_update_contact_success(self, client, mock_collection):
        """Test successful contact update"""
        mock_result = MagicMock()
        mock_result.matched_count = 1
        mock_collection.update_one.return_value = mock_result

        contact_id = "507f1f77bcf86cd799439011"
        contact_data = {
            "first": "John",
            "last": "Updated",
            "email": ["john.updated@example.com"]
        }

        response = client.put(f"/contacts/{contact_id}", json=contact_data)
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == contact_id
        assert data["message"] == "Contact updated successfully"

    @pytest.mark.asyncio
    async def test_update_contact_not_found(self, client, mock_collection):
        """Test updating non-existent contact"""
        mock_result = MagicMock()
        mock_result.matched_count = 0
        mock_collection.update_one.return_value = mock_result

        contact_id = "507f1f77bcf86cd799439011"
        contact_data = {
            "first": "John",
            "last": "Doe"
        }

        response = client.put(f"/contacts/{contact_id}", json=contact_data)
        assert response.status_code == 200
        data = response.json()
        assert "error" in data
        assert data["error"] == "Contact not found"

    def test_update_contact_invalid_id(self, client):
        """Test updating with invalid contact ID"""
        contact_data = {
            "first": "John",
            "last": "Doe"
        }

        response = client.put("/contacts/invalid_id", json=contact_data)
        assert response.status_code == 200
        data = response.json()
        assert "error" in data
        assert data["error"] == "Invalid contact ID"

    def test_update_contact_invalid_data(self, client):
        """Test updating with invalid contact data"""
        contact_id = "507f1f77bcf86cd799439011"
        contact_data = {
            "first": "John123",  # Invalid name with numbers
            "last": "Doe"
        }

        response = client.put(f"/contacts/{contact_id}", json=contact_data)
        assert response.status_code == 422


class TestDeleteContact:
    """Tests for DELETE /contacts/{contact_id} endpoint"""

    @pytest.mark.asyncio
    async def test_delete_contact_success(self, client, mock_collection):
        """Test successful contact deletion"""
        mock_result = MagicMock()
        mock_result.deleted_count = 1
        mock_collection.delete_one.return_value = mock_result

        contact_id = "507f1f77bcf86cd799439011"
        response = client.delete(f"/contacts/{contact_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == contact_id
        assert data["message"] == "Contact deleted successfully"

    @pytest.mark.asyncio
    async def test_delete_contact_not_found(self, client, mock_collection):
        """Test deleting non-existent contact"""
        mock_result = MagicMock()
        mock_result.deleted_count = 0
        mock_collection.delete_one.return_value = mock_result

        contact_id = "507f1f77bcf86cd799439011"
        response = client.delete(f"/contacts/{contact_id}")
        assert response.status_code == 200
        data = response.json()
        assert "error" in data
        assert data["error"] == "Contact not found"

    def test_delete_contact_invalid_id(self, client):
        """Test deleting with invalid contact ID"""
        response = client.delete("/contacts/invalid_id")
        assert response.status_code == 200
        data = response.json()
        assert "error" in data
        assert data["error"] == "Invalid contact ID"


class TestCheckForDuplicateContact:
    """Tests for checkForDuplicateContact background task"""

    @pytest.mark.asyncio
    async def test_check_duplicate_no_duplicates(self, mock_collection):
        """Test duplicate check when no duplicates exist"""
        from main import checkForDuplicateContact
        from dataModels import Contact

        mock_cursor = MagicMock()
        mock_cursor.to_list = AsyncMock(return_value=[])
        mock_collection.find.return_value = mock_cursor

        contact = Contact(
            first="John",
            last="Doe",
            email=["john@example.com"],
            phone=["123-456-7890"]
        )

        result = await checkForDuplicateContact(contact, "507f1f77bcf86cd799439011")
        assert result is False

    @pytest.mark.asyncio
    async def test_check_duplicate_with_duplicate_email(self, mock_collection):
        """Test duplicate check when email matches"""
        from main import checkForDuplicateContact
        from dataModels import Contact

        mock_cursor = MagicMock()
        mock_cursor.to_list = AsyncMock(return_value=[
            {
                "_id": ObjectId("507f1f77bcf86cd799439012"),
                "first": "John",
                "last": "Doe",
                "email": ["john@example.com"],
                "phone": []
            }
        ])
        mock_collection.find.return_value = mock_cursor

        contact = Contact(
            first="John",
            last="Doe",
            email=["john@example.com"],
            phone=["123-456-7890"]
        )

        result = await checkForDuplicateContact(contact, "507f1f77bcf86cd799439011")
        assert result is True

    @pytest.mark.asyncio
    async def test_check_duplicate_with_duplicate_phone(self, mock_collection):
        """Test duplicate check when phone matches"""
        from main import checkForDuplicateContact
        from dataModels import Contact

        mock_cursor = MagicMock()
        mock_cursor.to_list = AsyncMock(return_value=[
            {
                "_id": ObjectId("507f1f77bcf86cd799439012"),
                "first": "John",
                "last": "Doe",
                "email": [],
                "phone": ["123-456-7890"]
            }
        ])
        mock_collection.find.return_value = mock_cursor

        contact = Contact(
            first="John",
            last="Doe",
            email=["different@example.com"],
            phone=["123-456-7890"]
        )

        result = await checkForDuplicateContact(contact, "507f1f77bcf86cd799439011")
        assert result is True

    @pytest.mark.asyncio
    async def test_check_duplicate_ignores_same_contact(self, mock_collection):
        """Test duplicate check ignores the same contact ID"""
        from main import checkForDuplicateContact
        from dataModels import Contact

        contact_id = "507f1f77bcf86cd799439011"
        mock_cursor = MagicMock()
        mock_cursor.to_list = AsyncMock(return_value=[
            {
                "_id": ObjectId(contact_id),
                "first": "John",
                "last": "Doe",
                "email": ["john@example.com"],
                "phone": ["123-456-7890"]
            }
        ])
        mock_collection.find.return_value = mock_cursor

        contact = Contact(
            first="John",
            last="Doe",
            email=["john@example.com"],
            phone=["123-456-7890"]
        )

        result = await checkForDuplicateContact(contact, contact_id)
        assert result is False
