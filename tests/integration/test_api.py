import uuid

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


@pytest.mark.asyncio
async def test_create_campaign(client: AsyncClient, campaign_data: dict):
    response = await client.post("/campaigns", json=campaign_data)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == campaign_data["name"]
    assert data["edition"] == campaign_data["edition"]
    assert data["status"] == "active"
    assert "id" in data


@pytest.mark.asyncio
async def test_get_campaign(client: AsyncClient, created_campaign: dict):
    campaign_id = created_campaign["id"]
    response = await client.get(f"/campaigns/{campaign_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == campaign_id


@pytest.mark.asyncio
async def test_get_nonexistent_campaign(client: AsyncClient):
    fake_id = str(uuid.uuid4())
    response = await client.get(f"/campaigns/{fake_id}")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_enable_module_for_campaign(
    client: AsyncClient,
    created_campaign: dict,
):
    campaign_id = created_campaign["id"]
    response = await client.post(
        f"/campaigns/{campaign_id}/enable-module",
        json={"module_id": str(uuid.uuid4()), "priority": 50}
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_campaign_modules(
    client: AsyncClient,
    created_campaign: dict
):
    campaign_id = created_campaign["id"]
    response = await client.get(f"/campaigns/{campaign_id}/modules")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_session_event_creation(
    client: AsyncClient,
    created_campaign: dict
):
    campaign_id = created_campaign["id"]
    session_id = str(uuid.uuid4())
    event_data = {
        "campaign_id": campaign_id,
        "event_type": "player_action",
        "payload_json": {"action": "moved", "location": "forest"}
    }
    response = await client.post(f"/sessions/{session_id}/events", json=event_data)
    assert response.status_code == 200
    data = response.json()
    assert data["event_type"] == "player_action"
    assert data["session_id"] == session_id


@pytest.mark.asyncio
async def test_get_timeline(
    client: AsyncClient,
    created_campaign: dict
):
    campaign_id = created_campaign["id"]
    session_id = str(uuid.uuid4())

    event_data = {
        "campaign_id": campaign_id,
        "event_type": "combat_start",
        "payload_json": {"enemy": "wolf"}
    }
    await client.post(f"/sessions/{session_id}/events", json=event_data)

    response = await client.get(
        f"/sessions/{session_id}/events",
        params={"campaign_id": campaign_id}
    )
    assert response.status_code == 200
    data = response.json()
    assert "events" in data
    assert data["total"] >= 1


@pytest.mark.asyncio
async def test_apply_state_patches(
    client: AsyncClient,
    created_campaign: dict
):
    campaign_id = created_campaign["id"]
    patches = [
        {"op": "set", "path": "quests.main.status", "value": "in_progress"},
        {"op": "inc", "path": "player.xp", "value": 100}
    ]
    response = await client.post(
        "/state/apply",
        json={"campaign_id": campaign_id, "patches": patches}
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["applied"]) == 2


@pytest.mark.asyncio
async def test_get_world_state(
    client: AsyncClient,
    created_campaign: dict
):
    campaign_id = created_campaign["id"]

    patches = [{"op": "set", "path": "test.value", "value": 42}]
    await client.post(
        "/state/apply",
        json={"campaign_id": campaign_id, "patches": patches}
    )

    response = await client.get(f"/state/campaign/{campaign_id}")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


@pytest.mark.asyncio
async def test_query_requires_campaign(client: AsyncClient):
    query_data = {
        "campaign_id": str(uuid.uuid4()),
        "session_id": str(uuid.uuid4()),
        "user_input": "What are the rules for combat?"
    }
    response = await client.post("/query", json=query_data)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_query_returns_response_structure(
    client: AsyncClient,
    created_campaign: dict
):
    campaign_id = created_campaign["id"]
    session_id = str(uuid.uuid4())
    query_data = {
        "campaign_id": campaign_id,
        "session_id": session_id,
        "user_input": "What is armor class?",
        "mode": "rules"
    }
    response = await client.post("/query", json=query_data)
    assert response.status_code == 200
    data = response.json()
    assert "answer" in data
    assert "used_agent" in data
    assert "confidence" in data
    assert "citations" in data
    assert data["used_agent"] == "rules"


@pytest.mark.asyncio
async def test_query_auto_mode_detection(
    client: AsyncClient,
    created_campaign: dict
):
    campaign_id = created_campaign["id"]
    session_id = str(uuid.uuid4())
    query_data = {
        "campaign_id": campaign_id,
        "session_id": session_id,
        "user_input": "Roll initiative!"
    }
    response = await client.post("/query", json=query_data)
    assert response.status_code == 200
    data = response.json()
    assert data["used_agent"] == "encounter"


@pytest.mark.asyncio
async def test_query_state_mode(
    client: AsyncClient,
    created_campaign: dict
):
    campaign_id = created_campaign["id"]
    session_id = str(uuid.uuid4())
    query_data = {
        "campaign_id": campaign_id,
        "session_id": session_id,
        "user_input": "Mark quest complete",
        "mode": "state"
    }
    response = await client.post("/query", json=query_data)
    assert response.status_code == 200
    data = response.json()
    assert data["used_agent"] == "state"
    assert "state_updates" in data


@pytest.mark.asyncio
async def test_query_narrative_mode(
    client: AsyncClient,
    created_campaign: dict
):
    campaign_id = created_campaign["id"]
    session_id = str(uuid.uuid4())
    query_data = {
        "campaign_id": campaign_id,
        "session_id": session_id,
        "user_input": "Describe the forest",
        "mode": "narrative"
    }
    response = await client.post("/query", json=query_data)
    assert response.status_code == 200
    data = response.json()
    assert data["used_agent"] == "narrative"


@pytest.mark.asyncio
async def test_campaign_isolation(
    client: AsyncClient,
    campaign_data: dict
):
    response1 = await client.post("/campaigns", json=campaign_data)
    campaign1_id = response1.json()["id"]

    campaign2_data = {"name": "Campaign 2", "edition": "5e"}
    response2 = await client.post("/campaigns", json=campaign2_data)
    campaign2_id = response2.json()["id"]

    assert campaign1_id != campaign2_id

    query_data1 = {
        "campaign_id": str(campaign1_id),
        "session_id": str(uuid.uuid4()),
        "user_input": "Test query"
    }
    response = await client.post("/query", json=query_data1)
    assert response.status_code == 200
