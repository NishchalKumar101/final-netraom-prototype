# Adminer login (Postgres)

## One-click URL

http://localhost:8081/?pgsql=postgres&username=student&db=cspm_demo

Password: **`student`** (read-only) or **`demo`** / **`demo`** (full).

This compose stack mounts **`login-postgres`** plugin: the login form uses **PostgreSQL only** (no MySQL dropdown). Server is fixed to **`postgres`** on the Docker network.

## If you still see "Connection refused"

1. **Clear cookies** for `localhost:8081` (especially `adminer_permanent`). An old cookie can force **MySQL** with server `postgres`, which always fails.
2. Do **not** bookmark `?server=postgres` — that is the **MySQL** URL. Use **`?pgsql=postgres`** instead.
3. Ensure Postgres is running: `docker compose up -d postgres adminer`

## psql from your Mac (not Adminer)

```bash
psql "postgresql://student:student@localhost:5433/cspm_demo"
```

Port **5433** is for host clients only. Adminer inside Docker uses **`postgres:5432`**.
