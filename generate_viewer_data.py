import os
import json
from pymongo import MongoClient
from bson import ObjectId
import certifi
from dotenv import load_dotenv

load_dotenv()

CONNECTION_STRING = os.getenv("CONNECTION_STRING")

class MongoEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, ObjectId):
            return str(obj)
        return super().default(obj)

def dump_data():
    if not CONNECTION_STRING:
        print("Error: CONNECTION_STRING not found in .env")
        return
        
    print("Connecting to MongoDB Atlas...")
    client = MongoClient(CONNECTION_STRING, tlsCAFile=certifi.where())
    db = client.get_database("StudyNaksha")
    
    # Fetch questions
    questions_collection = db.get_collection("questions")
    print("Fetching questions...")
    questions = list(questions_collection.find({}, {"_id": 0}))
    
    # Convert ObjectId fields to strings
    for q in questions:
        if "comprehensionId" in q and isinstance(q["comprehensionId"], ObjectId):
            q["comprehensionId"] = str(q["comprehensionId"])
    
    # Fetch comprehensions
    comprehensions_collection = db.get_collection("comprehensions")
    print("Fetching comprehensions...")
    comprehensions = list(comprehensions_collection.find({}))
    
    # Build a lookup map: str(ObjectId) -> comprehension doc
    comp_map = {}
    for c in comprehensions:
        comp_map[str(c["_id"])] = {
            "text": c.get("text"),
            "imageUrls": c.get("imageUrls", []),
            "subject": c.get("subject"),
            "topic": c.get("topic")
        }
    
    output = {
        "questions": questions,
        "comprehensions": comp_map
    }
    
    with open("viewer_data.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2, cls=MongoEncoder)
        
    print(f"Successfully dumped {len(questions)} questions and {len(comprehensions)} comprehensions to viewer_data.json")

if __name__ == "__main__":
    dump_data()
