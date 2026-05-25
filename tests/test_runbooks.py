import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.domains.runbooks.models import Runbook, RunbookLayer, RunbookDevice, RunbookExecution, RunbookExecutionStep

@pytest.mark.asyncio
async def test_runbook_execution_and_username_audit(client: AsyncClient, db: AsyncSession):
    # 1. Create a Runbook
    rb_payload = {
        "name": "Emergency Shutdown",
        "typ": "shutdown",
        "beschreibung": "Emergency shutdown sequence"
    }
    response = await client.post("/api/v1/runbooks/", json=rb_payload, headers={"X-Username": "Andreas"})
    assert response.status_code == 201
    rb_data = response.json()
    assert rb_data["name"] == "Emergency Shutdown"
    assert rb_data["erstellt_von"] == "Andreas"
    rb_id = rb_data["id"]

    # 2. Create a Layer
    layer_payload = {
        "name": "Database Layer",
        "position": 1
    }
    response = await client.post(f"/api/v1/runbooks/{rb_id}/layers", json=layer_payload)
    assert response.status_code == 201
    layer_data = response.json()
    layer_id = layer_data["id"]

    # 3. Create a Runbook Device (using freitext)
    dev_payload = {
        "layer_id": layer_id,
        "freitext": "MySQL Core",
        "delay_seconds": 60,
        "responsible": "Andreas",
        "note": "Main database",
        "position": 1
    }
    response = await client.post(f"/api/v1/runbooks/{rb_id}/devices", json=dev_payload)
    assert response.status_code == 201
    device_data = response.json()
    device_id = device_data["id"]

    # 4. Start an Execution
    exec_payload = {
        "runbook_id": rb_id,
        "modus": "shutdown"
    }
    response = await client.post(f"/api/v1/runbooks/{rb_id}/execute", json=exec_payload, headers={"X-Username": "Andreas"})
    assert response.status_code == 201
    exec_data = response.json()
    assert exec_data["status"] == "aktiv"
    assert exec_data["gestartet_von"] == "Andreas"
    exec_id = exec_data["id"]

    # 5. Check a Step
    check_payload = {
        "note": "Stopped MySQL daemon"
    }
    response = await client.post(f"/api/v1/executions/{exec_id}/steps/{device_id}/check", json=check_payload, headers={"X-Username": "Andreas"})
    assert response.status_code == 200
    step_data = response.json()
    assert step_data["runbook_device_id"] == device_id
    assert step_data["abgehakt_von"] == "Andreas"
    assert step_data["note"] == "Stopped MySQL daemon"

    # 6. Check that execution steps are loaded
    response = await client.get(f"/api/v1/executions/{exec_id}")
    assert response.status_code == 200
    exec_details = response.json()
    assert len(exec_details["steps"]) == 1
    assert exec_details["steps"][0]["runbook_device_id"] == device_id

    # 7. Uncheck the Step
    response = await client.delete(f"/api/v1/executions/{exec_id}/steps/{device_id}/uncheck")
    assert response.status_code == 204

    # 8. Check that steps are now empty
    response = await client.get(f"/api/v1/executions/{exec_id}")
    assert response.status_code == 200
    exec_details = response.json()
    assert len(exec_details["steps"]) == 0

    # 9. Get all executions for the runbook
    response = await client.get(f"/api/v1/runbooks/{rb_id}/executions")
    assert response.status_code == 200
    executions_list = response.json()
    assert len(executions_list) == 1
    assert executions_list[0]["id"] == exec_id
