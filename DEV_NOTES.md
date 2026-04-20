[Fecha] 03/30/2026

## Problema
JWT permite acceso a tokens (refresh/access) de tipo incorrecto según endpoint.

## Causa
Mala configuración inicial, ausencia de validación antes del endpoint.

## Solución
- Se agregó un endpoint para refresh tokens.
- Se agregaron validaciones en `auth.py` para el método `create_user()`.
- Se agregó una validación en endpoint `/me` para evitar acceso con refresh tokens.

## Nota
Refresh Token sigue permitiendo reusarse, corregir esto a futuro.

---

[Fecha] 03/31/2026

## Problema
Importaciones rotas en `routes/users.py` y falta total de endpoint + lógica para almacenar los refresh tokens hasheados en la base de datos (`store_refresh_token`, `verify_refresh_token` y `UserToken`).

## Causa
- Imports incorrectos/duplicados y referencias a funciones que no existían en `core/auth.py`.
- El endpoint `/refresh` existía solo de nombre pero no tenía la lógica de validación ni persistencia del hash del refresh token.
- No se guardaba ningún refresh token en la tabla `user_tokens` → no había revocación ni control de sesión.

## Solución
- Se corrigieron todas las importaciones en `app/routes/users.py`.
- Se completó y limpió `app/core/auth.py` con:
  - Modelo `UserToken`.
  - Funciones `store_refresh_token` y `verify_refresh_token`.
  - `decode_refresh_token` centralizado.
  - Creación segura de access y refresh tokens.
- Se implementó correctamente el endpoint `/users/refresh` con validación de hash en BD.
- Ahora el flujo completo funciona: login → guarda hash del refresh + devuelve ambos tokens.

## Nota de seguridad (pendiente)
Refresh Token todavía permite reutilización (reuse attack). Próxima mejora: implementar Refresh Token Rotation (invalidar el usado y emitir uno nuevo en cada `/refresh`).

---

[Fecha] 03/31/2026

## Problema
Falta de protección en rutas y dependencia `get_current_user` no implementada.

## Causa
- No existía `get_current_user()` para extraer usuario desde access token.
- Faltaba `get_db()` en `database.py` para inyectar sesiones.
- Endpoints no tenían autenticación.

## Solución
- Se creó `get_db()` en `core/database.py`.
- Se creó `get_current_user()` en `core/dependencies.py` con decode de access token y búsqueda en BD.
- Se protegió endpoint `/users/me` con `Depends(get_current_user)`.

## Estado actual
- `/me` requiere token válido.
- 401 si token falta, expira o es inválido.
- Dependencia lista para proteger más endpoints.

---

[Fecha] 04/01/2026

## Problema
Alembic no podía generar ni aplicar migraciones por incompatibilidad con el motor asíncrono de SQLAlchemy (error `MissingGreenlet`).

## Causa
- El proyecto usa `create_async_engine` con `asyncpg`.
- Alembic, por defecto, solo funciona con motores síncronos.

## Solución
- Se modificó `migrations/env.py` para que Alembic utilice un motor síncrono (`create_engine` con `psycopg2`) solo durante las migraciones.
- Se generó la migración automática con `alembic revision --autogenerate -m "fix created_at timezone"`.
- Se aplicó la migración con `alembic upgrade head`, actualizando la columna `created_at` de la tabla `user_tokens` a `TIMESTAMP WITH TIME ZONE` con valor por defecto `now()`.

## Resultado
- La base de datos está sincronizada con los modelos.
- La aplicación sigue funcionando con `asyncpg` sin cambios.
- El flujo de migraciones ahora es compatible con el proyecto.

---

[Fecha] 07/04/2026

## Problema
Los tests de integración fallaban por múltiples razones: falta de configuración de pytest-asyncio, errores de conexión a PostgreSQL (host `postgres_db` no resuelto desde el host), problemas con variables de entorno no cargadas, y falta de creación de tablas en la base de datos de pruebas.

## Causa
- El archivo `tests/conftest.py` no cargaba `load_dotenv()` antes de importar `app.main`, causando errores de validación en `Settings`.
- Se usaba `@pytest.fixture` en lugar de `@pytest_asyncio.fixture` para fixtures asíncronas.
- El cliente HTTP con `httpx.AsyncClient` necesitaba `ASGITransport(app=app)` para probar FastAPI.
- La base de datos de pruebas apuntaba a PostgreSQL con nombre de host `postgres_db` (solo válido dentro de Docker), generando errores de resolución de DNS.
- Se intentó usar Alembic para crear las tablas de prueba, pero las migraciones no se generaban correctamente por falta de importación de modelos en `env.py` y conflictos de permisos.
- Además, se presentó un error de asyncio `Future attached to a different loop` al usar fixtures con `scope="session"`.

