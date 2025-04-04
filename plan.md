# Project Plan: Smukfest 2025 Risk Tool

## Phase 1: Core Data Handling & Basic Display (Completed)

*   [x] **API Investigation:** Understand the Smukfest API structure (`/api/content?path=%2Fprogram`).
*   [x] **Data Fetching Script:** Create `scripts/sync_artists_db.py` to fetch data.
*   [x] **Data Parsing:** Extract relevant artist, stage, and schedule information.
*   [x] **Database Schema:** Define SQLite schema for `artists` and `events` tables.
*   [x] **Database Synchronization:** Implement logic in script to:
    *   [x] Create tables if they don't exist.
    *   [x] Upsert artist data.
    *   [x] Clear and repopulate events data.
    *   [x] Handle stale data (delete old artists/events).
*   [x] **Basic FastAPI App:** Set up `app/main.py`.
*   [x] **Database Module:** Create `app/database.py` for DB connection and queries (`get_all_artists`, `get_all_events`).
*   [x] **Basic Web Page:** Create `app/templates/index.html` using Jinja2 and Tailwind CSS.
*   [x] **Display Artists:** Show fetched artists in a grid.
*   [x] **Display Schedule:** Show full schedule in a table.
*   [x] **Link Artist/Schedule:** Display performance times/stages on artist cards.

## Phase 2: UI Enhancements & Authentication (Completed)

*   [x] **Human-Readable Dates:** Format ISO timestamps nicely in the UI.
*   [x] **Filtering:** Add dropdown filters for Date and Stage.
*   [x] **Client-Side Filtering:** Implement JavaScript to filter artist grid and schedule table.
*   [x] **Password Protection:** Secure the application with login.
    *   [x] Add dependencies (`passlib`, `python-jose`).
    *   [x] Implement password hashing.
    *   [x] Implement JWT creation/validation.
    *   [x] Use secure HTTP-only cookies for session persistence.
    *   [x] Create login page (`login.html`).
    *   [x] Add `/login` (GET/POST) and `/logout` routes.
    *   [x] Protect main route (`/`) with auth dependency.
    *   [x] Use `.env` for configuration (secret key, credentials).

## Phase 3: Risk Assessment Features & Refinements (Next)

*   **Implement Risk Assessment Storage & Editing:**
    *   [ ] **DB Schema:** Add `risk_assessments` table to SQLite (`artist_slug` PK/FK, levels, notes, `updated_at`).
    *   [ ] **Update Sync Script:** Modify `setup_database` in `sync_artists_db.py` to create the new table.
    *   [ ] **Pydantic Models:** Define `RiskAssessment` models (Base, Create, Read).
    *   [ ] **DB Functions:** Add `get_assessment`, `get_all_assessments`, `upsert_assessment` to `app/database.py`.
    *   [ ] **Admin Dependency:** Create `get_admin_user` dependency for admin-only route access.
    *   [ ] **API Endpoint (Save):** Create `POST /api/assessments/{artist_slug}` endpoint (protected by admin dependency) to save/update assessment data.
    *   [ ] **Admin Page Route (View):** Create `GET /admin/assessments` route (protected by admin dependency) to fetch artists and assessments.
    *   [ ] **Admin Template:** Create `admin_assessments.html` to display artists and current assessment values.
    *   [ ] **Edit UI:** Implement inline/modal form with dropdowns (risk, intensity, density) and text areas (remarks, crowd, notes).
    *   [ ] **JavaScript:** Add JS to handle form display, submission via Fetch API to the POST endpoint, and update UI dynamically.
*   **Stage Mapping:** (Future)
    *   Investigate if API `location` data can reliably provide stage names or IDs.
    *   Implement mapping if possible.
    *   Refine filtering/display if stage names become available.
*   **Risk Assessment Logic & Display:** (Future - after storage)
    *   Define criteria for risk assessment (e.g., artist popularity, time clashes, stage capacity).
    *   Implement logic to calculate/display risk indicators based on stored assessments.
    *   Add UI elements to show risk scores/warnings on main page or admin page.
*   **User Management:** (Future)
    *   Replace hardcoded user with a database table for users.
    *   Add user registration/management features (if needed).
*   **Testing:** (Future)
    *   Add unit tests for auth and database functions.
    *   Add integration tests for API sync and main routes.
*   **UI Improvements:** (Future)
    *   Loading indicators during data fetch/filtering.
    *   More robust error handling and display.
    *   Accessibility improvements.
*   **Deployment:** (Future)
    *   Containerize the application using Docker.
    *   Set up deployment process (e.g., to a cloud platform).

## Phase 4: Long-Term Maintenance (Future)

*   Monitor API changes.
*   Update dependencies.
*   Address user feedback. 