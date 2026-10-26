# PayLink on macOS

The recording target is the public app at https://paylink-radiant690s-projects.vercel.app with hosted Supabase. The Mac setup also supports isolated integration tests and an optional local application.

## Installed and verified prerequisites

This Mac uses Python 3.12.16, Node 24.22.1, npm 11.19.1 and Homebrew PostgreSQL 16.15. Pandoc, Graphviz and Poppler support documents/diagrams. Playwright's Chromium is installed. Docker is optional: native PostgreSQL is the default on macOS.

For another Mac with Homebrew:

```bash
brew install python@3.12 node@24 postgresql@16 pandoc graphviz poppler
./scripts/install.sh
.venv/bin/python -m playwright install chromium
```

The scripts prefer Homebrew Node 24 without requiring a shell profile change. Set PYTHON_BIN or POSTGRES_BIN for a custom runtime location. On Intel Homebrew, POSTGRES_BIN may need `/usr/local/opt/postgresql@16/bin`. `LOCAL_DATABASE_MODE=docker` opts into the container path; Linux defaults to Docker PostgreSQL 16.

## Isolated test database

`install.sh` preserves an existing virtual environment, installs pinned dependencies, creates private ignored .env credentials only if missing, starts a dedicated cluster in .local/postgres on 127.0.0.1:54322, applies migrations, repeats the synthetic seed safely, and builds Next.js. It does not start or rewrite an unrelated Homebrew database service. Do not delete .env while keeping the cluster: its password must match. Never commit .local or .env.

```bash
./scripts/start.sh
.venv/bin/python -m pytest backend/tests -q
.venv/bin/python scripts/browser_test.py
.venv/bin/python scripts/capture_ui.py
.venv/bin/python scripts/query_evidence.py
```

The optional local app is http://localhost:3000. Local teaching profiles use the documented public synthetic password and demo buttons. They are separate from private hosted profiles. Tests clean their local fixtures; query_evidence temporarily inserts plan rows and drops an index inside a savepoint, then rolls everything back. It refuses hosted URLs.

Startup detaches the backend and frontend into independent sessions and waits for the complete proxy/API/database health path. Logs and PID files are ignored under artifacts/. Rebuild after frontend edits. Stop the project's existing processes before changing database modes; start.sh starts missing services and does not silently replace a running app.

## Hosted app checks from this Mac

The ignored .env.hosted has the restricted Supabase URL with full certificate verification. The ignored .local/recording-users.json has private synthetic profile passwords. With those existing files:

```bash
.venv/bin/python scripts/hosted_browser_test.py
.venv/bin/python scripts/hosted_evidence.py
```

The hosted browser check targets the public URL and deliberately retains its synthetic recording data. Do not point local admin fixture tests or the local plan benchmark at Supabase. Hosted schema changes use connected tools or a separately configured trusted admin URL as described in deployment.md.

For optional Mac servers backed by Supabase, stop the existing project servers first, build with NEXT_PUBLIC_DEMO_ENABLED=false, then run `./scripts/start.sh --hosted`. APP_ORIGIN in .env.hosted must match the browser origin used locally. The hosted startup skips the native database helper and local seeding.

## Document regeneration

The existing editable model is docs/er-diagram.drawio. To regenerate diagram reference exports:

```bash
.venv/bin/python scripts/diagrams.py
dot -Tsvg docs/er-diagram.dot -o docs/er-diagram.svg
dot -Tpng -Gdpi=140 docs/er-diagram.dot -o docs/er-diagram.png
```

`scripts/export_docs.py` uses Pandoc, python-docx and LibreOffice. The Codex bundled document runtime supplies python-docx and a renderer on this Mac; pass its Python executable and set SOFFICE if needed. For a standalone environment install scripts/requirements-docs.txt and LibreOffice, then run the helper. PDF files are rendered from the final DOCX so their content and pagination agree. Visually inspect all pages after regeneration.
