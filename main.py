#!/usr/bin/env python


from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi import BackgroundTasks
from bson.objectid import ObjectId
import connection
import dataModels
import uvicorn
from pydantic import BaseModel
from typing import List


app = FastAPI()

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
    global dbClient, collection
    dbClient = await connection.get_database()
    collection = dbClient["users"]

Contact = dataModels.Contact

@app.get("/")
async def root():
    """Serve index.html at root"""
    return FileResponse("static/index.html")

@app.get("/users/")
async def getUsers():
    results = await collection.find({}).to_list(100)
    print("Fetched results:")
    # Convert ObjectId to string for JSON serialization
    for doc in results:
        doc["_id"] = str(doc["_id"])
    return results

@app.get("/users/names")
async def getUserNames():
    """Get all user names from database"""
    results = await collection.find({}).to_list(100)
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
async def createContact(contact: dataModels.Contact , background_tasks: BackgroundTasks):
    """Create a new contact"""
    result = await collection.insert_one(contact.model_dump())
    background_tasks.add_task(checkForDuplicateContact, contact, result.inserted_id)
    return {"id": str(result.inserted_id), "message": "Contact created successfully"}

@app.get("/contacts/search")
async def searchContacts(query: str = ""):
    """Search contacts by first or last name"""
    if not query:
        results = await collection.find({}).to_list(100)
    else:
        results = await collection.find({
            "$or": [
                {"first": {"$regex": query, "$options": "i"}},
                {"last": {"$regex": query, "$options": "i"}}
            ]
        }).to_list(100)
    
    for doc in results:
        doc["_id"] = str(doc["_id"])
    
    return results

@app.put("/contacts/{contact_id}")
async def updateContact(contact_id: str, contact: dataModels.Contact):
    """Update an existing contact"""
    try:
        object_id = ObjectId(contact_id)
    except:
        return {"error": "Invalid contact ID"}
    
    result = await collection.update_one(
        {"_id": object_id},
        {"$set": contact.model_dump()}
    )
    
    if result.matched_count == 0:
        return {"error": "Contact not found"}
    
    return {"id": contact_id, "message": "Contact updated successfully"}



@app.delete("/contacts/{contact_id}")
async def deleteContact(contact_id: str):
    """Delete a contact by ID"""
    try:
        object_id = ObjectId(contact_id)
    except:
        return {"error": "Invalid contact ID"}
    
    result = await collection.delete_one({"_id": object_id})
    
    if result.deleted_count == 0:
        return {"error": "Contact not found"}
    
    return {"id": contact_id, "message": "Contact deleted successfully"}

# Serve static files (HTML, CSS, JS)
app.mount("/static", StaticFiles(directory="static"), name="static")

async def checkForDuplicateContact(contact: Contact, contact_id: str):
    emails = set()
    phones = set()
    """Check for duplicate contact based on first and last name"""
    existing_contacts = await collection.find({
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
    if emails.isdisjoint(set(contact.email)) is False or phones.isdisjoint(set(contact.phone)) is False:
            return True
    return False

if __name__ == '__main__':
    uvicorn.run(app, port=8080, host='0.0.0.0')
