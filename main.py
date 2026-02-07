#!/usr/bin/env python


from typing import List
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi import BackgroundTasks, Request
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel
from pydantic import ValidationError
from bson.objectid import ObjectId
import connection
import dataModels
from classes.emails import emailaddress
import uvicorn
import time
import random
import struct

# Initialize counter with random 3-byte value (0 to 16777215)
_counter = random.randint(0, 0xFFFFFF)

def generate_id() -> str:
    """
    Generate a 12-byte identifier:
    - First 4 bytes: timestamp (seconds since epoch)
    - Next 5 bytes: random value
    - Last 3 bytes: incremental counter (per process)
    
    Returns hex string representation of the 12-byte ID.
    """
    global _counter
    
    # 4-byte timestamp (seconds since epoch)
    timestamp = int(time.time())
    
    # 5-byte random value
    random_bytes = random.getrandbits(40)  # 40 bits = 5 bytes
    
    # 3-byte counter, wrapping around at 16777216 (2^24)
    counter = _counter
    _counter = (_counter + 1) & 0xFFFFFF
    
    # Pack into 12 bytes: 4-byte timestamp + 5-byte random + 3-byte counter
    # Using big-endian for consistent byte ordering
    id_bytes = struct.pack('>I', timestamp)  # 4 bytes unsigned int
    id_bytes += random_bytes.to_bytes(5, 'big')  # 5 bytes
    id_bytes += counter.to_bytes(3, 'big')  # 3 bytes
    
    # Return as hex string
    return id_bytes.hex()

app = FastAPI()

# Custom exception handler for validation errors
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = []
    for error in exc.errors():
        field = ".".join(str(x) for x in error["loc"][1:])  # Skip 'body' prefix
        message = error["msg"]
        errors.append({"field": field, "message": message})
    
    return JSONResponse(
        status_code=422,
        content={"error": "Validation failed", "details": errors}
    )

# Add CORS middleware to allow AJAX requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

#Establish database connection on startup
@app.on_event("startup")
async def startup():
    global dbClient, user_collection, emails_Collection
    dbClient = await connection.get_database()
    user_collection = dbClient["users"]
    emails_Collection = dbClient["emails"]

Contact = dataModels.Contact
EmailAddress = dataModels.EmailAddress

@app.get("/")
async def root():
    """Serve index.html at root"""
    return FileResponse("static/index.html")

@app.get("/users/")
async def getUsers():
    results = await user_collection.find({}).to_list(100)
    print("Fetched results:")
    # Convert ObjectId to string for JSON serialization
    for doc in results:
        doc["_id"] = str(doc["_id"])
        for email in doc.get("emails", []):
            email["_id"] = str(email["_id"])
            email["_contact_id"] = str(email["_contact_id"])
    return results

@app.get("/users/names")
async def getUserNames():
    """Get all user names from database"""
    results = await user_collection.find({}).to_list(100)
    for doc in results:
        doc["_id"] = str(doc["_id"])
    names = []
    for doc in results:
        first = doc.get("first", "")
        last = doc.get("last", "")
        full_name = f"{first} {last}".strip()
        if full_name:
            names.append(full_name)
    return {"names": sorted(names)}

@app.post("/contacts")
async def createContact(contact: dataModels.Contact, background_tasks: BackgroundTasks):
    """Create a new contact"""
    try:
        """Add unique IDs to contact and email addresses"""
        contact._id = bytes.fromhex(generate_id())
        for email in contact.emails:
            email._id = bytes.fromhex(generate_id())
            email._contact_id = contact._id
        
        """Convert to dict for storage, converting bytes to hex strings"""
        contact_dict = contact.model_dump()
        contact_dict["_id"] = contact._id.hex()
        
        """Convert email objects to dicts with hex strings"""
        emails_list = []
        for email in contact.emails:
            email_dict = {
                "_id": email._id.hex(),
                "_contact_id": email._contact_id.hex(),
                "address": email.address,
                "type": email.type
            }
            emails_list.append(email_dict)
        contact_dict["emails"] = emails_list
        
        """Add contact to database"""
        result = await user_collection.insert_one(contact_dict)
        background_tasks.add_task(gatherEmailAddresses)
        # background_tasks.add_task(checkForDuplicateContact, contact, str(result.inserted_id))
        return {"id": str(result.inserted_id), "message": "Contact created successfully"}
    except ValidationError as e:
        errors = []
        for error in e.errors():
            field = ".".join(str(x) for x in error["loc"])
            message = error["msg"]
            errors.append({"field": field, "message": message})
        return {"error": "Validation failed", "details": errors}
    except Exception as e:
        return {"error": f"Failed to create contact: {str(e)}"}

@app.put("/contacts/{contact_id}")
async def updateContact(contact_id: str, contact: dataModels.Contact, background_tasks: BackgroundTasks):
    """Update an existing contact"""
    """Convert to dict for storage, converting bytes to hex strings"""
    contact_dict = contact.model_dump()
    
    """Convert email objects to dicts with hex strings"""
    emails_list = []
    for email in contact.emails:
        # Handle new emails that don't have _id yet
        email_id = email._id
        if not email_id or email_id == b'':
            email_id = bytes.fromhex(generate_id())
        
        contact_id_val = email._contact_id
        if not contact_id_val or contact_id_val == b'':
            contact_id_val = bytes.fromhex(contact_id) if len(contact_id) == 24 else None
        
        email_dict = {
            "_id": email_id.hex() if isinstance(email_id, bytes) else email_id,
            "_contact_id": contact_id_val.hex() if isinstance(contact_id_val, bytes) else contact_id,
            "address": email.address,
            "type": email.type
        }
        emails_list.append(email_dict)
    contact_dict["emails"] = emails_list
    
    result = await user_collection.update_one(
        {"_id": contact_id},
        {"$set": contact_dict}
    )
    
    if result.matched_count == 0:
        return {"error": "Contact not found"}
           
    background_tasks.add_task(gatherEmailAddresses)
    return {"id": contact_id, "message": "Contact updated successfully"}

