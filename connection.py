import asyncio
from pymongo import AsyncMongoClient
import os
from dotenv import load_dotenv

load_dotenv() # Load environment variables from a .env file

async def get_database():
    URI = os.getenv("URI")
    client = AsyncMongoClient(URI)
    try:
        # Connect the client to the server
        await client.admin.command("ping")
        # Send a ping to confirm a successful connection
        print("Pinged your deployment. You successfully connected to MongoDB!")
        db = client["careTeam"]
    except Exception as err:
        print(err)
    return db

# This is added so that many files can reuse the function get_database()
if __name__ == "__main__":
    
    contactDatabase = get_database()
