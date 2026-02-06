import re
from typing import Optional

# This module defines the emailaddress class, which represents an email address and provides methods to access its components.
class emailaddress:
    """
    Represents an email address with parsing and validation capabilities.
    
    Provides methods to access email components (username, domain) and perform
    common validation tasks like domain checks and common domain detection.
    """
    
    # Common email provider domains
    COMMON_PROVIDERS = {
        'gmail.com', 'yahoo.com', 'outlook.com', 'hotmail.com', 
        'aol.com', 'icloud.com', 'mail.com', 'protonmail.com',
        'yandex.com', 'zoho.com', 'mail.ru'
    }
    
    # Email regex pattern (RFC 5322 simplified)
    EMAIL_PATTERN = re.compile(
        r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    )
    
    def __init__(self, address: str):
        """Initialize email address with validation."""
        # Is the string provided null or empty?
        if not address:
            raise ValueError("Email address cannot be empty")
        # Normalize the email address (lowercase and strip whitespace)
        address = address.lower().strip()

        # Validate the email address format using regex
        if not self.EMAIL_PATTERN.match(address):
            raise ValueError(f"Invalid email address format: {address}")
        
        self._address = address
        self._username, self._domain = self._parse_email()

    def __str__(self) -> str:
        """Return the email address as string."""
        return self._address
    
    def __repr__(self) -> str:
        """Return repr of email address."""
        return f"emailaddress('{self._address}')"
    
    def __eq__(self, other) -> bool:
        """Compare email addresses."""
        if isinstance(other, emailaddress):
            return self._address == other._address
        elif isinstance(other, str):
            return self._address == other.lower().strip()
        return False
    
    def __hash__(self) -> int:
        """Make emailaddress hashable for set operations."""
        return hash(self._address)
    
    def _parse_email(self) -> tuple:
        """Parse email into username and domain components."""
        try:
            username, domain = self._address.split("@", 1)  # Use maxsplit to handle edge cases
            if not username or not domain:
                raise ValueError("Invalid email format: empty username or domain")
            return username, domain
        except ValueError:
            raise ValueError(f"Invalid email address format: {self._address}")
    
    @property
    def address(self) -> str:
        """Get the full email address."""
        return self._address
    
    @property
    def username(self) -> str:
        """Get the username (local part) of the email address."""
        return self._username
    
    @property
    def domain(self) -> str:
        """Get the domain part of the email address."""
        return self._domain
    
    @property
    def is_common_provider(self) -> bool:
        """Check if email uses a common email provider."""
        return self._domain in self.COMMON_PROVIDERS
    
    def is_valid(self) -> bool:
        """Validate the email address format."""
        return bool(self.EMAIL_PATTERN.match(self._address))
    
    def get_domain_parts(self) -> dict:
        """Get domain broken down into subdomain and TLD."""
        parts = self._domain.split('.')
        return {
            'full': self._domain,
            'subdomain': '.'.join(parts[:-1]) if len(parts) > 1 else None,
            'tld': parts[-1] if parts else None
        }
    