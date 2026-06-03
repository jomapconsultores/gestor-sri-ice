# System Validator — Memory Index

- [Deploy: Arquitectura y procedimiento](project_deploy_arquitectura.md) — Render + Supabase, render.yaml, Procfile, gunicorn, DATABASE_URL inyectado en prod
- [Test suite: ejecución y gotcha import-time](project_test_suite.md) — 109 tests, create_app() corre db.create_all() a import-time y rompe colección si sqlite local no es accesible
- [Config: validación de entorno](project_config_env.md) — Config exige MISTRAL_API_KEY y CODESTRAL_API_KEY o lanza ValueError; .env local usa sqlite, prod usa Supabase
