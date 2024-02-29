import datetime
from flask import Flask, request, jsonify, Response
import jwt
from pymongo import MongoClient
from gridfs import GridFS
from dotenv import load_dotenv
import os
import base64
import bcrypt

from auth_middleware import token_required

from bson.objectid import ObjectId

from flask_cors import CORS

from bson.objectid import ObjectId

from auth_middleware import token_required

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)

CORS(app)

SECRET_KEY = os.environ.get('SECRET_KEY') or 'this is a secret'
#print(SECRET_KEY)
app.config['SECRET_KEY'] = SECRET_KEY

# MongoDB URI
mongo_uri = os.getenv("MONGO_URI")


# Connect to the MongoDB server
client = MongoClient(mongo_uri)

# Access the "RapidPrototype" database
db = client["RapidPrototype"]

# Access the "backend" collection within the database
collection = db["backend"]

# Initialize GridFS for file storage
fs = GridFS(db)

@app.route('/saveAI', methods=['POST'])
def ai_todb():
    try:
        file_path = 'pathoverlay.png'
        data = request.json  
        imageID = data.get('imageID')  # Need the original ID 

        if not os.path.exists(file_path):
            return jsonify({"error": "File not found"})

        with open(file_path, 'rb') as image_file:
            # Get ID from the grid
            image_file_id = fs.put(image_file, filename='pathoverlay.png')

            
            result = collection.insert_one({
                'image_file_id': image_file_id,  
                'imageID': imageID  
            })

            
            return jsonify({
                "message": "AI Image uploaded successfully",
                "aiID": str(result.inserted_id),  # MongoDB  ID 
                "image_file_id": str(image_file_id),  # GridFS file ID
                "imageID": imageID
            })

    except Exception as e:
        return jsonify({"error": str(e)})

@app.route('/updateAI/<string:aiID>', methods=['PUT'])
def update_ai(aiID):
    try:
        data = request.json
        result = collection.update_one(
            {"_id": ObjectId(aiID)},
            {"$set": data}  
        )

        if result.modified_count:
            return jsonify({"message": "AI Image metadata updated successfully"})
        else:
            return jsonify({"error": "No update performed"})
    except Exception as e:
        return jsonify({"error": str(e)})






@app.route('/update/<string:image_id>', methods=['PUT'])
def update_image(image_id):
    try:
        
        data = request.json

        
        result = collection.update_one(
            {"_id": ObjectId(image_id), 'ifImage': 'Yes'},
            {"$set": data}
        )

        if result.modified_count > 0:
            return jsonify({"message": "Image updated successfully"})
        else:
            return jsonify({"error": "No update performed"})

    except Exception as e:
        return jsonify({"error": str(e)})


@app.route('/deleteAI/<string:aiID>', methods=['DELETE'])
def delete_aiimage(aiID):
    try:
        document = collection.find_one_and_delete({"_id": ObjectId(aiID)})
        if document:
            fs.delete(document['image_file_id'])  # Delete the image file from GridFS
            return jsonify({"message": "AI Image deleted successfully"})
        else:
            return jsonify({"error": "No update performed"})
    except Exception as e:
        return jsonify({"error": str(e)})



@app.route('/delete/<string:image_id>', methods=['DELETE'])
def delete_image(image_id):
    try:
        
        document = collection.find_one_and_delete({"_id": ObjectId(image_id)})
        if document:
            fs.delete(document['image_file_id'])
            return jsonify({"message": "Image deleted successfully"})
        else:
            return jsonify({"error": "Image not found"})
    except Exception as e:
        return jsonify({"error": str(e)})



@app.route('/image', methods=['POST'])
def insert_img():
    try:
        if 'image' in request.files:
            image = request.files['image']
            name = request.form.get("name", "")  
            description = request.form.get("description", "")  
            user_id = request.form.get("user_id", "")  

           
            if not ObjectId.is_valid(user_id):
                return jsonify({"error": "Invalid user ID format"})

            
            image_path = 'img.jpg'
            image.save(image_path)

            # GridFS file and insert to MongoDB 
            with open(image_path, 'rb') as image_file:
                image_id = fs.put(image_file, filename=image.filename, name=name, description=description)

            
            result = collection.insert_one({
                'image_file_id': image_id,
                'ifImage': 'Yes',
                'name': name,
                'description': description,
                'user_id': user_id  
            })

            
            return jsonify({"message": "Image uploaded successfully", "imageID": str(result.inserted_id)})
        else:
            return jsonify({"error": "No image file provided in the request"})
    except Exception as e:
        return jsonify({"error": str(e)})






@app.route('/aiimages/<string:imageID>', methods=['GET'])
def get_images_by_imageID(imageID):
    try:
        
        metadata_docs = list(collection.find({"imageID": imageID}))
        if not metadata_docs:
            return jsonify({"error": "No images found with the provided imageID"})

        images = []
        for doc in metadata_docs:
            try:
                file_id = doc['image_file_id']
                grid_out = fs.get(file_id)
                image_data = grid_out.read()
                encoded_image = base64.b64encode(image_data).decode('utf-8')
                
                images.append({
                    "aiID": str(doc['_id']),
                    "imageID": doc['imageID'],
                    "aiData": encoded_image,  # Sending the ai image as a base64-encoded string
                    "name": doc.get("name", ""),
                    "description": doc.get("description", "")
                })
            except Exception as e:
                print(f"Error retrieving file from GridFS: {e}")
                

        return jsonify({
            "message": f"Retrieved {len(images)} images successfully",
            "images": images
        })
    except Exception as e:
        return jsonify({"error": str(e)})


