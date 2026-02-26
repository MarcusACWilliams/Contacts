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
from dotenv import load_dotenv
import connection
import dataModels
from classes.emails import emailaddress
from classes.messaging import EmailMessenger, SMSMessenger, VoiceCallMessenger, PhoneNumber
import uvicorn
import time
import random
import struct
from datetime import datetime
from pathlib import Path

# Load environment variables from .env file
load_dotenv()

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
BASE_DIR = Path(__file__).resolve().parent
FRONTEND_DIST_INDEX = BASE_DIR / "frontend" / "dist" / "index.html"

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
    global dbClient, user_collection, emails_Collection, messages_collection, email_messenger, sms_messenger, voice_call_messenger
    dbClient = await connection.get_database()
    user_collection = dbClient["users"]
    emails_Collection = dbClient["emails"]
    messages_collection = dbClient["messages"]
    
    # Initialize messaging services
    email_messenger = EmailMessenger()
    sms_messenger = SMSMessenger()
    voice_call_messenger = VoiceCallMessenger()

Contact = dataModels.Contact
EmailAddress = dataModels.EmailAddress
Message = dataModels.Message

@app.get("/")
async def root():
    """Serve React app if built, else fallback to legacy static HTML"""
    if FRONTEND_DIST_INDEX.exists():
        return FileResponse(FRONTEND_DIST_INDEX)
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

# Background task to gather email addresses from contacts and store in separate collection
async def gatherEmailAddresses():
    """Gather all email addresses from a list of contacts"""
    
    """Get the current list of emails"""
    existing_contacts = await user_collection.find({}).to_list(100)
    current_emails = await emails_Collection.find({}).to_list(100)

    # Create a set of existing email addresses for quick lookup
    existing_email_set = set()
    for email_doc in current_emails:
        email = EmailAddress(
            _id=bytes.fromhex(email_doc["_id"]) if "_id" in email_doc else None,
            _contact_id=bytes.fromhex(email_doc["_contact_id"]) if "_contact_id" in email_doc else None,
            address=email_doc.get("address", "").strip(),
            type=email_doc.get("type")
        )
        existing_email_set.add(email.address.strip().lower())

    new_email_docs = []
    for contact in existing_contacts:
        for email_doc in contact.get("emails", []):
                email = EmailAddress(
                    _id=bytes.fromhex(email_doc["_id"]) if "_id" in email_doc else None,
                    _contact_id=bytes.fromhex(email_doc["_contact_id"]) if "_contact_id" in email_doc else None,
                    address=email_doc.get("address", "").strip(),
                    type=email_doc.get("type")
                )
                if email.address.strip().lower() not in existing_email_set:
                    new_email_docs.append(email_doc)
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


# ============= MESSAGE ENDPOINTS =============

@app.post("/messages/email/send")
async def send_email_message(message_data: dict):
    """Send email to a contact"""
    try:
        contact_id = message_data.get("contact_id")
        recipient_email = message_data.get("email")
        subject = message_data.get("subject", "")
        body = message_data.get("body", "")
        is_draft = message_data.get("is_draft", False)
        
        # Validate required fields
        if not contact_id:
            return {"error": "contact_id is required"}
        if not recipient_email:
            return {"error": "email is required"}
        if not body.strip():
            return {"error": "body cannot be empty"}
        
        # Verify contact exists
        contact = await user_collection.find_one({"_id": contact_id})
        if not contact:
            return {"error": "Contact not found"}
        
        # Create message record
        message_id = generate_id()
        message = Message(
            _id=message_id,
            _contact_id=contact_id,
            type="email",
            direction="sent",
            recipient=recipient_email,
            subject=subject,
            body=body,
            status="draft" if is_draft else "sending",
            timestamp=datetime.utcnow()
        )
        
        # Save as draft
        if is_draft:
            message_dict = message.model_dump()
            await messages_collection.insert_one(message_dict)
            return {
                "id": message_id,
                "status": "draft",
                "message": "Email saved as draft"
            }
        
        # Send email
        result = await email_messenger.send_email(
            recipient_email=recipient_email,
            subject=subject,
            body=body,
            contact_id=contact_id
        )
        
        # Update message status based on result
        if result["success"]:
            message.status = "sent"
            message.delivered_at = datetime.utcnow()
            message.metadata = {
                "provider": result.get("provider"),
                "message_id": result.get("message_id")
            }
        else:
            message.status = "failed"
            message.error_message = result.get("error")
        
        # Save message to database
        message_dict = message.model_dump()
        await messages_collection.insert_one(message_dict)
        
        if result["success"]:
            return {
                "id": message_id,
                "status": "sent",
                "message": "Email sent successfully"
            }
        else:
            return {
                "error": f"Failed to send email: {result.get('error')}",
                "message_id": message_id,
                "status": "failed"
            }
    
    except ValidationError as e:
        errors = []
        for error in e.errors():
            field = ".".join(str(x) for x in error["loc"])
            message = error["msg"]
            errors.append({"field": field, "message": message})
        return {"error": "Validation failed", "details": errors}
    except Exception as e:
        return {"error": f"Failed to send email: {str(e)}"}


