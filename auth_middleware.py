from functools import wraps
import os
from dotenv import load_dotenv
import jwt
from flask import request, abort
from flask import current_app
from pymongo import MongoClient
import pymongo
from bson.objectid import ObjectId
#import models
load_dotenv()
mongo_uri = os.getenv("MONGO_URI")
client = MongoClient(mongo_uri)
db = client["RapidPrototype"]
collection = db["backend"]

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if "Authorization" in request.headers:
            token = request.headers["Authorization"].split(" ")[1]
        if not token:
            return {
                "message": "Authentication Token is missing!",
                "data": None,
                "error": "Unauthorized"
            }, 401
        try:
            data=jwt.decode(token, current_app.config["SECRET_KEY"], algorithms=["HS256"])
            print("Hello")
            #print(str(data))
            user_id = data["user_id"]
            current_user=collection.find_one({'_id':ObjectId(user_id)})
            #print(str(current_user))
            if current_user is None:
                return {
                "message": "Invalid Authentication token!",
                "data": None,
                "error": "Unauthorized"
            }, 401
        except Exception as e:
            return {
                "message": "Something went wrong",
                "data": None,
                "error": str(e)
            }, 500

        return f(current_user, *args, **kwargs)

    return decorated