## Solución
- Se reordenó `conftest.py` para definir variables de entorno (`os.environ`) **antes** de cualquier importación de la app, eliminando la dependencia del archivo `.env` para los tests.
- Se cambió a `@pytest_asyncio.fixture` para la fixture `client`.
- Se reemplazó `httpx.AsyncClient(app=app)` por `ASGITransport(app=app)`.
- Se optó por usar **SQLite en memoria** (`sqlite+aiosqlite:///:memory:`) como base de datos de pruebas, eliminando la necesidad de PostgreSQL y los problemas de red.
- Se agregó `aiosqlite` como dependencia de desarrollo.
- Se configuró una fixture `setup_db` con `scope="session"` que crea las tablas una sola vez, y una fixture `clean_db` con `autouse=True` que limpia los datos entre tests (sin destruir las tablas).
- Se corrigió el error del loop asíncrono usando un único engine compartido y evitando `scope="function"` con recreación de tablas.
- Se completaron los tests unitarios e integración para los endpoints de autenticación (registro, login, refresh, logout, perfil, flujo completo).
- Se ajustaron los headers de autorización en los tests para usar `Authorization: Bearer {token}` con el espacio correcto.

## Nota
Los tests ahora pasan completamente (10 tests exitosos) y la suite se ejecuta en menos de 3 segundos. El uso de SQLite en memoria para pruebas es una práctica común y acelera el desarrollo, aunque se recomienda mantener un entorno de integración con PostgreSQL para validar características específicas del motor. Los tests cubren los flujos principales de autenticación y servirán como red de seguridad para futuros cambios.

---

[Fecha] 08/04/2026

## Problema
La aplicación manejaba sesión única (un solo dispositivo activo por usuario), lo cual no es el comportamiento más común en aplicaciones web modernas donde los usuarios esperan estar conectados desde múltiples dispositivos (web, móvil, tablet) simultáneamente.

## Causa
- La función `store_refresh_token` en `app/core/auth.py` realizaba un `DELETE` de todos los refresh tokens anteriores del usuario antes de insertar uno nuevo, limitando la sesión a un solo token activo.
- No se almacenaba información del dispositivo (nombre, IP) ni se registraba el último uso de cada sesión.
- No existían endpoints para listar ni revocar sesiones activas remotamente.
- Además, el test `test_refresh_token` fallaba porque el nuevo access token generado era idéntico al original (falta de unicidad en el payload del JWT).

## Solución
- Se modificó la tabla `user_tokens` agregando las columnas:
  - `device_name` (VARCHAR 100) – nombre del dispositivo (ej. "Chrome en Windows").
  - `ip_address` (VARCHAR 45) – dirección IP del cliente.
  - `last_used_at` (TIMESTAMP WITH TIME ZONE) – última vez que se usó el refresh token.
- Se cambió `store_refresh_token` para **insertar** un nuevo token sin eliminar los anteriores, permitiendo múltiples tokens activos por usuario.
- Se capturó en el endpoint `/login` el `User-Agent` y la IP del cliente (usando `fastapi.Request`) y se almacenan junto con el refresh token.
- Se agregaron dos nuevos endpoints protegidos:
  - `GET /users/sessions` – lista todas las sesiones activas del usuario autenticado.
  - `DELETE /users/sessions/{session_id}` – revoca una sesión específica (logout remoto).
- Se mejoró `verify_refresh_token` para que solo considere tokens no revocados (`revoked == False`).
- Para garantizar unicidad de cada token (y que el test `test_refresh_token` pase), se añadió el campo `jti` (JWT ID) con un UUID aleatorio en el payload de access y refresh tokens.
- Se corrigió el test `test_refresh_token` (que ahora pasa sin necesidad de `sleep`).

## Estado actual
- La API permite múltiples sesiones simultáneas por usuario.
- Cada login genera un nuevo refresh token sin invalidar los anteriores.
- El logout revoca únicamente el token utilizado.
- El usuario puede listar y cerrar sesiones remotamente desde otros dispositivos.
- Todos los tests (10) pasan exitosamente.
- La seguridad mejora gracias al `jti` único por token y la posibilidad de revocación individual.

## Pendiente / Mejoras futuras
- Implementar límite máximo de sesiones activas por usuario (ej. 5 dispositivos).
- Añadir rotación de refresh tokens (emitir uno nuevo en cada `/refresh` y revocar el usado).
- Notificar al usuario por email cuando se inicia una nueva sesión en un dispositivo desconocido.

---

[Fecha] 08/04/2026 (2)

## Problema
La aplicación carecía de un sistema de logging estructurado que permitiera rastrear peticiones, depurar errores y auditar eventos de autenticación en producción.

## Causa
- No se registraban eventos de entrada/salida de los endpoints.
- No existía un identificador de correlación (correlation ID) para seguir una petición a través de los logs.
- Los errores y advertencias no quedaban registrados sistemáticamente.

