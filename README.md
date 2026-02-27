# Contacts

Contacts is a FastAPI backend with a React frontend for managing personal contacts.

## Features

- Add, view, edit, search, and delete contacts
- iOS-inspired list/detail rough-draft UI in React
- Existing backend API contract preserved (`/contacts/*`, `/messages/*`, `/emails/*`)

## Run backend

```bash
make install
make run-uvicorn
```

The API runs on `http://127.0.0.1:8000` by default.

## Run React frontend (development)

```bash
cd frontend
npm install
npm run dev
```

Vite runs on `http://127.0.0.1:5173` and proxies API requests to FastAPI.

## Build React and serve through FastAPI

```bash
cd frontend
npm install
npm run build
```

Or via Makefile:

```bash
make frontend-install
make frontend-build
```

After build, FastAPI serves `frontend/dist/index.html` at `/`.
If no React build exists yet, `/` falls back to the legacy `static/index.html`.

## Deployment note

The React build output in `frontend/dist` must be present in the deployed artifact.
If your deploy pipeline does not run `npm run build`, deploy will show the legacy UI.
