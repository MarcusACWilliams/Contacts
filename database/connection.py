import pymongo

def get_database():
    URI = "mongodb+srv://marcusacwilliams:WorkhardBenice2024$$@vitalcluster.elzgb.mongodb.net/?retryWrites=true&w=majority&appName=VitalCluster"
    client = pymongo.MongoClient(URI)
    try:
        # Connect the client to the server
        client.admin.command("ping")
        # Send a ping to confirm a successful connection
        print("Pinged your deployment. You successfully connected to MongoDB!")
    except Exception as err:
        print(err)
    return client

# This is added so that many files can reuse the function get_database()
if __name__ == "__main__":
    contactDatabase = get_database()