@app.route('/images/<string:user_id>', methods=['GET'])
def get_all_images(user_id):
    try:
        image_documents = list(collection.find({"ifImage": "Yes", "user_id": user_id}))
        image_data_list = []

        for doc in image_documents:
            image_file = fs.get(doc['image_file_id'])
            if image_file:
                image_data = image_file.read()
                base64_data = base64.b64encode(image_data).decode('utf-8')
                image_data_list.append({
                    "imageID": str(doc['_id']), 
                    "image_file_id": str(doc['image_file_id']),  
                    "data": base64_data,
                    "name": doc.get("name", ""),
                    "description": doc.get("description", "")
                })

        return jsonify({"images": image_data_list})

    except Exception as e:
        return jsonify({"error": str(e)})

# updates name and password, returns message
# code to update username is commented out
# needs JWT implemented
@app.route('/edituser', methods=['POST'])
@token_required
def edit_user(current_user):
    # user to update
    # format: {"update":username to update, "username": ... "password": new password }
    try:
        data = request.json

       
        result = collection.find_one({"_id": current_user["_id"]})
        if result:
            updates = {}
            if "name" in data:
                updates["name"] = data["name"]
            
            # update username (commented since it should be unique and unchanged)
            #if "username" in data :
            #    dict["username"] = data["username"]

            # Update the password if provided
            if "password" in data:
                # Hash the new password
                hashed_password = bcrypt.hashpw(data['password'].encode('utf-8'), bcrypt.gensalt())
                updates["password"] = hashed_password

           
            if updates:
                collection.update_one({'_id': current_user["_id"]}, {"$set": updates})
                return jsonify({"msg": "User update successful"})
            else:
                return jsonify({"msg": "No updates performed"})

        return jsonify({"msg": "User does not exist"})
    except Exception as e:
        return jsonify({'error': str(e)})

# any param can be passed for delete, returns only message
# recomment deleting by username, since is is unique
# needs JWT implemented
@app.route('/deleteuser', methods=['POST'])
@token_required
def delete_user(current_user):
    try:
       
        result = collection.find_one({"_id":current_user['_id']})
        if result :
            
            collection.delete_one(result)
            
            return jsonify({"msg": "User deleted successfully"})
        
        return jsonify({"msg": "User does not exist"})
    except Exception as e:
        return jsonify({'error': str(e)})

# login by username and password
# Returns user token ad user_id
@app.route('/login', methods=['POST'])
def login():
    try:
        data = request.json

        
        user = collection.find_one({'username': data['username']})

        
        if user:
            
            password_try = data['password'].encode('utf-8')
            
            
            hashed_password = user['password']
            
           
            if bcrypt.checkpw(password_try, hashed_password):
                
                user_token = jwt.encode(
                    {"user_id": str(user["_id"]), "exp" : str(datetime.timedelta(hours=12))},
                    app.config["SECRET_KEY"],
                    algorithm="HS256"
                )
                return jsonify({"user_token": str(user_token), "user_id": str(user['_id']), "msg": "User logged in"}), 200
            else:
                return jsonify({"msg": "Password is incorrect"})
        else:
            return jsonify({"msg": "User not found"})
    except Exception as e:
        return jsonify({'error': str(e)})


# primarily for development
# user can be read by anything, returns all user information
# comment out when deployed
@app.route('/readuser', methods=['GET'])
def read_user() :
    try:
        # params for user
        data = request.json

        result = collection.find_one(data)

        # return all user info
        user = str(result)

        return jsonify({"user": user, "msg": "User loaded successfully"})
    except Exception as e:
        return jsonify({'error': str(e)})

# this is basically just register 
# make sure to pass name, username, and password
# Returns a user token
@app.route('/adduser', methods=['POST'])
def create_user():
    try:
        data = request.json

        # Check if username already exists
        currentusername = collection.find_one({"username": data["username"]})
        if currentusername:
            return jsonify({"msg": "Username already taken"})

       
        hashed_password = bcrypt.hashpw(data['password'].encode('utf-8'), bcrypt.gensalt())

        
        data['password'] = hashed_password

        
        collection.insert_one(data)

        
        user = collection.find_one({"username": data["username"]})

        # Generate token
        user["token"] = jwt.encode(
            {"user_id": str(user["_id"]), "exp" : str(datetime.timedelta(hours=12))},
            app.config["SECRET_KEY"],
            algorithm="HS256"
        )

        
        return jsonify({
            'user_token': str(user['token']), 
            'user_id': str(user['_id']),  
            'msg': 'User added successfully'
        })
    except Exception as e:
        return jsonify({'error': str(e)})


if __name__ == '__main__':
    app.run(debug=True)





