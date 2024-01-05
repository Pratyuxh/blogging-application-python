import os
import certifi
import requests
from flask import Flask, Response, jsonify, request, make_response, render_template, flash, redirect, g, after_this_request
from flask_pymongo import PyMongo
from pymongo import MongoClient
from flask_swagger_ui import get_swaggerui_blueprint
from flask_cors import CORS
from flask_jwt_extended import JWTManager, jwt_required, create_access_token, get_jwt_identity
from bson.json_util import dumps
from bson.objectid import ObjectId
from flask_httpauth import HTTPBasicAuth
from werkzeug.security import generate_password_hash, check_password_hash
from botocore.exceptions import NoCredentialsError
import boto3

app = Flask(__name__)
jwt = JWTManager(app)
cors = CORS(app)
app.config["CORS_HEADERS"] = "Content-Type"

mongo_db_url = os.environ.get("MONGO_DB_CONN_STRING")
client = MongoClient(mongo_db_url)
db = client['blogging']

connection_string = f"mongodb://localhost:27017/blog"
client = MongoClient(connection_string)

app.config['MONGO_URI'] = "mongodb://localhost:27017/blog"
mongo = PyMongo(app)

# Configure SWAGGER
SWAGGER_URL = '/swagger'  
API_URL = '/static/swagger.json'  # Our API url (can of course be a local resource)

swaggerui_blueprint = get_swaggerui_blueprint(
    SWAGGER_URL,  
    API_URL,
    config={ 
        'app_name': "Blogging",
    },
)

app.register_blueprint(swaggerui_blueprint, url_prefix = SWAGGER_URL)

auth = HTTPBasicAuth()

# Configure JWT
app.config['JWT_SECRET_KEY'] = '854d9f0a3a754b16a6e1f3655b3cfbb5'
jwt = JWTManager(app)
app.config['JWT_TOKEN_LOCATION'] = ['headers']
app.config['JWT_BLACKLIST_ENABLED'] = True
app.config['PROPAGATE_EXCEPTIONS'] = True

headers = {
    'Content-Type': 'application/json',
    'Authorization': 'Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJmcmVzaCI6ZmFsc2UsImlhdCI6MTcwMTM2MTQwMCwianRpIjoiZGJlZmY2NzAtM2IzMi00NGQ3LTlkNzItMjY2NjliNjA3OGM0IiwidHlwZSI6ImFjY2VzcyIsInN1YiI6InVzZXIxIiwibmJmIjoxNzAxMzYxNDAwLCJleHAiOjE3MDEzNjIzMDB9.Il6UB4Til2jOXTTaMhaFe0SOlhKmNkBQn6S3bdKzRtE'}

# Mock user data for demonstration
users = {
    'user1': {'password': 'password1'},
    "admin": generate_password_hash("admin"),
}

# Token creation route (login)
@app.route('/login', methods=['GET','POST'])
def login():
    username = request.json.get('username', None)
    password = request.json.get('password', None)

    if username in users and users[username]['password'] == password:
        access_token = create_access_token(identity=username)
        return jsonify(access_token=access_token), 200
    else:
        return jsonify({'message': 'Invalid credentials'}), 401

# Protected route (CRUD operations)
@app.route('/protected', methods=['GET', 'POST'])
@jwt_required()
def protected():
    current_user = get_jwt_identity()
    return jsonify(logged_in_as=current_user), 200

# Configure BasicAuth
auth = HTTPBasicAuth()

@auth.verify_password
def verify_password(username, password):
    if username in users and \
            check_password_hash(users.get(username), password):
        return username

# Base 
@app.route('/')
@auth.login_required
def index():
    return "Hello, {}!".format(auth.current_user())

# Create a User
@app.route('/register', methods=['POST'])
def add_user():
    _json = request.json
    _name = _json['name']
    _email = _json['email']
    _pwd = _json['pwd']

    if _name and _email and _pwd and request.method == 'POST':
        _hashed_password = generate_password_hash(_pwd) 
        id = mongo.db.user.insert_one({'name': _name, 'email': _email, 'pwd': _hashed_password})
        return {"data":"User registered successfully"}
    else:
        return {'error':'Not found'}

apis = [
    "http://localhost:8080/api/blogs"
    # Add more endpoints as needed
]

# Get all blogs
@app.route('/api/blogs', methods=['GET'])
def get_blogs():
    blogs = mongo.db.blog.find()
    resp = dumps(blogs)
    return resp

# Get a specific blog by ID
@app.route('/api/blogs/<id>')
@jwt_required()
def blog(id):
    blog = mongo.db.blog.find_one({'_id':ObjectId(id)})
    resp = dumps(blog)
    return resp

# Delete a blog
@app.route('/api/blogs/<id>', methods=['DELETE'])
@jwt_required()
def delete_blog(id):
    mongo.db.blog.delete_one({'_id':ObjectId(id)})
    resp = jsonify("Blog Deleted Successfully")
    resp.status_code = 200
    return resp

# Update a blog
@app.route('/api/blogs/<id>', methods=['PUT'])
@jwt_required()
def update_blog(id):
    _json = request.json
    _id = id
    _title = _json['title']
    _content = _json['content']
    _author = _json['author']
    _timestamp = _json['timestamp']

    if _title and _content and _author and _timestamp and request.method == 'PUT':
        mongo.db.blog.update_one({'_id': ObjectId(_id['$oid']) if '$oid' in _id else ObjectId(_id)}, {'$set': {'title': _title, 'content': _content, 'author': _author, 'timestamp': _timestamp }})
        resp = jsonify("Blog Updated Successfully")
        resp.status_code = 200
        return resp

# Create a blog
@app.route('/api/blogs', methods=['POST'])
@jwt_required()
def create_booking():
    _json = request.json
    _title = _json['title']
    _content = _json['content']
    _author = _json['author']
    _timestamp = _json['timestamp']

    if _title and _content and _author and _timestamp and request.method == 'POST':
        id = mongo.db.blog.insert_one({'title': _title, 'content': _content, 'author': _author, 'timestamp': _timestamp })
        return {"data":"Blog Added Successfully"}
    else:
        return {'error':'Blog Not Found'}

# Run the flask App
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)