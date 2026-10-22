# JalSetu — MDM Water Supply Management System

JalSetu is a web application project designed to help users report water-supply problems, track complaints, and allow administrators to manage complaint resolution.

## Project Technology

- **Frontend:** HTML, CSS, JavaScript
- **Backend:** Python, Flask REST API
- **Database:** PostgreSQL
- **Authentication:** JWT-based authentication
- **Image processing:** Pillow
- **Backend server:** Flask for development; Gunicorn is included for deployment

## Features

- User registration, login, and logout
- Submit water-supply complaints
- Add complaint descriptions and location information
- Upload complaint images through the backend's validated upload flow
- Track complaints using a reference number
- View complaint information and status
- Admin dashboard for complaint management
- Update complaint statuses: Pending, In Progress, and Resolved
- Complaint search and dashboard statistics
- Built-in rule-based chatbot for basic water-supply guidance
- Shared frontend API configuration to support changing the backend URL

**Chatbot note:** The current chatbot uses predefined responses. It is not a fully integrated cloud AI assistant.

## Repository Structure

```text
jalsetu/
├── backend/
│   ├── app.py
│   ├── models.py
│   ├── requirements.txt
│   └── uploads/              # Runtime uploads; not committed
├── frontend/
│   ├── home.html
│   ├── index.html
│   ├── login.html
│   ├── register.html
│   ├── dashboard.html
│   ├── admin.html
│   ├── config.js
│   └── chatbot.js
├── .gitignore
└── README.md
```

## Prerequisites

- Python and pip
- PostgreSQL
- Git
- A modern web browser

The development instructions below assume the repository's existing Python virtual environment and PostgreSQL configuration are available.

## Local Development

### 1. Open the repository

```bash
cd ~/jalsetu
```

### 2. Activate the Python virtual environment

```bash
source .venv/bin/activate
```

### 3. Install backend dependencies

```bash
python -m pip install -r backend/requirements.txt
```

### 4. Configure the backend

Configure the backend environment file at `backend/.env` with the database connection and a strong, private JWT signing secret.

Required settings include:

- `DATABASE_URL` — PostgreSQL connection URL
- `JWT_SECRET_KEY` — a strong secret used to sign authentication tokens

Use the existing local database configuration if you have already initialized PostgreSQL. Do not commit `.env` files or real secrets to Git.

### 5. Start the backend

In a terminal with the virtual environment activated:

```bash
cd ~/jalsetu
source .venv/bin/activate
python -m backend.app
```

The local API is configured to use port `5000`.

Check the health endpoint:

```text
http://localhost:5000/api/health
```

A successful response should indicate that the application and database are healthy.

### 6. Configure the frontend API URL

Open `frontend/config.js`.

The local development default is:

```javascript
window.JALSETU_API_BASE =
  window.JALSETU_API_BASE ||
  "http://localhost:5000";
```

For local development, keep the URL as shown. For deployment, configure the frontend to use the actual HTTPS API origin.

### 7. Start the frontend

Open a second terminal:

```bash
cd ~/jalsetu
python3 -m http.server 5173 --bind 0.0.0.0 --directory frontend
```

Open the application at:

```text
http://localhost:5173/home.html
```

The frontend development server is not a production hosting server.

## API Overview

The backend includes the following application routes:

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api` | API information |
| GET | `/api/health` | Application and database health |
| POST | `/api/auth/register` | Register a user |
| POST | `/api/auth/login` | Authenticate a user |
| GET | `/api/auth/me` | Retrieve the authenticated user's information |
| GET | `/api/complaints` | Retrieve complaints for the authenticated user |
| POST | `/api/complaints` | Submit a complaint |
| GET | `/api/complaints/<reference>` | Track an owned complaint by reference |
| GET | `/api/complaints/<reference>/image` | Retrieve an authorized complaint image |
| POST | `/api/chat` | Get rule-based chatbot guidance |

Administrative routes require appropriate authentication and authorization. Consult `backend/app.py` for their exact methods and paths.

Protected endpoints require valid authentication where configured. Do not assume every endpoint is public.

## Security and Data Notes

- Keep backend environment files and signing secrets private.
- Do not commit `.venv`, credentials, or private database backups.
- Uploaded complaint images should be handled through the validated backend upload flow.
- Local uploads are stored on the backend filesystem; production deployment must provide suitable persistent storage.
- Configure production CORS origins, HTTPS, database access, and secret management before exposing the application publicly.
- Do not use real user data in public demonstrations without appropriate permission.

## Deployment Status

This repository documents the local development setup. A working public deployment requires separately configured frontend hosting, backend hosting, a reachable PostgreSQL database, correct environment variables, and persistent image storage.

A successful local run does not by itself mean the application is deployed publicly.

## Project Team

- Sakshant Santosh Gire — B-06, CSE
- Pranitee Chandrakant Jadhav — B-20, CSE
- Shrutika Shrikant Bagal — B-71, CSE

## Project Languages

English, Hindi, and Marathi are intended project languages. Verify that each language is fully supported by the current interface before describing multilingual support as complete.
