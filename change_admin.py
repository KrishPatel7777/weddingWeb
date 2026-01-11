from pymongo import MongoClient
from werkzeug.security import generate_password_hash
import os

MONGO_URI = "mongodb+srv://parampara_admin:ParamparaRiser123@parampara-cluster.ho0inu5.mongodb.net/parampara_db?retryWrites=true&w=majority"
client = MongoClient(MONGO_URI)
db = client['parampara_db']
admins = db['admins']

NEW_USERNAME = "Parampara_panel"
NEW_PASSWORD = "Parampara@2022"

admins.update_one(
    {},
    {
        "$set": {
            "username": NEW_USERNAME,
            "password": generate_password_hash(NEW_PASSWORD)
        }
    }
)

print("Admin username & password updated successfully")