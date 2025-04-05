# Smukfest 2025 Risikoværktøj

Dette projekt indeholder en webapplikation bygget med FastAPI til at vise kunstner- og tidsplaninformation for Smukfest 2025, samt til at administrere interne risikovurderinger for kunstnerne. Applikationen henter data fra Smukfests API, gemmer det i en lokal SQLite-database (`./data/database.db`) og bruger Docker Compose til udviklingsmiljøet.

## Features

*   **API Data Sync:** Henter kunstner- og tidsplandata fra Smukfests API via `scripts/sync_artists_db.py` (køres under `setup.sh`).
*   **Database:** Bruger SQLite (`./data/database.db`) og SQLAlchemy ORM til at gemme data om kunstnere, scener, events, brugere og risikovurderinger. Databasen gemmes vedvarende på host-maskinen via et Docker Bind Mount.
*   **Web Interface (FastAPI & Jinja2):**
    *   Viser et overblik over kunstnere og tidsplan.
    *   Filtrering af kunstnere/tidsplan (dato, scene, risikoniveau).
    *   Detaljeside for hver kunstner.
    *   Admin-interface (`/admin/assessments`) til at se og redigere risikovurderinger.
*   **Autentificering:**
    *   Brugerstyring i databasen (Admin/User roller).
    *   Sikker password hashing (bcrypt).
    *   JWT-baseret autentificering via HTTP-only cookies.
    *   Oprettelse af standardbrugere (`admin`/`skovtrold`, `smuk`/`storcigar`) via `scripts/seed_users.py` (køres under `setup.sh`).
*   **Udviklingsmiljø (Docker Compose):**
    *   Nem opsætning af containermiljø.
    *   Dedikeret setup-script (`setup.sh`) til initial database-oprettelse, seeding og synkronisering.
    *   Hot-reloading af kodeændringer i `app/` og `scripts/` når applikationen kører via `docker compose up`.

## Opsætning og Kørsel (Docker Compose - Anbefalet)

