# Loan EMI Calculator

Node.js/Express + jQuery/Bootstrap, storing every calculation in MongoDB.

## Endpoints
- `POST /api/emi` body `{ "P": 500000, "rate": 12, "n": 24 }` returns EMI, total payment, total interest, serving pod name and IP
- `GET /api/history` last 10 calculations, newest first
- `GET /health` 200 only if MongoDB is reachable (readiness probe)

## Configuration
| Variable | Purpose | Default |
|---|---|---|
| `MONGO_URL` | MongoDB connection string (required) | none |
| `DB_NAME` | database name | `emiapp` |
| `PORT` | HTTP port | `3000` |
| `HOSTNAME` | pod name (set by Kubernetes) | OS hostname |

## Run locally
    docker compose up --build
    # open http://localhost:3000

Or without Docker for the app:

    docker run -d -p 27017:27017 --name mongo mongo:7
    npm install
    MONGO_URL=mongodb://localhost:27017 npm start

## Quick API test
    curl -X POST localhost:3000/api/emi -H "Content-Type: application/json" -d '{"P":500000,"rate":12,"n":24}'
    curl localhost:3000/api/history
    curl -i localhost:3000/health
