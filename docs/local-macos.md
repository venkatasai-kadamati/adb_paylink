# Continue PayLink locally on macOS

## One-time prerequisites

Install and open Docker Desktop. Install Node.js 24 (the repository includes `.nvmrc`) and Python 3.12. With Homebrew already installed, `brew install python@3.12 node@24` provides the runtimes; ensure Node 24 is on your PATH, or use your existing Node version manager. Check `node --version`, `python3.12 --version`, and `docker info` before setup.

## Clone and start

```bash
git clone https://github.com/venkatasai-kadamati/adb_paylink.git
cd adb_paylink
PYTHON_BIN=python3.12 ./scripts/install.sh
./scripts/start.sh
```

Open **http://localhost:3000** on your Mac. This is your local application; Docker holds the PostgreSQL database, FastAPI handles the backend, and Next.js serves the UI. No Supabase or hosting credentials are needed for this local workflow.

The installer generates ignored `.env` and `frontend/.env.local` files, applies the schema, seeds synthetic accounts, and builds the app. Do not copy a virtual environment or node_modules folder from the cloud machine. Existing local credentials and demo data are preserved on repeat setup. The database container/volume is named `paylink-db`; keep the generated `.env` alongside that database because its passwords must match.

Use **Explore as Sai** or **Siddhardth** on the sign-in page. Manual local demo password: `PaylinkDemo!2026`. These are synthetic teaching profiles, not hosted credentials.

## Tests and screenshots

```bash
.venv/bin/python -m pytest backend/tests -q
.venv/bin/python -m playwright install chromium
.venv/bin/python scripts/browser_test.py
.venv/bin/python scripts/capture_ui.py
```

Browser helpers use Playwright's Chromium on macOS. They can also use `CHROMIUM_EXECUTABLE_PATH` if you intentionally select an installed Chromium browser. Tests administer only the isolated local teaching database and clean up their own fixtures.

## Edit the application

For frontend hot reload, stop the production frontend terminal/process started by this project, then run `npm --prefix frontend run dev` in a terminal. For backend hot reload, stop this project's existing backend, then run `.venv/bin/python -m uvicorn backend.app.main:app --reload --port 8000`. Do not run two processes on the same port. Startup PID files and logs are in ignored `artifacts/*.pid` and `artifacts/*.log`.

If using the production startup instead, run `npm --prefix frontend run build` after frontend edits and restart the frontend to serve the new build. `scripts/start.sh` starts missing services; it does not replace a running service.

## Documents

Reports and diagrams are already exported under `docs/`. For optional regeneration, install Pandoc and Graphviz (`brew install pandoc graphviz`), then run:

```bash
.venv/bin/python scripts/diagrams.py
dot -Tsvg docs/er-diagram.dot -o docs/er-diagram.svg
dot -Tpng -Gdpi=140 docs/er-diagram.dot -o docs/er-diagram.png
.venv/bin/python scripts/export_docs.py
```

Open `docs/er-diagram.drawio` in diagrams.net to edit entities/connectors directly. The report and submission guide have Markdown, PDF, DOCX, and HTML versions.

macOS setup commands are prepared for a fresh clone; the previous execution evidence was collected on Linux, not on a Mac. Hosted Supabase/public deployment is a separate unfinished workflow described in `docs/deployment.md`.