## Solución
- Se implementó un sistema de logging usando el módulo `logging` estándar de Python.
- Se agregó el middleware `CorrelationIdMiddleware` que genera/extrae un `X-Correlation-ID` (UUID) y lo propaga mediante `contextvars`.
- Se configuró un `CorrelationIdFilter` para añadir el correlation ID a cada registro de log.
- Se añadieron logs informativos (`info`) y de advertencia (`warning`) en todos los endpoints de autenticación: login, logout, refresh, create_user, get_me.
- Se registran intentos, éxitos y fallos (con detalles como email, user_id, causa del error).
- La salida de logs se envía a la consola (stdout) con formato: `timestamp - name - level - [correlation_id] - message`.

## Resultado
- Ahora es posible rastrear una petición completa desde que entra hasta que sale gracias al correlation ID.
- Los logs permiten monitorear la salud de la API y depurar problemas en producción.
- Todos los tests (10) siguen pasando sin cambios adicionales.
- La aplicación está lista para ser desplegada con trazabilidad.

## Nota
El nivel de log se puede cambiar entre `INFO` y `DEBUG` mediante la variable de entorno `LOG_LEVEL` (pendiente de implementar). Por ahora está fijo en `INFO` en `main.py`.

---

[Fecha] 09/04/2026

## Problema
La API no contaba con un endpoint de monitoreo que permitiera verificar su estado y el de la base de datos, tanto en desarrollo como en producción.

## Causa
- No existía un endpoint dedicado a health check.
- No se validaba la conectividad con la base de datos desde la API.

## Solución
- Se creó el endpoint `GET /health` en `app/routes/health.py`.
- El endpoint ejecuta una consulta simple `SELECT 1` a la base de datos.
- Retorna `200 OK` con `{"status":"ok","database":"connected"}` si la base responde.
- Si hay error, retorna `503 Service Unavailable` con `{"status":"degraded","database":"disconnected"}`.
- Se registró el router en `app/main.py`.
- Se agregaron logs de error en caso de falla.

## Resultado
- Ahora se puede monitorear la salud de la API y la base de datos mediante `GET /health`.
- Útil para orquestadores (Docker, Kubernetes) y servicios de monitoreo.
- Todos los tests siguen pasando.

---

[Fecha] 09/04/2026

## Problema
El despliegue en Railway fallaba porque la variable `DATABASE_URL` usaba el driver síncrono `postgresql://`, incompatible con el uso de `asyncpg` en SQLAlchemy asíncrono.

## Causa
Railway inyecta por defecto una URL con `postgresql://` (sin `+asyncpg`). La aplicación esperaba un driver asíncrono para `create_async_engine`.

## Solución
- Se modificó manualmente la variable `DATABASE_URL` en el servicio de API de Railway, cambiando `postgresql://` por `postgresql+asyncpg://`.
- Alternativamente, se agregó un validador en `app/core/config.py` que convierte automáticamente la URL al formato asíncrono si es necesario.
- Se redeployó la aplicación.

## Resultado
- La aplicación arranca correctamente en Railway.
- Las tablas se crean automáticamente mediante `Base.metadata.create_all`.
- El endpoint `/health` responde `200 OK`.
- La documentación Swagger está disponible en `/docs`.

---

[Fecha] 10/04/2026

## Problema
Los endpoints `/login`, `/refresh` y `/logout` usaban mecanismos confusos para el usuario:
- `/login` utilizaba `OAuth2PasswordRequestForm`, que mostraba campos irrelevantes en Swagger (`grant_type`, `scope`, `client_id`, `client_secret`).
- `/refresh` y `/logout` esperaban el token en el header `Authorization`, lo que obligaba a usar el botón "Authorize" en Swagger y dificultaba las pruebas manuales.
- Los tests enviaban los datos en formato `data=` (form) o en headers, no en JSON.

## Causa
- Se había adoptado el estándar OAuth2 password flow sin necesidad real.
- No se diseñaron esquemas Pydantic explícitos para la entrada de estos endpoints.

## Solución
- Se crearon los esquemas `LoginRequest`, `RefreshRequest` y `LogoutRequest` en `app/schemas/user.py`.
- Se modificaron los endpoints para recibir JSON en lugar de form data o headers.
- Se eliminaron las dependencias `OAuth2PasswordRequestForm`, `OAuth2PasswordBearer` y `oauth2_scheme` (ya no se usan).
- Se mejoraron los logs en `/logout` (se agrega verificación opcional del token y advertencias).
- Se actualizaron todos los tests en `tests/integration/test_users.py` para usar `json=` en lugar de `data=` o headers.
- Se corrigió `test_refresh_token` para que use el usuario correcto.