@app.post("/messages/email/draft")
async def save_email_draft(message_data: dict):
    """Save email as draft"""
    message_data["is_draft"] = True
    return await send_email_message(message_data)


@app.get("/messages/contact/{contact_id}")
async def get_contact_messages(contact_id: str):
    """Get all messages for a contact"""
    try:
        messages = await messages_collection.find(
            {"_contact_id": contact_id}
        ).sort("timestamp", -1).to_list(100)
        
        # Convert datetime to string for JSON serialization
        for msg in messages:
            if msg.get("timestamp"):
                msg["timestamp"] = msg["timestamp"].isoformat()
            if msg.get("delivered_at"):
                msg["delivered_at"] = msg["delivered_at"].isoformat()
        
        return {"messages": messages}
    except Exception as e:
        return {"error": f"Failed to retrieve messages: {str(e)}"}


@app.put("/messages/{message_id}")
async def update_message(message_id: str, message_data: dict):
    """Update a draft message"""
    try:
        # Check if message exists and is a draft
        existing = await messages_collection.find_one({"_id": message_id})
        if not existing:
            return {"error": "Message not found"}
        
        if existing.get("status") != "draft":
            return {"error": "Only draft messages can be updated"}
        
        # Update allowed fields
        update_fields = {}
        if "subject" in message_data:
            update_fields["subject"] = message_data["subject"]
        if "body" in message_data:
            update_fields["body"] = message_data["body"]
        if "recipient" in message_data:
            update_fields["recipient"] = message_data["recipient"]
        
        if update_fields:
            await messages_collection.update_one(
                {"_id": message_id},
                {"$set": update_fields}
            )
        
        return {
            "id": message_id,
            "message": "Draft updated successfully"
        }
    except Exception as e:
        return {"error": f"Failed to update message: {str(e)}"}


@app.delete("/messages/{message_id}")
async def delete_message(message_id: str):
    """Delete a draft message"""
    try:
        # Check if message exists and is a draft
        existing = await messages_collection.find_one({"_id": message_id})
        if not existing:
            return {"error": "Message not found"}
        
        if existing.get("status") != "draft":
            return {"error": "Only draft messages can be deleted"}
        
        result = await messages_collection.delete_one({"_id": message_id})
        
        if result.deleted_count == 0:
            return {"error": "Message not found"}
        
        return {
            "id": message_id,
            "message": "Draft deleted successfully"
        }
    except Exception as e:
        return {"error": f"Failed to delete message: {str(e)}"}


@app.get("/messages/templates")
async def get_email_templates():
    """Get available email templates"""
    return {
        "templates": email_messenger.get_available_templates()
    }


@app.post("/messages/templates/render")
async def render_email_template(template_data: dict):
    """Render an email template with context"""
    try:
        template_name = template_data.get("template_name")
        context = template_data.get("context", {})
        
        if not template_name:
            return {"error": "template_name is required"}
        
        rendered = email_messenger.render_template(template_name, context)
        return {"body": rendered}
    except Exception as e:
        return {"error": f"Failed to render template: {str(e)}"}


# ============= MOBILE MESSAGE ENDPOINTS (SMS & VOICE CALLS) =============

@app.post("/phone/validate")
async def validate_phone(phone_data: dict):
    """Validate a phone number using the PhoneNumber class"""
    try:
        phone = phone_data.get("phone", "").strip()
        if not phone:
            return {"valid": False, "error": "Phone number cannot be empty"}
        
        phone_obj = PhoneNumber(phone)
        return {
            "valid": True,
            "raw": phone_obj.raw,
            "normalized": phone_obj.normalized,
            "e164": phone_obj.e164,
            "call_uri": phone_obj.get_call_uri(),
            "sms_uri": phone_obj.get_sms_uri()
        }
    except ValueError as e:
        return {"valid": False, "error": str(e)}
    except Exception as e:
        return {"valid": False, "error": f"Validation error: {str(e)}"}


@app.post("/messages/sms/mobile-uri")
async def get_sms_mobile_uri(sms_data: dict):
    """Get mobile-compatible SMS URI for a contact"""
    try:
        phone_number = sms_data.get("phone")
        message = sms_data.get("message", "")
        
        if not phone_number:
            return {"error": "phone number is required"}
        
        result = sms_messenger.get_mobile_sms_uri(phone_number, message)
        return result
    except Exception as e:
        return {"error": f"Failed to generate SMS URI: {str(e)}"}