@app.get("/contacts/search")
async def searchContacts(query: str = ""):
    """Search contacts by first or last name"""
    if not query:
        results = await user_collection.find({}).to_list(100)
    else:
        results = await user_collection.find({
            "$or": [
                {"first": {"$regex": query, "$options": "i"}},
                {"last": {"$regex": query, "$options": "i"}}
            ]
        }).to_list(100)
    
    for doc in results:
        doc["_id"] = str(doc["_id"])
    
    return results

@app.delete("/contacts/{contact_id}")
async def deleteContact(contact_id: str):
    """Delete a contact by ID"""
    try:
        print(f"Attempting to delete contact with _id: {contact_id}")
        result = await user_collection.delete_one({"_id": contact_id})
        print(f"Delete result - deleted_count: {result.deleted_count}")
        
        if result.deleted_count == 0:
            print(f"Contact not found with _id: {contact_id}")
            return {"error": "Contact not found"}
        
        print(f"Successfully deleted contact with _id: {contact_id}")
        return {"id": contact_id, "message": "Contact deleted successfully"}
    except Exception as e:
        print(f"Error deleting contact: {e}")
        return {"error": str(e)}


async def checkForDuplicateContact(contact: Contact, contact_id: str):
    """Check for duplicate contact based on name and contact details"""
    emails = set()
    phones = set()
    """Check for duplicate contact based on first and last name"""
    existing_contacts = await user_collection.find({
        "first": contact.first,
        "last": contact.last
    }).to_list(100)
    for doc in existing_contacts:
        doc["_id"] = str(doc["_id"])
    #Remove the current contact from the list
    filtered_contacts = filter(lambda cont: cont["_id"] != contact_id, existing_contacts)
    # Check for matching email or phone
    for ex_contact in filtered_contacts:
        for mail in ex_contact.get("email", []):
            emails.add(mail)
        for phone in ex_contact.get("phone", []):
            phones.add(phone)
    if emails.isdisjoint(set(contact.emails)) is False or phones.isdisjoint(set(contact.phone)) is False:
            return True
    return False


# Serve static files (HTML, CSS, JS)
#

async def gatherEmailAddresses():
    """Gather all email addresses from a list of contacts"""
    
    """Get the current list of emails"""
    existing_contacts = await user_collection.find({}).to_list(100)
    current_emails = await emails_Collection.find({}).to_list(100)

    existing_email_set = set()
    for email_doc in current_emails:
        address = email_doc.get("address")
        if address:
            existing_email_set.add(address.strip().lower())

    new_email_docs = []
    for contact in existing_contacts:
        for email in contact.get("emails", []):
            address = email.get("address") if isinstance(email, dict) else None
            if not address:
                continue

            try:
                # Validate and normalize using the EmailAddress data model
                email_model = EmailAddress(address=address.strip())
                normalized = email_model.address.strip().lower()

                if normalized in existing_email_set:
                    continue

                existing_email_set.add(normalized)
                new_email_docs.append({"address": email_model.address.strip()})
            except ValidationError:
                continue

    try:
        if new_email_docs:
            insert_result = await emails_Collection.insert_many(new_email_docs)
            print(f"Inserted {len(insert_result.inserted_ids)} new unique email addresses")
        return {"count": len(new_email_docs), "emails": [doc["address"] for doc in new_email_docs]}
    except Exception as e:
        print("Error gathering email addresses:", str(e))
        return {"error": str(e)}


# Email utility endpoints
@app.post("/emails/validate")
async def validate_email(email: dict):
    """Validate an email address using the emailaddress class"""
    try:
        address = email.get("address", "").strip()
        if not address:
            return {"valid": False, "error": "Email address cannot be empty"}
        
        email_obj = emailaddress(address)
        return {
            "valid": True,
            "address": email_obj.address,
            "username": email_obj.username,
            "domain": email_obj.domain,
            "is_common_provider": email_obj.is_common_provider,
            "domain_parts": email_obj.get_domain_parts()
        }
    except ValueError as e:
        return {"valid": False, "error": str(e)}
    except Exception as e:
        return {"valid": False, "error": f"Validation error: {str(e)}"}


@app.get("/emails/list")
async def list_all_emails():
    """Get all unique email addresses from contacts"""
    try:
        result = await gatherEmailAddresses()
        return result
    except Exception as e:
        return {"error": str(e)}


@app.get("/emails/providers")
async def get_email_providers():
    """Get list of common email providers"""
    return {
        "providers": sorted(list(emailaddress.COMMON_PROVIDERS))
    }


# Serve static files (HTML, CSS, JS)
app.mount("/static", StaticFiles(directory="static"), name="static")


if __name__ == '__main__':
    uvicorn.run(app, port=8080, host='0.0.0.0')


#if __name__ == '__main__':
#    uvicorn.run(app, port=8080, host='0.0.0.0')

