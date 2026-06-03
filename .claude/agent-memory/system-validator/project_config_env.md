---
name: project-config-env
description: config.py exige MISTRAL_API_KEY y CODESTRAL_API_KEY (ValueError si faltan); .env local usa sqlite, producción usa Supabase
metadata:
  type: project
---

`config.py` (clase `Config`) **lanza ValueError a import-time** si faltan `MISTRAL_API_KEY` o `CODESTRAL_API_KEY` (líneas 51-54). Esto significa que cualquier import de `config`/`app` requiere esas dos claves en el entorno, incluso para correr tests.

**Why:** Hard requirement de las integraciones IA (Mistral/Codestral) para procesamiento de PDFs y conciliación bancaria.

**How to apply:** En Render esas dos keys deben estar configuradas como env vars o el boot falla. Al validar pre-deploy, confirmar que ambas existan en el dashboard de Render.

El `.env` local (git-ignored, correctamente en .gitignore líneas 24-28) contiene todas las keys necesarias: DATABASE_URL, SECRET_KEY, MISTRAL_API_KEY, CODESTRAL_API_KEY, más config tributaria (IVA_RATE, etc.), MAIL_*, SRI_BASE_URL=https://srienlinea.sri.gob.ec, FLASK_ENV=production, DEBUG=False.

Importante: el `DATABASE_URL` del `.env` local apunta a **sqlite** (`sqlite:///instance/sistema_ice.db`), NO a Supabase. El `DATABASE_URL` de Supabase/PostgreSQL solo vive en el dashboard de Render (`sync: false` en render.yaml). No confundir: validar el .env local NO valida la DB de producción. Ver [[project-deploy-arquitectura]] y [[project-test-suite]].
