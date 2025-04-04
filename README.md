# Smukfest 2025 Risikoværktøj

Dette projekt indeholder en webapplikation bygget med FastAPI til at vise kunstner- og tidsplaninformation for Smukfest 2025, samt til at administrere interne risikovurderinger for kunstnerne. Applikationen henter data fra Smukfests API, gemmer det i en lokal SQLite-database og bruger Docker Compose til udviklingsmiljøet.

## Features

*   **API Data Sync:** Henter automatisk kunstner- og tidsplandata fra Smukfests API ved opstart af containeren via `scripts/sync_artists_db.py`.
*   **Database:** Bruger SQLite (`smukfest_artists.db`) og SQLAlchemy ORM til at gemme data om kunstnere, scener, events, brugere og risikovurderinger. Databasen gemmes vedvarende vha. Docker Volumes (eller Bind Mount, afhængig af `docker-compose.yml` konfiguration).
*   **Web Interface (FastAPI & Jinja2):**
    *   Viser et overblik over kunstnere og tidsplan.
    *   Filtrering af kunstnere/tidsplan (dato, scene, risikoniveau).
    *   Detaljeside for hver kunstner.
    *   Admin-interface (`/admin/assessments`) til at se og redigere risikovurderinger.
*   **Autentificering:**
    *   Brugerstyring i databasen (Admin/User roller).
    *   Sikker password hashing (bcrypt).
    *   JWT-baseret autentificering via HTTP-only cookies.
    *   Automatisk oprettelse af standardbrugere (`admin`/`skovtrold`, `smuk`/`storcigar`) ved opstart via `scripts/seed_users.py`.
*   **Udviklingsmiljø (Docker Compose):**
    *   Nem opsætning af containermiljø.
    *   Automatisk database-synkronisering og bruger-seeding ved opstart.
    *   Hot-reloading af kodeændringer i `app/` og `scripts/`.

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

4.  **(Valgfrit - Hvis Bind Mount bruges for DB):** Hvis `docker-compose.yml` bruger et bind mount for databasen (`- ./smukfest_artists.db:/app/smukfest_artists.db`), opret da en tom databasefil lokalt før første start:
    ```bash
    touch smukfest_artists.db
    # Juster evt. rettigheder, hvis containeren ikke kan skrive til filen:
    # chmod 666 smukfest_artists.db
    ```
    *(Bemærk: Bruger du et named volume (anbefales), er dette trin ikke nødvendigt).*

5.  **Byg og Start Containeren:**
    ```bash
    docker compose up --build
    ```
    *   Dette bygger Docker-imaget baseret på `Dockerfile` og starter `web`-servicen defineret i `docker-compose.yml`.
    *   Ved første start (og efterfølgende starter) vil `CMD`-instruktionen i `Dockerfile` automatisk køre `sync_artists_db.py` og `seed_users.py` før `uvicorn` starter. Se output i terminalen.
    *   Brug `-d` flaget (`docker compose up --build -d`) for at køre i baggrunden (detached mode).

6.  **Tilgå Applikationen:** Åbn din browser og gå til `http://127.0.0.1:8000`.

7.  **Login:** Brug en af standardbrugerne:
    *   `admin` / `skovtrold` (Admin rolle)
    *   `smuk` / `storcigar` (User rolle)

8.  **Hot Reloading:** Ændringer i `./app` eller `./scripts` genstarter automatisk `uvicorn`-serveren inde i containeren.

9.  **Stop:**
    *   Hvis kørende i forgrunden: Tryk `Ctrl+C`.
    *   Kør derefter (eller hvis kørende i baggrunden):
        ```bash
        docker compose down
        ```
        *(Bruger du named volume, slettes databasen ikke her. Bruger du bind mount, bevares filen lokalt).*

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
├── scripts/             # Hjælpescripts
│   ├── seed_users.py    # Opretter standardbrugere i DB
│   └── sync_artists_db.py # Henter API data og synkroniserer kunstnere/events/scener til DB
├── .env                 # Miljøvariabler (SECRET!, config) - BØR IKKE COMMITTES!
├── .gitignore           # Filer/mapper ignoreret af Git
├── Dockerfile           # Instruktioner til at bygge Docker image (inkl. locale & startup CMD)
├── .dockerignore        # Filer/mapper ignoreret af Docker build
├── docker-compose.yml   # Docker Compose konfiguration (service, volumes, ports)
├── README.md            # Denne fil
├── requirements.txt     # Python dependencies
└── smukfest_artists.db  # SQLite database fil (oprettes/bruges via volume/bind mount)
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
    *   Kør `python -c "from app.database import create_db_tables; create_db_tables()"` for at oprette tabellerne i en lokal `smukfest_artists.db`.
    *   Kør `python scripts/sync_artists_db.py` for at hente data.
    *   Kør `python scripts/seed_users.py` for at oprette standardbrugere.
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