## Resultado
- Swagger ahora muestra campos limpios y editables para cada endpoint.
- La API es más intuitiva para desarrolladores externos.
- Los tests pasan correctamente (10/10).
- El código es más mantenible al eliminar dependencias innecesarias.

## Nota
Se mantiene la lógica de negocio original (generación de tokens, almacenamiento de hashes, revocación, multi‑sesión). Solo cambió la interfaz de entrada.

---

[Fecha] 11/04/2026

## Problema
Se requiere evolucionar la API hacia un sistema de pagos headless (Plug & Play Payment Links). Para ello es necesario añadir Redis, Celery, modelos de pago, endpoints básicos y asegurar que el despliegue en Railway funcione correctamente.

## Causa
- La aplicación no tenía soporte para tareas asíncronas (emails, webhooks).
- Faltaban las tablas `payment_links`, `payments`, `events`.
- El despliegue en Railway fallaba por falta de los esquemas `LoginRequest`, `RefreshRequest`, `LogoutRequest` (añadidos en el paso anterior pero no subidos correctamente).
- El modelo `PaymentLink` usaba el nombre `metadata`, que está reservado por SQLAlchemy.

## Solución

### 1. Configuración de Redis y Celery
- Se agregaron las dependencias `redis`, `celery`, `stripe` a `pyproject.toml`.
- Se configuró Redis en `docker-compose.yml` (puerto 6379).
- Se creó `app/workers/celery_app.py` y `app/workers/tasks.py` con una tarea de ejemplo.
- Se añadió `redis_url` a `Settings` en `config.py` (sin valor por defecto, obligatorio desde `.env`).
- Se probó el worker localmente con `celery -A app.workers.celery_app worker`.

### 2. Modelos de pago y eventos
- Se crearon `app/models/payment_link.py`, `payment.py`, `event.py` usando SQLAlchemy 2.0 (`Mapped`, `mapped_column`).
- Se reemplazó `metadata` por `extra_data` para evitar conflicto con palabra reservada.
- Se generó y aplicó la migración Alembic (`add_payment_tables_fixed`).

### 3. Esquemas Pydantic y endpoints
- Se creó `app/schemas/payment_link.py` con `PaymentLinkCreate` y `PaymentLinkResponse`.
- Se creó `app/routes/payment_links.py` con el endpoint `POST /payment-links` (protegido con JWT).
- Se registró el router en `app/main.py`.
- Se corrigió el uso de `data.metadata` por `data.extra_data` en el endpoint.

### 4. Corrección del despliegue en Railway
- Se verificó que los esquemas `LoginRequest`, `RefreshRequest`, `LogoutRequest` estuvieran en `app/schemas/user.py` (faltaban en el repositorio remoto).
- Se hizo push de los cambios y Railway redeployó correctamente.
- Se actualizó la variable `REDIS_URL` en Railway para conectar con el servicio Redis añadido.