@app.post("/messages/sms/send-native")
async def send_sms_native(sms_data: dict):
    """Get mobile SMS URI without sending (user initiates from mobile device)"""
    try:
        contact_id = sms_data.get("contact_id")
        phone_number = sms_data.get("phone")
        message = sms_data.get("message", "")
        
        if not phone_number:
            return {"error": "phone number is required"}
        
        # Verify contact exists
        if contact_id:
            contact = await user_collection.find_one({"_id": contact_id})
            if not contact:
                return {"error": "Contact not found"}
        
        result = sms_messenger.get_mobile_sms_uri(phone_number, message)
        
        # Log the SMS intent if contact exists
        if result["success"] and contact_id:
            message_id = generate_id()
            message_record = Message(
                _id=message_id,
                _contact_id=contact_id,
                type="sms",
                direction="sent",
                recipient=phone_number,
                body=message,
                status="sending",
                timestamp=datetime.utcnow(),
                metadata={"type": "native_sms", "uri": result["uri"]}
            )
            message_dict = message_record.model_dump()
            await messages_collection.insert_one(message_dict)
            result["message_id"] = message_id
        
        return result
    except Exception as e:
        return {"error": f"Failed to initiate SMS: {str(e)}"}


@app.post("/messages/call/mobile-uri")
async def get_call_mobile_uri(call_data: dict):
    """Get mobile-compatible voice call URI for a contact"""
    try:
        phone_number = call_data.get("phone")
        contact_name = call_data.get("contact_name")
        
        if not phone_number:
            return {"error": "phone number is required"}
        
        result = voice_call_messenger.get_mobile_call_uri(phone_number)
        if contact_name and result["success"]:
            result["contact_name"] = contact_name
        
        return result
    except Exception as e:
        return {"error": f"Failed to generate call URI: {str(e)}"}


@app.post("/messages/call/initiate")
async def initiate_voice_call(call_data: dict):
    """Initiate a voice call to a contact"""
    try:
        contact_id = call_data.get("contact_id")
        phone_number = call_data.get("phone")
        contact_name = call_data.get("contact_name")
        
        if not phone_number:
            return {"error": "phone number is required"}
        
        # Verify contact exists
        if contact_id:
            contact = await user_collection.find_one({"_id": contact_id})
            if not contact:
                return {"error": "Contact not found"}
        
        result = await voice_call_messenger.initiate_call(
            phone_number=phone_number,
            contact_id=contact_id,
            contact_name=contact_name
        )
        
        # Log the call intent if contact exists
        if result["success"] and contact_id:
            message_id = generate_id()
            # Create a message record for call history
            message_record = Message(
                _id=message_id,
                _contact_id=contact_id,
                type="call",  # Note: using "call" as type
                direction="sent",
                recipient=phone_number,
                body=f"Voice call to {contact_name}" if contact_name else "Voice call",
                status="initiated",
                timestamp=datetime.utcnow(),
                metadata={"type": "native_voice_call", "uri": result["mobile_uri"]}
            )
            message_dict = message_record.model_dump()
            # Store in a call history collection or use metadata
            await messages_collection.insert_one(message_dict)
            result["message_id"] = message_id
        
        return result
    except Exception as e:
        return {"error": f"Failed to initiate call: {str(e)}"}


@app.get("/contacts/{contact_id}/mobile-actions")
async def get_contact_mobile_actions(contact_id: str):
    """Get all mobile communication options for a contact (calls, SMS, etc.)"""
    try:
        contact = await user_collection.find_one({"_id": contact_id})
        if not contact:
            return {"error": "Contact not found"}
        
        actions = {
            "contact_id": contact_id,
            "contact_name": f"{contact.get('first', '')} {contact.get('last', '')}".strip(),
            "phone_actions": [],
            "email_actions": []
        }
        
        # Add SMS and call URIs for each phone number
        for phone in contact.get("phone", []):
            try:
                phone_obj = PhoneNumber(phone)
                actions["phone_actions"].append({
                    "phone": phone,
                    "e164": phone_obj.e164,
                    "call_uri": phone_obj.get_call_uri(),
                    "sms_uri": phone_obj.get_sms_uri()
                })
            except ValueError:
                pass
        
        # Add email addresses
        for email in contact.get("emails", []):
            if isinstance(email, dict):
                email_addr = email.get("address")
            else:
                email_addr = str(email)
            if email_addr:
                actions["email_actions"].append({"email": email_addr})
        
        return actions
    except Exception as e:
        return {"error": f"Failed to retrieve contact actions: {str(e)}"}


# Serve React build assets if present
frontend_assets = BASE_DIR / "frontend" / "dist" / "assets"
if frontend_assets.exists():
    app.mount("/assets", StaticFiles(directory=frontend_assets), name="assets")

# Serve static files (HTML, CSS, JS)
app.mount("/static", StaticFiles(directory="static"), name="static")


if __name__ == '__main__':
    uvicorn.run(app, port=8080, host='0.0.0.0')


