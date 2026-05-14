# Task Manager API

A multi‑user task management backend with JWT authentication.
Users register, log in, create tasks, group them into categories,
and track completion. Every user sees only their own data.

## Why I built this

I wanted a simple tool to keep my tasks in a database instead of a
notepad, and I was curious how JSON Web Tokens actually work. This
project is the result: a REST API that any frontend or curl can talk to.

## Features

- User registration with password hashing
- JWT login protecting all sensitive routes
- Full CRUD for tasks with dynamic field updates
- Per‑user categories
- Ownership enforcement
- Environment variable configuration

## Tech Stack

- Python 3.10 + Flask
- PostgreSQL 16
- Flask‑JWT‑Extended
- psycopg2
- Werkzeug

## Getting Started

1. Clone the repository
   git clone https://github.com/aliaizn/task-manager.git
   cd task-manager

2. Set up environment variables
   cp .env.example .env
   Edit .env with your own database credentials and a strong JWT secret.

3. Start a PostgreSQL database
   docker run --name task-db \
     -e POSTGRES_PASSWORD=yourpass \
     -e POSTGRES_DB=taskmanager \
     -p 5432:5432 -d postgres:16

4. Create the tables
   docker exec -i task-db psql -U postgres -d taskmanager < schema.sql

5. Install dependencies and run
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   python app.py

6. Test with curl
   curl -X POST http://localhost:5005/api/v1/register \
     -H "Content-Type: application/json" \
     -d '{"username":"alice","password":"secret123"}'

   TOKEN=$(curl -s -X POST http://localhost:5005/api/v1/login \
     -H "Content-Type: application/json" \
     -d '{"username":"alice","password":"secret123"}' \
     | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

   curl -X POST http://localhost:5005/api/v1/tasks \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer $TOKEN" \
     -d '{"title":"Finish README","priority":"high"}'

   curl http://localhost:5005/api/v1/tasks \
     -H "Authorization: Bearer $TOKEN"

## API Endpoints

| Method | Path               | Auth | Description          |
|--------|--------------------|------|----------------------|
| GET    | /api/v1/health     | No   | Health check         |
| POST   | /api/v1/register   | No   | Register new user    |
| POST   | /api/v1/login      | No   | Login, receive JWT   |
| GET    | /api/v1/tasks      | Yes  | List your tasks      |
| POST   | /api/v1/tasks      | Yes  | Create a task        |
| PUT    | /api/v1/tasks/<id> | Yes  | Update a task        |
| DELETE | /api/v1/tasks/<id> | Yes  | Delete a task        |
| GET    | /api/v1/categories | Yes  | List your categories |
| POST   | /api/v1/categories | Yes  | Create a category    |



## Author

Ali Aizn
GitHub: github.com/aliaizn

## License

MIT