### 5. Prueba de creación de payment link
- Se autenticó un usuario (`cafe@gato.com`) y se obtuvo `access_token`.
- Se llamó a `POST /payment-links` con el token y se recibió respuesta exitosa:
  ```json
  {"id":1,"title":"Consultoría","amount":15000.0,"currency":"CLP","type":"fixed","status":"active","public_id":"091f598d","created_at":"2026-04-11T14:52:12.428287Z","extra_data":{}}

## Resultado

- Redis y Celery operativos en desarrollo local (y listos para producción).

- Modelos de pago creados y migrados.

- Endpoint de creación de payment links funcionando con autenticación JWT.

- Despliegue en Railway restablecido y funcionando.

- El sistema está preparado para la siguiente fase: integración con pasarelas de pago (Stripe) y webhooks.

## Nota

- El worker de Celery aún no se despliega en Railway; se añadirá como un servicio separado en el futuro.

- Los endpoints de listado, detalle y página pública (/pay/{public_id}) se implementarán en la próxima iteración.

---

[Fecha] 11/04/2026 (2)

## Problema
Se necesita integrar una pasarela de pagos real (Stripe) para que los payment links creados permitan a los compradores pagar con tarjeta. Además, se requiere manejar webhooks para actualizar el estado de los pagos y emitir eventos internos.

## Causa
- No existía integración con Stripe.
- Los endpoints de payment links solo almacenaban datos, no generaban sesiones de pago.
- No se gestionaban eventos de éxito/fracaso de pagos.

## Solución

### 1. Integración de Stripe
- Se añadieron las variables de entorno `STRIPE_SECRET_KEY` y `STRIPE_PUBLISHABLE_KEY` (en `.env` y en Railway).
- Se instaló la librería `stripe` (ya estaba).
- Se creó el endpoint público `GET /pay/{public_id}` que:
  - Busca el `PaymentLink` por `public_id`.
  - Crea una sesión de Stripe Checkout con el monto, título y moneda.
  - Redirige al usuario a `session.url` (devuelve la URL en JSON).
- Se registró el router en `app/main.py`.

### 2. Webhook de Stripe
- Se creó el endpoint `POST /webhooks/stripe` que:
  - Verifica la firma del webhook usando la clave `STRIPE_WEBHOOK_SECRET`.
  - Escucha el evento `checkout.session.completed`.
  - Actualiza la tabla `payments` (crea un registro si no existe, o lo marca como `succeeded`).
  - Emite un evento interno (se guarda en la tabla `events` con tipo `payment.succeeded`).

### 3. Modelo `Payment` y tabla `payments`
- Se creó el modelo `Payment` en `app/models/payment.py` con los campos: `id`, `payment_link_id`, `provider`, `provider_payment_id`, `amount`, `currency`, `status`, `metadata`, `created_at`, `updated_at`.
- Se generó la migración correspondiente y se aplicó.

### 4. Endpoints adicionales de payment links
- Se añadió `GET /payment-links` para listar los links del usuario autenticado.
- Se mejoró la respuesta de creación incluyendo el `public_id` generado.

### 5. Despliegue en Railway
- Se agregó el servicio Redis a Railway (necesario para Celery en el futuro).
- Se configuraron las variables de entorno `REDIS_URL`, `STRIPE_SECRET_KEY`, `STRIPE_PUBLISHABLE_KEY`, `STRIPE_WEBHOOK_SECRET`.
- Se redeployó la aplicación; todos los endpoints funcionan correctamente en producción.

## Resultado
- El sistema ya permite crear payment links y procesar pagos reales con Stripe (modo test).
- Los pagos exitosos actualizan el estado en la base de datos y generan eventos.
- La API está desplegada en Railway y accesible públicamente.
- El flujo completo es: crear link → compartir URL pública → cliente paga → webhook actualiza estado.

## Próximos pasos
- Implementar workers de Celery para procesar eventos (enviar emails, notificaciones).
- Añadir soporte para MercadoPago.
- Construir un SDK oficial (Python, JavaScript).

---
[Fecha] 11/04/2026 (3)

## Problema
Se requiere integrar Stripe como pasarela de pago para los payment links, permitiendo a los compradores pagar con tarjeta y actualizar el estado del pago mediante webhooks.

## Causa
- No existía integración con Stripe.
- Los endpoints de payment links solo almacenaban datos, no generaban sesiones de pago.
- No se gestionaban eventos de éxito/fracaso de pagos.

## Solución

### 1. Dependencias y configuración
- Se añadió `stripe` al proyecto (`poetry add stripe`).
- Se configuraron las variables de entorno: `STRIPE_SECRET_KEY`, `STRIPE_PUBLISHABLE_KEY`, `STRIPE_WEBHOOK_SECRET`.
- Se instaló y configuró Stripe CLI para desarrollo local (`stripe listen --forward-to localhost:8000/webhooks/stripe`).

### 2. Endpoint público de pago
- Se creó `GET /pay/{public_id}` en `app/routes/payment_links.py`.
- Busca el `PaymentLink` por `public_id` y crea una sesión de Stripe Checkout.
- Devuelve la URL de Stripe para que el comprador realice el pago.

### 3. Webhook de Stripe
- Se creó el endpoint `POST /webhooks/stripe` en `app/routes/webhooks.py`.
- Verifica la firma del webhook con `stripe.Webhook.construct_event`.
- Escucha eventos `checkout.session.completed` y `checkout.session.expired`.
- Actualiza la tabla `payments` (crea o actualiza registro) y emite eventos internos en la tabla `events`.

### 4. Prueba local exitosa
- Se creó un usuario, se generó un payment link, se obtuvo la URL de Stripe Checkout.
- Se pagó con tarjeta de prueba `4242 4242 4242 4242`.
- El webhook local (Stripe CLI) recibió el evento y la API actualizó el estado del pago en la base de datos.

## Resultado
- El sistema ya permite procesar pagos reales con Stripe en modo test.
- El flujo completo es: crear link → compartir URL → cliente paga → webhook actualiza estado.
- La API está lista para desplegar en Railway con el webhook de producción configurado en Stripe Dashboard.

## Nota
- Para producción, se debe crear un webhook aparte en Stripe Dashboard con la URL pública de Railway y usar su propio secreto (`STRIPE_WEBHOOK_SECRET`).
- La CLI de Stripe se usa solo para desarrollo local.

---

[Fecha] 13/04/2026

## Problema
Se necesita exponer los pagos realizados por los usuarios a través de la API, para que puedan consultar su historial y el detalle de cada transacción.

## Causa
- No existían endpoints para listar pagos ni para ver el detalle de un pago específico.
- Los endpoints de listado de payment links no tenían paginación.

## Solución
- Se creó el esquema `PaymentResponse` en `app/schemas/payment.py`.
- Se implementó el endpoint `GET /payment-links/payments` que lista todos los pagos del usuario autenticado (con paginación `skip`/`limit` y orden descendente por fecha).
- Se implementó el endpoint `GET /payment-links/payments/{payment_id}` que devuelve el detalle de un pago específico (verificando que pertenezca al usuario).
- Se añadió paginación a `GET /payment-links` (parámetros `skip` y `limit`).
- Se corrigió la importación de `Optional` (debe venir de `typing`, no de `pydantic`).

## Resultado
- Los usuarios pueden consultar su historial de pagos y el detalle de cada transacción.
- Los endpoints de listado ahora soportan paginación, mejorando el rendimiento y la usabilidad.
- La API está más completa para integrarse con frontends o servicios externos.

## Nota
- Los nuevos endpoints requieren autenticación (access token).
- La paginación usa `skip` (registros a saltar) y `limit` (máximo de registros por página).

---

[Fecha] 18/04/2026

## Problema
El botón "Authorize" de Swagger UI (documentación interactiva en `/docs`) fallaba con error `422 Unprocessable Content` al intentar autenticar. El formulario de autorización mostraba campos de usuario/contraseña (OAuth2 password flow) y al enviarlos, Swagger realizaba una petición `POST /users/login` con `Content-Type: application/x-www-form-urlencoded`, pero el endpoint espera JSON, causando el error.

## Causa
- La dependencia `OAuth2PasswordBearer(tokenUrl="/users/login")` en `app/core/dependencies.py` indicaba a FastAPI que el esquema de seguridad era OAuth2 con password flow.
- FastAPI generaba el OpenAPI con `securitySchemes` de tipo `oauth2`, lo que obligaba a Swagger UI a mostrar un formulario de usuario/contraseña y a enviar los datos en formato form-urlencoded.
- El endpoint real `/users/login` solo acepta JSON, no form data, produciendo el error 422.

## Solución

### 1. Cambiar la dependencia de autenticación
- Se reemplazó `OAuth2PasswordBearer` por `HTTPBearer` en `app/core/dependencies.py`.
- Se modificó `get_current_user` para recibir `HTTPAuthorizationCredentials` y extraer el token manualmente.
- Se añadió manejo del caso `credentials is None` para retornar 401 con el header `WWW-Authenticate: Bearer`.

### 2. Personalizar el esquema OpenAPI
- En `app/main.py` se añadió la función `custom_openapi()` que:
  - Obtiene el esquema por defecto con `get_openapi()`.
  - Reemplaza `securitySchemes` con `BearerAuth` de tipo `http`, esquema `bearer` y formato `JWT`.
  - Agrega una descripción detallada explicando cómo obtener el token desde `POST /users/login`.
  - Asigna `security: [{"BearerAuth": []}]` a nivel global.
- Se sobrescribió `app.openapi = custom_openapi` para que Swagger UI use esta configuración.

### 3. Flujo de trabajo para desarrolladores
- El desarrollador obtiene un token mediante `curl` o la propia interfaz de Swagger ejecutando `POST /users/login` con JSON.
- Copia el `access_token` y lo pega en el campo "Value" del nuevo formulario de autorización.
- Swagger UI guarda el token y lo envía en el header `Authorization: Bearer <token>` en todas las peticiones autenticadas.

## Resultado
- Swagger UI ya no muestra el formulario OAuth2 con usuario/contraseña, sino un campo de texto simple para pegar el token.
- Desaparece el error 422 porque Swagger ya no intenta llamar a `/users/login`.
- Los endpoints protegidos (creación/listado de payment links, consulta de pagos, etc.) se pueden probar sin problemas en la documentación interactiva.
- La API mantiene su endpoint `/users/login` con JSON para el frontend real, sin cambios.

## Nota
- Este cambio no afecta al funcionamiento de la API para clientes reales; solo modifica la documentación interactiva.
- La autenticación sigue basándose en JWT, y la validación de tokens no ha variado.
- La solución es compatible con cualquier cliente que envíe el header `Authorization: Bearer <token>`.

---
[Fecha] 19/04/2026

## Problema
Aunque se había configurado `HTTPBearer` para la autenticación, Swagger UI seguía sin enviar el header `Authorization` en las peticiones a los endpoints protegidos (ej. `POST /payment-links/`). El botón "Authorize" aceptaba cualquier texto (incluso inválido) y mostraba "Authorized", pero al ejecutar un endpoint el servidor respondía `401 Unauthorized`. Además, el endpoint público `/payment-links/pay/{public_id}` aparecía con el candado de autenticación, causando confusión.

## Causa
- El esquema de seguridad en el OpenAPI generado por FastAPI se llamaba `BearerAuth`, pero las operaciones (paths) requerían un esquema llamado `HTTPBearer`. Swagger UI no podía asociar el token ingresado con el requisito de seguridad.
- Aunque se definió `custom_openapi()`, no se asignó explícitamente la seguridad a cada operación, y el nombre del esquema no coincidía.
- El endpoint público heredaba la dependencia global del router (`dependencies=[Depends(get_current_user)]`), por lo que el OpenAPI lo marcaba como protegido.

## Solución

### 1. Corregir el nombre del esquema de seguridad
En `app/main.py`, dentro de `custom_openapi()`, se cambió la clave del diccionario `securitySchemes` de `"BearerAuth"` a `"HTTPBearer"` (el nombre que FastAPI espera por defecto al usar `HTTPBearer` en las dependencias).

### 2. Asignar seguridad a cada operación explícitamente
Se recorrieron todos los `paths` del OpenAPI y se asignó `operation["security"] = [{"HTTPBearer": []}]` a todas las operaciones excepto aquellas con path público (como `/payment-links/pay/`). Para el path público se asignó `operation["security"] = []`.

### 3. Configurar dependencia global en el router de payment links
En `app/routes/payment_links.py` se agregó `dependencies=[Depends(get_current_user)]` al definir el `APIRouter`, asegurando que todas las rutas del router requieran autenticación por defecto. Luego, se anuló explícitamente en el endpoint público usando `@router.get("/pay/{public_id}", dependencies=[])`.

### 4. Mejorar la descripción en Swagger
Se actualizó la descripción del esquema `HTTPBearer` para advertir que Swagger no valida el token y que el usuario debe pegar un token real obtenido de `POST /users/login`.

## Resultado
- Swagger UI ahora envía correctamente el header `Authorization: Bearer <token>` en todas las peticiones a endpoints protegidos.
- El endpoint público ya no muestra el candado de autenticación y funciona sin token.
- El botón "Authorize" sigue aceptando cualquier texto (comportamiento normal de Swagger), pero el backend valida el token y rechaza los inválidos con `401`.
- Los desarrolladores pueden probar los endpoints de pago sin errores de formato (422) y con validación real de token.

## Nota
- La validación del token sigue siendo responsabilidad exclusiva del backend. Swagger solo actúa como un gestor de headers.
- Se recomienda a los desarrolladores obtener un token fresco desde `POST /users/login` y pegarlo en Authorize antes de probar endpoints protegidos.
- Este cambio no afecta a clientes externos que ya usen el header `Authorization` correctamente.

---
Fecha] 20/04/2026

## Problema
La integración con Stripe presentaba errores en el webhook al recibir el evento `checkout.session.completed`. El endpoint público `/payment-links/pay/{public_id}` aún exigía autenticación a pesar de haber sido declarado como público, y no existían endpoints de redirección para éxito/cancelación. Además, el webhook fallaba con `500 Internal Server Error` debido a problemas de serialización JSON y al uso incorrecto del objeto `StripeObject`.

## Causa
- El router de `payment-links` tenía una dependencia global `dependencies=[Depends(get_current_user)]` que se aplicaba a todas las rutas, incluyendo `/pay/{public_id}`, a pesar de intentar anularla con `dependencies=[]`.
- Dentro del webhook, se intentaba acceder a `session.metadata` como si fuera un diccionario, pero `session` era un `StripeObject` sin método `.get()`, causando `AttributeError`.
- Se intentaba serializar el objeto `event` completo con `json.dumps(event)`, pero `event` no es JSON serializable (objeto `stripe.Event`).
- Faltaban endpoints de redirección (`/payment-success`, `/payment-cancel`) para que Stripe pudiera redirigir al usuario después del pago.
- Las URLs de éxito/cancelación en la creación de la sesión de Stripe apuntaban a `https://tu-sitio.com/success`, que no existen.

