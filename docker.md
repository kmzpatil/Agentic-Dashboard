# Docker + AWS (EC2) Deployment Guide

This guide assumes you are deploying on a fresh Linux VM (AWS EC2) and want a single Postgres container with the API and web UI. The only required per-machine change is to create a `.env` file from `.env.example`.

## 1) Server prerequisites (AWS EC2)
- Ubuntu 22.04 or Amazon Linux 2023 works well.
- Open the following inbound ports in your Security Group:
  - 22 (SSH)
  - 8080 (web UI)
  - 4000 (API)

## 2) Install Docker and Compose
### Ubuntu 22.04
```bash
sudo apt-get update
sudo apt-get install -y ca-certificates curl gnupg
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo $VERSION_CODENAME) stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

sudo usermod -aG docker $USER
newgrp docker
```

### Amazon Linux 2023
```bash
sudo dnf update -y
sudo dnf install -y docker
sudo systemctl enable docker
sudo systemctl start docker
sudo usermod -aG docker $USER
newgrp docker
```

## 3) Clone the repo
```bash
git clone <your-repo-url> gcdata
cd gcdata
```

## 4) Create the environment file
```bash
cp .env.example .env
```
Update these fields in `.env`:
- `POSTGRES_PASSWORD` (required)
- `PGPASSWORD` (must match `POSTGRES_PASSWORD`)
- `JWT_SECRET`
- `AZURE_OPENAI_ENDPOINT` and `AZURE_OPENAI_API_KEY` (if using Azure OpenAI)

Notes:
- For Docker, the API connects to Postgres using `PGHOST=db` and `POSTGRES_HOST=db` by default.
- A single DB name is used everywhere via `PGDATABASE` and `POSTGRES_DB`.

## 5) Build and run the stack
```bash
docker compose up -d --build
```

## 6) Initialize the database (first time only)
```bash
docker compose run --rm api python /app/database/bootstrap_postgres.py
docker compose run --rm api python -m backend.db.seed_auth_users
```

## 7) Access the app
- Web UI: http://<YOUR_EC2_PUBLIC_IP>:8080
- API: http://<YOUR_EC2_PUBLIC_IP>:4000/api

## 8) Stop and restart
```bash
docker compose down
```

## Optional: Use an external Postgres
If you want Postgres outside Docker (e.g., RDS), set these in `.env`:
```
PGHOST=<rds-endpoint>
PGPORT=5432
PGUSER=<user>
PGPASSWORD=<password>
PGDATABASE=<db_name>

POSTGRES_HOST=<rds-endpoint>
POSTGRES_PORT=5432
POSTGRES_USER=<user>
POSTGRES_PASSWORD=<password>
POSTGRES_DB=<db_name>
```
Then remove or comment out the `db` service in `docker-compose.yml`.

## Troubleshooting
- If the API container cannot connect to the DB, confirm `POSTGRES_PASSWORD` and `PGPASSWORD` match.
- If the UI cannot reach the API, rebuild the web image after changing `VITE_API_BASE_URL`.
- On AWS, verify the Security Group allows inbound access to 8080 and 4000.
