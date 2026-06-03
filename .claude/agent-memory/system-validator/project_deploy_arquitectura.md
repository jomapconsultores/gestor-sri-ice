---
name: project-deploy-arquitectura
description: Arquitectura de deployment del Gestor SRI ICE — Render (web service) + Supabase (PostgreSQL), git push a origin/master dispara deploy
metadata:
  type: project
---

El Gestor SRI ICE se despliega en **Render** como web service, con base de datos **Supabase (PostgreSQL)**. El deploy se dispara con `git push` a `origin/master` (auto-deploy de Render conectado al repo GitHub `jomapconsultores/gestor-sri-ice`).

**Why:** Es una app Flask monolítica con gunicorn; Render hace build+deploy automático al detectar push en master.

**How to apply:** Antes de un deploy, el push a master ES el deploy. No hay rama de staging separada. Validar TODO antes del push porque va directo a producción.

Archivos clave de deploy:
- `render.yaml` — define el web service, `buildCommand: pip install -r requirements.txt`, `startCommand: gunicorn app:app --bind 0.0.0.0:$PORT --workers 2 --timeout 120`. PYTHON_VERSION=3.12.0.
- `Procfile` — mismo comando gunicorn (redundante con render.yaml).
- En `render.yaml`, `DATABASE_URL` y `BASE_URL` tienen `sync: false` → se configuran manualmente en el dashboard de Render, NO en el repo. `SECRET_KEY` usa `generateValue: true`.

Importante: `config.py` convierte `postgres://` y `postgresql://` → `postgresql+psycopg://` (usa psycopg 3, `psycopg[binary]==3.2.6`). El `DATABASE_URL` de producción debe ser el de Supabase.

Migraciones: hay SQL en `migrations/` (0001_create_saldo_iva_mes.sql, 0002_create_auditoria_cambios.sql) PERO `app.py::_migrar_bd()` aplica migraciones de columnas idempotentes a import-time vía ALTER TABLE ... IF NOT EXISTS (en PG). `db.create_all()` crea tablas faltantes. Ver [[project-test-suite]].
