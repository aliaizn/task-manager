from flask import Flask, request, jsonify, abort
from werkzeug.security import generate_password_hash, check_password_hash
import psycopg2
import psycopg2.extras  # for dict-like rows
import os
from dotenv import load_dotenv

from flask_jwt_extended import create_access_token
from flask_jwt_extended import get_jwt_identity
from flask_jwt_extended import jwt_required
from flask_jwt_extended import JWTManager

app = Flask(__name__)

# Setup the Flask-JWT-Extended extention
app.config["JWT_SECRET_KEY"] = os.environ.get("JWT_SECRET_KEY", "dev-sercret-change-me")
jwt = JWTManager(app)


# Database configuration
DB_HOST = os.environ.get("DB_HOST", "localhost")
DB_NAME = os.environ.get("DB_NAME", "taskmanager")
DB_USER = os.environ.get("DB_USER", "postgres")
DB_PASS = os.environ.get("DB_PASS", "devpass")
DB_PORT = int(os.environ.get("DB_PORT", 5431))

load_dotenv()

def get_db_connection():
    """Return a database connection and configure row factory."""
    conn = psycopg2.connect(
        host=DB_HOST,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASS,
        port=DB_PORT
    )
    #This makes rows behave like dictionaries (column: value)
    conn.cursor_factory = psycopg2.extras.RealDictCursor
    return conn
    
def get_current_user():
    """Return the user dict for the currently authenticated user."""
    user_id = get_jwt_identity()
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, username FROM users WHERE id = %s", (int(user_id),))
    user = cur.fetchone()
    cur.close()
    conn.close()
    if user is None:
        abort(404, description="User not found")
    return user
    

@app.route("/api/v1/health", methods=["GET"])
def hello_world():
    return  jsonify({"msg":"OK"}), 200

@app.route("/api/v1/register", methods=["POST"])
def register():
    data = request.get_json()
    username = data.get("username", "").strip()
    password = data.get("password", "")

    if not username or not password:
        return jsonify({"msg": "Username and password are required."}), 400
    if len(password) < 6:
        return jsonify({"msg": "Password must be at least 6 characters"}), 400

    conn = get_db_connection()
    cur = conn.cursor()
    #check if the username already exists
    cur.execute("SELECT id FROM users WHERE username = %s", (username,))
    if cur.fetchone() is not None:
        cur.close()
        conn.close()
        return jsonify({"msg": "Username already exists"}), 409

    # Insert new user
    password_hash = generate_password_hash(password)
    cur.execute(
        "INSERT INTO users (username, password_hash) VALUES (%s, %s) RETURNING id", (username, password_hash)
        )
    new_id = cur.fetchone()["id"]
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({"msg": "User registerd successfully", "id": new_id}), 201

@app.route("/api/v1/login", methods=["POST"])
def login():
    data = request.get_json()
    username = request.json.get("username", "").strip()
    password = request.json.get("password", "")

    if not username or not password:
        return jsonify({"msg": "Username and password are required."}), 400

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, password_hash FROM users WHERE username = %s", (username,))
    user = cur.fetchone()
    cur.close()
    conn.close()
    
    if user is None:
        return jsonify({"msg": "Bad username or password"}), 401

    if not check_password_hash(user["password_hash"], password):
        return jsonify({"msg": "Bad username or password"}), 401
        
    access_token = create_access_token(identity=str(user["id"]))
    return jsonify(access_token=access_token), 200

@app.route("/api/v1/tasks", methods=['GET'])
@jwt_required()
def list_tasks():
    user = get_current_user()
    # Get filters from query strings (optional)
    category_id = request.args.get("category_id", type=int)
    status = request.args.get("status") # "done" or "pending"


    conn = get_db_connection()
    cur = conn.cursor()

    query = "SELECT * FROM tasks WHERE user_id = %s"
    params = [user["id"]]

    if category_id is not None:
        query += " AND category_id = %s"
        params.append(category_id)
    if status == "done":
        query += " AND completed = TRUE"
    elif status == "pending":
        query += " AND completed = FALSE"

    query += " ORDER BY created_at DESC"
    cur.execute(query, params)
    tasks = cur.fetchall()
    cur.close()
    conn.close()
    return jsonify(tasks), 200

@app.route("/api/v1/tasks", methods=["POST"])
@jwt_required()
def create_task():
   user = get_current_user()
   data = request.get_json()
   category_id = request.json.get("category_id")
   title = request.json.get("title")
   description = request.json.get("description")
   due_date= request.json.get("due_date")
   priority = request.json.get("priority")

   if title is None:
       return jsonify({"msg": "title is missing"}), 400
       

   conn = get_db_connection()
   cur = conn.cursor()

   if category_id is not None:
       cur.execute("SELECT id, user_id FROM categories WHERE id = %s", (category_id,))
       row = cur.fetchone()
       if row is None or row['user_id'] != user['id']:
           return jsonify({"msg": "Invalid category"}), 400
       
   cur.execute(
       "INSERT INTO tasks (title, description, due_date, priority, category_id, user_id) VALUES (%s, %s, %s, %s, %s, %s) RETURNING id", (title, description, due_date, priority, category_id, user['id'])
)
   new_id = cur.fetchone()["id"]
   conn.commit()
   cur.close()
   conn.close()

   return jsonify({"msg": "Task created", "id":new_id}), 201
   

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5005, debug=True)
