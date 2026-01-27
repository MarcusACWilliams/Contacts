"""Unit tests for dataModels.py"""
import pytest
from datetime import datetime
from pydantic import ValidationError
from dataModels import Contact


class TestContactModel:
    """Tests for the Contact Pydantic model"""

    def test_valid_contact_minimal(self):
        """Test creating a contact with only required fields"""
        contact = Contact(first="John", last="Doe")
        assert contact.first == "John"
        assert contact.last == "Doe"
        assert contact.email == []
        assert contact.phone == []
        assert contact.address is None

    def test_valid_contact_full(self):
        """Test creating a contact with all fields"""
        contact = Contact(
            first="Jane",
            last="Smith",
            email=["jane@example.com", "j.smith@work.com"],
            phone=["123-456-7890", "(555) 123-4567"],
            address="123 Main St",
            social_media={"twitter": "@jane", "linkedin": "jane-smith"},
            notes="Important client",
            birthday=datetime(1990, 5, 15)
        )
        assert contact.first == "Jane"
        assert contact.last == "Smith"
        assert len(contact.email) == 2
        assert len(contact.phone) == 2
        assert contact.address == "123 Main St"

    def test_name_trimming(self):
        """Test that names are trimmed of whitespace"""
        contact = Contact(first="  John  ", last="  Doe  ")
        assert contact.first == "John"
        assert contact.last == "Doe"

    def test_name_with_hyphen(self):
        """Test names with hyphens are valid"""
        contact = Contact(first="Mary-Jane", last="Parker-Smith")
        assert contact.first == "Mary-Jane"
        assert contact.last == "Parker-Smith"

    def test_name_with_apostrophe(self):
        """Test names with apostrophes are valid"""
        contact = Contact(first="O'Brien", last="D'Angelo")
        assert contact.first == "O'Brien"
        assert contact.last == "D'Angelo"

    def test_name_with_space(self):
        """Test names with spaces are valid"""
        contact = Contact(first="Mary Jane", last="Van Der Berg")
        assert contact.first == "Mary Jane"
        assert contact.last == "Van Der Berg"

    def test_empty_first_name_fails(self):
        """Test that empty first name raises ValidationError"""
        with pytest.raises(ValidationError) as exc_info:
            Contact(first="", last="Doe")
        errors = exc_info.value.errors()
        assert any("Name cannot be empty" in str(e["ctx"]["error"]) for e in errors)

    def test_empty_last_name_fails(self):
        """Test that empty last name raises ValidationError"""
        with pytest.raises(ValidationError) as exc_info:
            Contact(first="John", last="")
        errors = exc_info.value.errors()
        assert any("Name cannot be empty" in str(e["ctx"]["error"]) for e in errors)

    def test_whitespace_only_name_fails(self):
        """Test that whitespace-only names are rejected"""
        with pytest.raises(ValidationError) as exc_info:
            Contact(first="   ", last="Doe")
        errors = exc_info.value.errors()
        assert any("Name cannot be empty" in str(e["ctx"]["error"]) for e in errors)

    def test_name_with_numbers_fails(self):
        """Test that names with numbers are rejected"""
        with pytest.raises(ValidationError) as exc_info:
            Contact(first="John123", last="Doe")
        errors = exc_info.value.errors()
        assert any("must only contain letters" in str(e["ctx"]["error"]) for e in errors)

    def test_name_with_special_chars_fails(self):
        """Test that names with invalid special characters are rejected"""
        with pytest.raises(ValidationError) as exc_info:
            Contact(first="John@", last="Doe")
        errors = exc_info.value.errors()
        assert any("must only contain letters" in str(e["ctx"]["error"]) for e in errors)

    def test_email_validation_valid(self):
        """Test that valid email formats are accepted"""
        contact = Contact(
            first="John",
            last="Doe",
            email=["john@example.com", "test.user@domain.co.uk"]
        )
        assert len(contact.email) == 2

    def test_email_validation_missing_at(self):
        """Test that emails without @ are rejected"""
        with pytest.raises(ValidationError) as exc_info:
            Contact(first="John", last="Doe", email=["invalidemail.com"])
        errors = exc_info.value.errors()
        assert any("Invalid email address" in str(e["ctx"]["error"]) for e in errors)

    def test_email_validation_missing_dot(self):
        """Test that emails without dot are rejected"""
        with pytest.raises(ValidationError) as exc_info:
            Contact(first="John", last="Doe", email=["invalid@emailcom"])
        errors = exc_info.value.errors()
        assert any("Invalid email address" in str(e["ctx"]["error"]) for e in errors)

    def test_email_trimming(self):
        """Test that email addresses are trimmed"""
        contact = Contact(first="John", last="Doe", email=["  test@example.com  "])
        assert contact.email[0] == "test@example.com"

    def test_empty_email_filtered(self):
        """Test that empty strings in email list are filtered out"""
        contact = Contact(first="John", last="Doe", email=["test@example.com", "", "  "])
        assert len(contact.email) == 1
        assert contact.email[0] == "test@example.com"

    def test_phone_validation_valid(self):
        """Test that valid phone formats are accepted"""
        contact = Contact(
            first="John",
            last="Doe",
            phone=["123-456-7890", "(555) 123-4567", "555 123 4567"]
        )
        assert len(contact.phone) == 3

    def test_phone_validation_with_letters_fails(self):
        """Test that phone numbers with letters are rejected"""
        with pytest.raises(ValidationError) as exc_info:
            Contact(first="John", last="Doe", phone=["123-ABC-7890"])
        errors = exc_info.value.errors()
        assert any("must only contain digits" in str(e["ctx"]["error"]) for e in errors)

    def test_phone_validation_with_invalid_chars_fails(self):
        """Test that phone numbers with invalid characters are rejected"""
        with pytest.raises(ValidationError) as exc_info:
            Contact(first="John", last="Doe", phone=["123@456#7890"])
        errors = exc_info.value.errors()
        assert any("must only contain digits" in str(e["ctx"]["error"]) for e in errors)

    def test_phone_trimming(self):
        """Test that phone numbers are trimmed"""
        contact = Contact(first="John", last="Doe", phone=["  123-456-7890  "])
        assert contact.phone[0] == "123-456-7890"

    def test_empty_phone_filtered(self):
        """Test that empty strings in phone list are filtered out"""
        contact = Contact(first="John", last="Doe", phone=["123-456-7890", "", "  "])
        assert len(contact.phone) == 1
        assert contact.phone[0] == "123-456-7890"

    def test_model_dump(self):
        """Test that model_dump() returns correct dictionary"""
        contact = Contact(
            first="John",
            last="Doe",
            email=["john@example.com"],
            phone=["123-456-7890"]
        )
        data = contact.model_dump()
        assert data["first"] == "John"
        assert data["last"] == "Doe"
        assert data["email"] == ["john@example.com"]
        assert data["phone"] == ["123-456-7890"]
        assert "address" in data
        assert data["address"] is None
