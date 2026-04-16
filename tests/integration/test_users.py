import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.main import app
from app.core.database import get_db, Base
from app.models.user import User, UserToken

# =====================================================
# configuración de base de datos de prueba (sqlite en memoria)
# =====================================================
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"
test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestSessionLocal = async_sessionmaker(test_engine, expire_on_commit=False)

# =====================================================
# fixtures
# =====================================================
@pytest_asyncio.fixture(scope="function", autouse=True)
async def setup_test_db():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await test_engine.dispose()

@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

# helper para crear un usuario rapido
async def create_user(client: AsyncClient, email: str, password: str):
    return await client.post("/users/", json={"email": email, "password": password})

# test endpoint create_user
@pytest.mark.asyncio
async def test_create_user(client: AsyncClient):
    response = await create_user(client, "test@example.com", "secret123")
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "test@example.com"
    assert "id" in data

# test endpoint login - login success
@pytest.mark.asyncio
async def test_login_success(client: AsyncClient):
    await create_user(client, "login@example.com", "mypass")
    response = await client.post("/users/login", json={
        "username": "login@example.com",
        "password": "mypass"
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"

# invalid password
@pytest.mark.asyncio
async def test_login_invalid_password(client: AsyncClient):
    await create_user(client, "wrongpass@example.com", "correctpass")
    response = await client.post("/users/login", json={
        "username": "wrongpass@example.com",
        "password": "badpass"
    })
    assert response.status_code == 401
    assert "detail" in response.json()

# user not found
@pytest.mark.asyncio
async def test_login_user_not_found(client: AsyncClient):
    response = await client.post("/users/login", json={
        "username": "nonexistent@example.com",
        "password": "anything"
    })
    assert response.status_code == 401

# test endpoint /me
@pytest.mark.asyncio
async def test_get_me(client: AsyncClient):
    await create_user(client, "me@example.com", "test123")
    login_resp = await client.post("/users/login", json={
        "username": "me@example.com",
        "password": "test123"
    })
    access_token = login_resp.json()["access_token"]
    response = await client.get("/users/me", headers={
        "Authorization": f"Bearer {access_token}"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "me@example.com"
    assert "id" in data

@pytest.mark.asyncio
async def test_get_me_unauthorized(client: AsyncClient):
    response = await client.get("/users/me")
    assert response.status_code == 401

# test endpoint refresh token
@pytest.mark.asyncio
async def test_refresh_token(client: AsyncClient):
    await create_user(client, "refresh@example.com", "pass")
    login = await client.post("/users/login", json={
        "username": "refresh@example.com",
        "password": "pass"
    })
    refresh_token = login.json()["refresh_token"]
    refresh_resp = await client.post("/users/refresh", json={"refresh_token": refresh_token})
    assert refresh_resp.status_code == 200
    new_access = refresh_resp.json()["access_token"]
    assert new_access != login.json()["access_token"]
    # Verificar que el nuevo access token funciona
    me = await client.get("/users/me", headers={"Authorization": f"Bearer {new_access}"})
    assert me.status_code == 200

@pytest.mark.asyncio
async def test_refresh_with_invalid_token(client: AsyncClient):
    response = await client.post("/users/refresh", json={"refresh_token": "invalid.token.value"})
    assert response.status_code == 401

# test endpoint logout
@pytest.mark.asyncio
async def test_logout(client: AsyncClient):
    await create_user(client, "logout@example.com", "pass")
    login = await client.post("/users/login", json={
        "username": "logout@example.com",
        "password": "pass"
    })
    refresh_token = login.json()["refresh_token"]
    logout_resp = await client.post("/users/logout", json={"refresh_token": refresh_token})
    assert logout_resp.status_code == 200
    # Intentar refrescar con el mismo token debería fallar
    refresh_resp = await client.post("/users/refresh", json={"refresh_token": refresh_token})
    assert refresh_resp.status_code == 401

# test full flow
@pytest.mark.asyncio
async def test_full_flow(client: AsyncClient):
    # 1. Registrar
    reg = await client.post("/users/", json={"email": "flow@example.com", "password": "flowpass"})
    assert reg.status_code == 200
    # 2. Login
    login = await client.post("/users/login", json={
        "username": "flow@example.com",
        "password": "flowpass"
    })
    assert login.status_code == 200
    tokens = login.json()
    access = tokens["access_token"]
    refresh = tokens["refresh_token"]
    # 3. Obtener perfil
    me = await client.get("/users/me", headers={"Authorization": f"Bearer {access}"})
    assert me.status_code == 200
    assert me.json()["email"] == "flow@example.com"
    # 4. Refrescar token
    refresh_resp = await client.post("/users/refresh", json={"refresh_token": refresh})
    assert refresh_resp.status_code == 200
    new_access = refresh_resp.json()["access_token"]
    # 5. Probar nuevo access token
    me2 = await client.get("/users/me", headers={"Authorization": f"Bearer {new_access}"})
    assert me2.status_code == 200
    # 6. Logout
    logout = await client.post("/users/logout", json={"refresh_token": refresh})
    assert logout.status_code == 200
    # 7. Verificar que refresh ya no sirve
    refresh_fail = await client.post("/users/refresh", json={"refresh_token": refresh})
    assert refresh_fail.status_code == 401