## Solución

### 1. Separar routers públicos y protegidos
- Se creó un segundo router `public_router` en `app/routes/payment_links.py` sin dependencia de autenticación.
- Se movieron los endpoints públicos (`/pay/{public_id}`, `/payment-success`, `/payment-cancel`) a `public_router`.
- Se mantuvo el router original `router` con `dependencies=[Depends(get_current_user)]` para los endpoints protegidos.
- En `app/main.py`, se registraron ambos routers (`payment_links_router` y `public_router`).
- Se actualizó `app/routes/__init__.py` para exportar `public_router`.

### 2. Crear endpoints de redirección
- Se agregaron dos nuevos endpoints públicos en `public_router`:
  - `GET /payment-success?session_id=...` → retorna `{"message": "Payment successful", "session_id": session_id}`
  - `GET /payment-cancel` → retorna `{"message": "Payment cancelled"}`
- Se actualizó la creación de la sesión de Stripe en `/pay/{public_id}` para que `success_url` y `cancel_url` apunten a `http://localhost:8000/payment-links/payment-success?session_id={CHECKOUT_SESSION_ID}` y `http://localhost:8000/payment-links/payment-cancel` respectivamente.

### 3. Corregir el webhook de Stripe
- En `app/routes/webhooks.py`, se convirtió el objeto `session` a diccionario usando `session.to_dict()` o `dict(session)` para poder usar `.get()` y evitar errores de serialización.
- Se reemplazó `session.metadata or {}` por `metadata = session_dict.get("metadata", {})`.
- Se eliminó la línea `app_logger.info(f"full event: {json.dumps(event, indent=2)}")` que causaba el error `TypeError: Object of type Event is not JSON serializable`. Alternativamente, se puede loguear `event.to_dict()` si se desea.
- Se ajustó la creación del objeto `Payment` usando `session_dict` en lugar del objeto original.

