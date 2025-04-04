# Smukfest 2025 Risk Tool

This project fetches artist and schedule data for Smukfest 2025, stores it in a local SQLite database along with risk assessments and user data using **SQLAlchemy ORM**, and presents it through a **FastAPI** web application. Development is streamlined using **Docker Compose**.

## Features

*   **Database Storage:** Uses SQLAlchemy ORM to manage artists, stages, events, risk assessments, and users in a local SQLite database (`smukfest_artists.db`).
*   **Data Synchronization:** Includes scripts to fetch data from external sources (like Smukfest API) and potentially seed initial data.
*   **Web Interface (FastAPI):**
    *   Displays artists and their schedules.
    *   Provides filtering capabilities.
    *   Includes an **Admin Interface** for viewing and editing artist risk assessments.
    *   Uses Jinja2 templates for rendering.
*   **Authentication:**
    *   **Database-backed Users:** User credentials stored securely in the database.
    *   Secure password hashing (bcrypt).
    *   JWT-based authentication using secure HTTP-only cookies.
    *   Login page, persistent sessions, and logout functionality.
    *   Role-based access control (Admin vs. User).
*   **Development Environment:** Uses **Docker Compose** for easy setup, dependency management, and hot-reloading.

## Setup and Running (Docker Compose - Recommended)

This is the recommended way to set up and run the application for development.

1.  **Prerequisites:**
    *   Git
    *   Docker & Docker Compose ([Install Docker Desktop](https://www.docker.com/products/docker-desktop/))

2.  **Clone the repository:**
    ```bash
    git clone <your-repo-url>
    cd Smukfest2025
    ```

3.  **Configure Environment Variables:**
    *   Create a `.env` file in the project root directory (you can copy `.env.example` if it exists).
    *   **Generate `SECRET_KEY`:** Run `openssl rand -hex 32` in your terminal and paste the output as the value for `SECRET_KEY`. **Keep this secret!**
    *   The `.env` file should contain at least:
        ```dotenv
        # --- Security ---
        SECRET_KEY="YOUR_GENERATED_SECRET_KEY_HERE"
        ALGORITHM="HS256"
        ACCESS_TOKEN_EXPIRE_MINUTES=1440 # 1 day (adjust as needed)

        # Other variables if needed by your app/scripts
        # e.g., DATABASE_URL (if not hardcoded in database.py)
        ```
    *   **Note:** User credentials are now managed in the database, not `.env`.

4.  **Build and Start the Container:**
    ```bash
    docker compose up --build
    ```
    *   This command builds the Docker image based on `Dockerfile` and starts the `web` service defined in `docker-compose.yml`.
    *   The first build might take some time.
    *   Use `docker compose up --build -d` to run in detached (background) mode.

5.  **Seed Initial Users:** The database tables will be created automatically on the first run (via `create_db_tables()` in `main.py`). To log in, you need to add users to the database. Run the seeding script *after* the container is up and running:
    ```bash
    docker exec smukfest-app-compose python scripts/seed_users.py 
    ```
    *   (Replace `smukfest-app-compose` with your container name if different).
    *   This script adds the default users:
        *   `admin` / `skovtrold` (Admin role)
        *   `smuk` / `storcigar` (User role)

6.  **Access the application:** Open your web browser and navigate to `http://127.0.0.1:8000`.

7.  **Login:** Use one of the seeded user credentials.

8.  **Hot Reloading:** Thanks to Docker volumes defined in `docker-compose.yml`, any changes you make to the code in the `./app` or `./scripts` directory on your local machine will automatically trigger a reload of the application inside the container.

9.  **Stopping:**
    ```bash
    docker compose down
    ```
    *   (If running in foreground, press `Ctrl+C` first).

## (Alternative) Local Python Environment Setup

While Docker is recommended, you can still run locally if preferred.

1.  **Prerequisites:** Git, Python 3.11+.
2.  **Clone:** `git clone ...`, `cd ...`
3.  **Create Virtual Env:** `python3 -m venv venv`, `source venv/bin/activate` (or equivalent for your OS).
4.  **Install Deps:** `pip install --upgrade pip`, `pip install -r requirements.txt`.
5.  **Configure `.env`:** Create `.env` and set `SECRET_KEY` as described in the Docker section.
6.  **Initialize/Update Database:**
    *   The first time, run `python -c "from app.database import create_db_tables; create_db_tables()"` to create tables.
    *   Run `python scripts/seed_users.py` to add initial users.
    *   Run `python scripts/sync_artists_db.py` (if needed and updated for SQLAlchemy) to populate artist/event data.
7.  **Run Server:** `uvicorn app.main:app --reload`.
8.  **Access:** `http://127.0.0.1:8000`.

## Project Structure

```
Smukfest2025/
├── app/                 # FastAPI application code
│   ├── static/          # Static files (CSS, JS, images)
│   ├── templates/       # HTML templates (Jinja2)
│   │   ├── base.html
│   │   ├── index.html
│   │   ├── login.html
│   │   ├── admin_assessments.html
│   │   └── artist_detail.html 
│   ├── __init__.py
│   ├── auth.py          # Authentication logic (JWT, cookies, dependencies)
│   ├── crud.py          # Database Create, Read, Update, Delete operations (using SQLAlchemy)
│   ├── database.py      # SQLAlchemy setup (engine, SessionLocal, Base)
│   ├── main.py          # FastAPI app definition, routes, startup
│   ├── models.py        # SQLAlchemy ORM models
│   └── schemas.py       # Pydantic schemas (for validation and serialization)
│   └── utils.py         # Utility functions
├── scripts/             # Utility scripts
│   ├── seed_users.py    # Creates initial admin/demo users in the DB
│   └── sync_artists_db.py # (Needs review/update) Syncs API data to local DB
├── .env                 # Environment variables (SECRET!, config) - DO NOT COMMIT
├── .gitignore           # Files/directories ignored by Git
├── Dockerfile           # Instructions for building the Docker image
├── .dockerignore        # Files/directories ignored by Docker build
├── docker-compose.yml   # Docker Compose configuration for development
├── README.md            # This file
├── requirements.txt     # Python dependencies
├── plan.md              # Project plan notes
├── todo.md              # Project TODO list
└── smukfest_artists.db  # SQLite database file - DO NOT COMMIT (usually)
```

## Database Structure (SQLAlchemy Models)

Defined in `app/models.py`:

*   **`Artist`:** Core artist info (slug, title, nationality, etc.).
*   **`Stage`:** Stage information (name, etc.).
*   **`Event`:** Schedule info (start/end times), linked to `Artist` (via `artist_slug`) and `Stage` (via `stage_id`).
*   **`RiskAssessment`:** Assessment details linked one-to-one with `Artist` (via `artist_slug`). Stores levels (risk, intensity, density), notes, etc.
*   **`User`:** User information (username, hashed_password, role, email, etc.).

## Future Ideas / TODOs

(See `plan.md` and `todo.md` for more details)

*   Review/Update `scripts/sync_artists_db.py` to use SQLAlchemy ORM.
*   Implement database migrations (e.g., using Alembic) for schema changes instead of relying solely on `create_all`.
*   Add more comprehensive tests (unit, integration).
*   Refine UI/UX (loading indicators, clearer error messages, improved styling).
*   Add more filtering/sorting options to the UI.
*   Configure for production deployment (different Dockerfile/Compose setup, HTTPS, etc.).
*   Potential enhancements to risk assessment data model. 