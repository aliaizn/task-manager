from flask import Flask, request, jsonify, abort
from werkzeug.security import generate_password_hash, check_password_hash
import psycopg2
import psycopg2.extras  # for dict-like rows

from flask_jwt_extended import create_access_token
from flask_jwt_extended import get_jwt_identity
from flask_jwt_extended import jwt_required
from flask_jwt_extended import JWTManager

app = Flask(__name__)

# Setup the Flask-JWT-Extended extention
app.config["JWT_SECRET_KEY"] = "super-secret"
jwt = JWTManager(app)


# Database configuration
DB_HOST = "localhost"
DB_NAME = "taskmanager"
DB_USER = "postgres"
DB_PASS = "devpass"
DB_PORT = 5431

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
    

@app.route("/api/v1/health")
def hello_world():
    return "<p>OK</P>"

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
    
    print(f"user is: {user}")
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
            
# def protected():

#     current_user = get_jwt_identity()
#     return jsonify(logged_in_as=current_user), 200


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5005, debug=True)