### 4. Probar el flujo completo localmente
- Se ejecutó Stripe CLI: `stripe listen --forward-to localhost:8000/webhooks/stripe`
- Se creó un payment link autenticado.
- Se accedió a `GET /payment-links/pay/{public_id}` (sin token), obteniendo `checkout_url`.
- Se pagó con tarjeta de prueba `4242 4242 4242 4242`.
- El webhook recibió el evento `checkout.session.completed` y respondió `200 OK`, guardando el pago en la tabla `payments`.
- El navegador fue redirigido a `/payment-success` mostrando el mensaje de éxito.

## Resultado
- El endpoint público ya no requiere autenticación (cualquier cliente puede pagar).
- El webhook procesa correctamente los eventos de Stripe y persiste los pagos en la base de datos.
- Los endpoints de redirección permiten al usuario saber el resultado del pago.
- El flujo completo de pago funciona sin errores en entorno local.
- Los endpoints protegidos (listado de payment links, pagos, etc.) siguen requiriendo token JWT.

## Nota
- Para producción, se deben reemplazar las URLs `http://localhost:8000` por la URL pública de Railway (ej. `https://mi-api.up.railway.app`).
- El secreto del webhook (`STRIPE_WEBHOOK_SECRET`) debe ser el generado por Stripe CLI para desarrollo, y en producción el del webhook creado en Stripe Dashboard.
- La tarjeta de prueba `4242 4242 4242 4242` simula un pago exitoso sin dinero real.