1.  **Forudsætninger:**
    *   Git
    *   Docker & Docker Compose ([Installer Docker Desktop](https://www.docker.com/products/docker-desktop/))

2.  **Klon Repositoriet:**
    ```bash
    git clone <your-repo-url>
    cd Smukfest2025
    ```

3.  **Konfigurer Miljøvariabler:**
    *   Opret en `.env` fil i projektets rodmappe (kopiér evt. `.env.example` hvis den findes).
    *   **Generer `SECRET_KEY`:** Kør `openssl rand -hex 32` i din terminal og indsæt outputtet som værdi for `SECRET_KEY`. **Hold denne hemmelig!**
    *   `.env`-filen skal som minimum indeholde:
        ```dotenv
        # --- Sikkerhed ---
        SECRET_KEY="DIN_GENEREREDE_SECRET_KEY_HER"
        ALGORITHM="HS256"
        ACCESS_TOKEN_EXPIRE_MINUTES=1440 # 1 dag (juster efter behov)

        # Evt. andre variable...
        ```

4.  **Kør Setup Script (Første gang):**
    Gør scriptet eksekverbart og kør det. Dette script vil:
    *   Oprette `./data` mappen og den tomme databasefil (`./data/database.db`).
    *   Bygge Docker imaget.
    *   Køre en midlertidig container for at initialisere databasetabellerne, oprette standardbrugere og synkronisere kunstner/event data fra API'en.
    *   Starte alle services (`traefik`, `smukrisiko`) i baggrunden.

    ```bash
    chmod +x setup.sh
    ./setup.sh
    ```
    *Følg outputtet for eventuelle fejl under processen.*

5.  **Tilgå Applikationen:** Åbn din browser og gå til den adresse, Traefik er konfigureret til (f.eks. `http://localhost` eller `https://risiko.smukfest.dk` afhængigt af din opsætning og DNS).

6.  **Login:** Brug en af standardbrugerne:
    *   `admin` / `skovtrold` (Admin rolle)
    *   `smuk` / `storcigar` (User rolle)

7.  **Efterfølgende Start/Stop:**
    *   For at starte applikationen igen (uden at køre setup): `docker compose up -d`
    *   For at stoppe applikationen: `docker compose down`
    *   Databasen i `./data/database.db` vil blive bevaret mellem start/stop.

8.  **Hot Reloading:** Ændringer i `./app` eller `./scripts` genstarter automatisk `uvicorn`-serveren inde i containeren, når den kører via `docker compose up`.

## Projektstruktur

```
Smukfest2025/
├── app/                 # FastAPI applikationskode
│   ├── static/          # Statiske filer (CSS, JS, billeder - f.eks. logo, favicon)
│   ├── templates/       # HTML skabeloner (Jinja2)
│   │   ├── base.html
│   │   ├── index.html
│   │   ├── login.html
│   │   ├── admin_assessments.html
│   │   └── artist_detail.html
│   ├── __init__.py
│   ├── auth.py          # Autentificeringslogik (JWT, cookies, dependencies)
│   ├── crud.py          # Database CRUD operationer (SQLAlchemy)
│   ├── database.py      # SQLAlchemy setup (engine, SessionLocal, Base, table creation)
│   ├── main.py          # FastAPI app definition, routes, startup logic
│   ├── models.py        # SQLAlchemy ORM modeller
│   ├── schemas.py       # Pydantic schemas (validering, serialisering)
│   └── utils.py         # Hjælpefunktioner (f.eks. datoformatering)
├── data/                # Mappe til persistente data (oprettes af setup.sh)
│   └── database.db      # SQLite database fil
├── scripts/             # Hjælpescripts
│   ├── seed_users.py    # Opretter standardbrugere
│   └── sync_artists_db.py # Synkroniserer med Smukfest API
├── .env                 # Miljøvariabler (SECRET!, config) - BØR IKKE COMMITTES!
├── .gitignore           # Filer/mapper ignoreret af Git
├── Dockerfile           # Instruktioner til at bygge Docker image (inkl. locale & startup CMD)
├── .dockerignore        # Filer/mapper ignoreret af Docker build
├── docker-compose.yml   # Docker Compose konfiguration (service, volumes, ports)
├── README.md            # Denne fil
├── requirements.txt     # Python dependencies
└── setup.sh             # Initialiseringsscript
```

## Database Struktur (SQLAlchemy Modeller)

Defineret i `app/models.py`:

*   **`Artist`:** Basisinfo om kunstner (id, slug, title, nationality, image_url, etc.).
*   **`Stage`:** Sceneinformation (id, name).
*   **`Event`:** Tidsplaninfo (event\_id, start\_time, end\_time), linket til `Artist` (via `artist_slug`) og `Stage` (via `stage_id`).
*   **`RiskAssessment`:** Vurderingsdetaljer (id, artist\_slug, risk\_level, intensity\_level, density\_level, remarks, crowd\_profile, notes, updated\_at), linket one-to-one med `Artist`.
*   **`User`:** Brugerinformation (id, username, email, hashed\_password, role, disabled, created\_at).

## (Alternativ) Lokal Python Opsætning

Selvom Docker anbefales, kan du køre lokalt:

1.  **Forudsætninger:** Git, Python 3.11+.
2.  **Klon:** `git clone ...`, `cd ...`
3.  **Virtuelt Miljø:** `python3 -m venv venv`, `source venv/bin/activate` (eller tilsvarende).
4.  **Installer Dependencies:** `pip install --upgrade pip`, `pip install -r requirements.txt`.
5.  **Konfigurer `.env`:** Opret `.env` og sæt `SECRET_KEY` som beskrevet i Docker-sektionen.
6.  **Initialiser Database:**
    *   Opret mappen: `mkdir -p data`
    *   Kør `python -c "import os; from app.database import create_db_tables, DATABASE_URL; print(f'Using DB: {DATABASE_URL}'); create_db_tables()"` for at oprette tabellerne i `./data/database.db`.
    *   Sæt environment variable og kør sync: `export DATABASE_URL='sqlite:///./data/database.db'; python scripts/sync_artists_db.py`
    *   Kør seeding: `python scripts/seed_users.py` (Denne skal muligvis også opdateres til at bruge DATABASE_URL hvis den køres uden for docker).
7.  **Kør Server:** `uvicorn app.main:app --reload`.
8.  **Tilgå:** `http://127.0.0.1:8000`.

## Future Ideas / TODOs

(See `plan.md` and `todo.md` for more details)

*   Review/Update `scripts/sync_artists_db.py` to use SQLAlchemy ORM.
*   Implement database migrations (e.g., using Alembic) for schema changes instead of relying solely on `create_all`.
*   Add more comprehensive tests (unit, integration).
*   Refine UI/UX (loading indicators, clearer error messages, improved styling).
*   Add more filtering/sorting options to the UI.
*   Configure for production deployment (different Dockerfile/Compose setup, HTTPS, etc.).
*   Potential enhancements to risk assessment data model. 