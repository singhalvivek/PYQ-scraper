import os
import json
from pymongo import MongoClient
import certifi
from dotenv import load_dotenv

load_dotenv()

CONNECTION_STRING = os.getenv("CONNECTION_STRING")

def dump_data():
    if not CONNECTION_STRING:
        print("Error: CONNECTION_STRING not found in .env")
        return
        
    print("Connecting to MongoDB Atlas...")
    client = MongoClient(CONNECTION_STRING, tlsCAFile=certifi.where())
    db = client.get_database("StudyNaksha")
    collection = db.get_collection("questions")
    
    print("Fetching questions...")
    # exclude _id because it is an ObjectId and not JSON serializable by default
    questions = list(collection.find({}, {"_id": 0}))
    
    with open("viewer_data.json", "w", encoding="utf-8") as f:
        json.dump(questions, f, ensure_ascii=False, indent=2)
        
    print(f"Successfully dumped {len(questions)} questions to viewer_data.json")

if __name__ == "__main__":
    dump_data()