---

[Fecha] 20/04/2026

## Problema
El webhook de Stripe procesaba los pagos de forma síncrona, lo que podía causar timeouts (Stripe espera una respuesta en menos de 10 segundos) y bloqueaba el rendimiento de la API. Además, no se aprovechaba la infraestructura asíncrona.

## Causa
- El endpoint `/webhooks/stripe` realizaba consultas a la base de datos y creación de registros dentro del mismo ciclo de petición.
- No se había integrado Celery para delegar tareas pesadas a workers en segundo plano.

## Solución

### 1. Configuración de Celery y Redis
- Se añadió Redis como broker y backend (en `docker-compose.yml` y en Railway).
- Se creó `app/workers/celery_app.py` con la instancia de Celery.
- Se definió la variable `redis_url` en `Settings`.

### 2. Tarea asíncrona para procesar pagos
- En `app/workers/tasks.py` se creó la tarea `process_stripe_payment` que:
  - Usa un motor de base de datos síncrono (porque Celery no soporta async).
  - Consulta Stripe para obtener la sesión de pago.
  - Guarda el registro en la tabla `payments` con idempotencia.
- También se mantuvo la tarea de ejemplo `send_test_email`.

### 3. Webhook no bloqueante
- Se modificó `app/routes/webhooks.py` para que:
  - Solo valide la firma del webhook.
  - Encole la tarea `process_stripe_payment.delay(session_id)`.
  - Responda inmediatamente con `{"status": "queued"}`.

### 4. Despliegue del worker
- En local: se agregó un servicio `worker` en `docker-compose.yml` con el comando `celery -A app.workers.celery_app worker`.
- En Railway: se añadió un nuevo servicio (desde el mismo repositorio) con el comando de inicio personalizado para Celery, más un servicio Redis.

## Resultado
- El webhook responde en milisegundos, Stripe recibe `200 OK` rápidamente.
- El procesamiento del pago se ejecuta en segundo plano sin afectar la experiencia del usuario.
- La API es más escalable y tolerante a picos de tráfico.
- Se aprovecha la infraestructura de Railway con servicios separados (API, Redis, Worker).

## Nota
- Es crucial que el worker tenga las mismas variables de entorno que la API (sobre todo `DATABASE_URL`, `STRIPE_SECRET_KEY` y `REDIS_URL`).
- Para desarrollo local, Redis se levanta con `docker-compose`.
- En producción, Railway maneja la persistencia de Redis y PostgreSQL automáticamente.

---
