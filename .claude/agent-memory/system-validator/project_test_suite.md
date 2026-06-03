---
name: project-test-suite
description: Suite de tests (109 total) y gotcha — create_app() ejecuta db.create_all() a import-time, rompiendo la colección de pytest si la sqlite local no es accesible
metadata:
  type: project
---

La suite tiene **109 tests** en `tests/`: test_endpoints_reportes.py (26), test_validaciones_sri.py (26), test_reportes_sri.py (25), test_iva_tarifas.py (17), test_gastos_limits.py (15). No hay conftest.py.

**Gotcha crítico (causa raíz de fallos de colección):** `app.py` línea 228 ejecuta `app = create_app()` a nivel de módulo, y `create_app()` (línea 160-163) corre `db.create_all()`, `_migrar_bd()` y `_crear_admin_inicial()` dentro de un `app_context()` usando el `SQLALCHEMY_DATABASE_URI` de `Config` (que toma `DATABASE_URL` del .env = `sqlite:///instance/sistema_ice.db`).

Los tests hacen `from app import create_app`, lo que dispara ese `create_app()` de import-time ANTES de que `setUp()` cambie el URI a `sqlite:///:memory:`. Si el sqlite local no es accesible desde el contexto de pytest, los 51 tests que importan `app` (endpoints_reportes + reportes_sri) fallan en **colección** con `sqlite3.OperationalError: unable to open database file`. Los otros 58 tests (validaciones, iva_tarifas, gastos_limits) NO importan `app` y pasan siempre.

**Why:** El side-effect de import-time (`app = create_app()` + `db.create_all()`) acopla la importación del módulo a una DB real.

**How to apply:** Para que pasen los 109/109 localmente hay que asegurar que `DATABASE_URL` apunte a una DB accesible en colección, o refactorizar `app.py` para no instanciar/crear tablas a import-time (mover `db.create_all()` fuera de create_app o detrás de un guard `TESTING`). En producción NO afecta porque Render usa Supabase (PostgreSQL) accesible. Ver [[project-config-env]] y [[project-deploy-arquitectura]].
