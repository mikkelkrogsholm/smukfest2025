# Smukfest 2025 Risikoværktøj

Dette projekt indeholder en webapplikation bygget med FastAPI til at vise kunstner- og tidsplaninformation for Smukfest 2025, samt til at administrere interne risikovurderinger for kunstnerne. Applikationen henter data fra Smukfests API, gemmer det i en lokal SQLite-database (`./data/database.db`) og bruger Docker Compose til udviklingsmiljøet.

## Features

*   **Automatisk API Data Sync (Hver Time):** Applikationen synkroniserer automatisk kunstner-, scene- og tidsplandata fra Smukfests API hver time via en baggrundsjob (APScheduler), der kalder `scripts/sync_artists_db.py`. Dette script køres også én gang under den initiale opsætning via `setup.sh`.
*   **Database:** Bruger SQLite (`./data/database.db`) og SQLAlchemy ORM til at gemme data om kunstnere, scener, events, brugere og risikovurderinger. Databasen gemmes vedvarende på host-maskinen via et Docker Bind Mount.
    *   **Cascade Delete:** Hvis en kunstner slettes (f.eks. fordi den fjernes fra API'et og `sync_artists_db.py` køres), vil den tilknyttede `RiskAssessment` også automatisk blive slettet (via `ON DELETE CASCADE`).
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
    *   Hot-reloading af kodeændringer i `app/` mappen genstarter automatisk `uvicorn`-serveren (pga. `--reload --reload-dir app` i `Dockerfile`). Ændringer i `scripts/` trigger ikke automatisk genstart.

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

4.  **Kør Setup Script (Kun første gang):**
    Gør scriptet eksekverbart og kør det. Dette script automatiserer hele den initiale opsætning.

    ```bash
    chmod +x setup.sh
    ./setup.sh
    ```

    **Hvad scriptet gør:**
    *   Opretter `./data` mappen og den tomme databasefil (`./data/database.db`) på din host-maskine.
    *   Bygger Docker imaget (`smukfest2025-smukrisiko`), hvis det ikke allerede findes.
    *   Starter en **midlertidig container** baseret på dette image for at:
        *   Køre `python scripts/initialize_database.py`. Dette script:
            *   Anvender Alembic-migrationer (`alembic upgrade head`) for at oprette/opdatere databasetabellerne inde i containeren (mod `./data/database.db`).
            *   Seeder standardbrugere (`scripts/seed_users.py`).
        *   Synkroniserer kunstner/event data fra Smukfest API'en (`scripts/sync_artists_db.py`).
    *   Starter de permanente services (`traefik`, `smukrisiko`) via `docker compose up -d` i baggrunden.

    **Vigtigt:** Følg outputtet fra `./setup.sh` nøje første gang. Hvis det fejler, se afsnit 4.a nedenfor.

5.  **Fejlfinding: Manuel Oprettelse af Første Migration (hvis `setup.sh` fejler med "no such table")**
    *   Hvis `./setup.sh` fejler under database-initialiseringen (f.eks. med `sqlite3.OperationalError: no such table: users`), skyldes det sandsynligvis, at den første Alembic-migration ikke blev genereret korrekt automatisk. Dette kan ske, hvis modellerne ændres, før den allerførste migration køres.
    *   **Løsning:** Kør følgende kommando i din terminal (i projektets rodmappe) for manuelt at generere den initiale migrationsfil *inde i en container*:
        ```bash
        docker run --rm \\
            -v "$(pwd):/workspace" \\
            -w /workspace \\
            -e DATABASE_URL="sqlite:////workspace/data/database.db" \\
            --name "smukrisiko_alembic_gen" \\
            smukfest2025-smukrisiko \\
            alembic revision --autogenerate -m "Create initial tables"
        ```
    *   Dette bør oprette en ny fil i `alembic/versions/`. Verificér, at den indeholder `op.create_table(...)` kald.
    *   Slet den (potentielt tomme/ufuldstændige) `data/database.db` fil: `rm -f data/database.db`
    *   Kør `./setup.sh` igen. Den bør nu finde og anvende den manuelt genererede migration korrekt.

6.  **Tilgå Applikationen:** Åbn din browser og gå til den adresse, Traefik er konfigureret til (f.eks. `http://localhost` eller `https://risiko.smukfest.dk` afhængigt af din opsætning og DNS).

7.  **Login:** Brug en af standardbrugerne:
    *   `admin` / `skovtrold` (Admin rolle)
    *   `smuk` / `storcigar` (User rolle)

8.  **Efterfølgende Start/Stop:**
    *   For at starte applikationen igen (uden at køre setup): `docker compose up -d`
    *   For at stoppe applikationen: `docker compose down`
    *   Databasen i `./data/database.db` vil blive bevaret mellem start/stop.

9.  **Hot Reloading:** Ændringer i `./app` eller `./scripts` genstarter automatisk `uvicorn`-serveren inde i `smukrisiko`-containeren, når den kører via `docker compose up`.

## Projektstruktur

```
Smukfest2025/
├── alembic/             # Alembic migrations mappe
│   ├── versions/        # Migrations-scripts
│   ├── env.py           # Alembic environment setup
│   ├── script.py.mako   # Migrations script template
│   └── README           # Alembic README
├── app/                 # FastAPI applikationskode
│   ├── static/          # Statiske filer (CSS, JS, billeder, favicons)
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
│   └── sync_artists_db.py # Synkroniserer med Smukfest API (køres automatisk hver time og under setup)
│   └── restore_assessments.py # (Manuelt script) Gendanner assessments fra en backup DB
├── .env                 # Miljøvariabler (SECRET!, config) - BØR IKKE COMMITTES!
├── .gitignore           # Filer/mapper ignoreret af Git
├── Dockerfile           # Instruktioner til at bygge Docker image (inkl. locale & startup CMD med --reload-dir)
├── .dockerignore        # Filer/mapper ignoreret af Docker build
├── alembic.ini          # Alembic konfigurationsfil
├── docker-compose.yml   # Docker Compose konfiguration (service, volumes, ports)
├── README.md            # Denne fil
├── requirements.txt     # Python dependencies
└── setup.sh             # Initialiseringsscript (bruger Alembic)
```

## Database Struktur (SQLAlchemy Modeller)

Defineret i `app/models.py`:

*   **`Artist`:** Basisinfo om kunstner (id, slug, title, nationality, image_url, etc.).
*   **`Stage`:** Sceneinformation (id, name).
*   **`Event`:** Tidsplaninfo (event\_id, start\_time, end\_time), linket til `Artist` (via `artist_slug`) og `Stage` (via `stage_id`).
*   **`RiskAssessment`:** Vurderingsdetaljer (id, artist\_slug, risk\_level, intensity\_level, density\_level, remarks, crowd\_profile, notes, updated\_at), linket one-to-one med `Artist`. **Bemærk:** Har `ondelete="CASCADE"` på `artist_slug`, så vurderingen slettes hvis kunstneren slettes.
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
    *   Sæt environment variable for database path: `export DATABASE_URL='sqlite:///./data/database.db'`
    *   Kør Alembic migrations for at oprette/opdatere tabellerne: `alembic upgrade head`
    *   Kør sync: `python scripts/sync_artists_db.py` (bruger `DATABASE_URL` fra env)
    *   Kør seeding: `python scripts/seed_users.py` (bruger `DATABASE_URL` fra env)
7.  **Kør Server:** `uvicorn app.main:app --reload`.
8.  **Tilgå:** `http://127.0.0.1:8000`.

## Future Ideas / TODOs

(See `plan.md` and `todo.md` for more details)

*   Add more comprehensive tests (unit, integration).
*   Refine UI/UX (loading indicators, clearer error messages, improved styling).
*   Add more filtering/sorting options to the UI.
*   Configure for production deployment (different Dockerfile/Compose setup, HTTPS, etc.).
*   Potential enhancements to risk assessment data model. 