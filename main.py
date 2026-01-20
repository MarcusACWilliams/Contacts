#!/usr/bin/env python


from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
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

@app.on_event("startup")
async def startup():
    global dbClient, collection
    dbClient = await connection.get_database()
    collection = dbClient["users"]

Contact = dataModels.Contact

# Define a Pydantic model for Todo items
class TodoItem(BaseModel):
    name: str   
todo_db = []

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
async def createContact(contact: dataModels.Contact):
    """Create a new contact"""
    result = await collection.insert_one(contact.dict())
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

# Serve static files (HTML, CSS, JS)
app.mount("/static", StaticFiles(directory="static"), name="static")

if __name__ == '__main__':
    uvicorn.run(app, port=8080, host='0.0.0.0')
