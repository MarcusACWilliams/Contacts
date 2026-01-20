#!/usr/bin/env python


from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
import connection
import dataModels
import uvicorn
from pydantic import BaseModel
from typing import List


app = FastAPI()

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

# Serve static files (HTML, CSS, JS)
#app.mount("/", StaticFiles(directory="static", html=True), name="static")

@app.get("/users/")
async def getUsers():
    results = await collection.find({}).to_list(100)
    print("Fetched results:")
    # Convert ObjectId to string for JSON serialization
    for doc in results:
        doc["_id"] = str(doc["_id"])
    return results

@app.get("/add/{num1}/{num2}")
async def add(num1: int, num2: int):
    """Add two numbers together"""

    total = num1 + num2
    return {"total": total}

if __name__ == '__main__':
    uvicorn.run(app, port=8080, host='0.0.0.0')
