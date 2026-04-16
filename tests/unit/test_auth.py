import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_docs_endpoint(client: AsyncClient):
    response = await client.get("/docs")
    assert response.status_code == 200
