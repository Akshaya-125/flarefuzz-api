from fastapi.testclient import TestClient

from flarefuzz_api.main import app


client = TestClient(app)


def test_normalize_endpoint_returns_inventory_and_separate_si_values():
    response = client.post(
        "/api/v1/normalize",
        files={"file": ("diameters.csv", b"Flame diameter (mm)\n12\n", "text/csv")},
        data={"provenance": "experimental", "experiment": "drop-tower-A"},
    )
    assert response.status_code == 200
    result = response.json()
    assert result["parameters"][0]["canonical_name"] == "flame_diameter"
    assert result["source_values"] == [{"flame_diameter#1": "12"}]
    assert result["si_values"] == [{"flame_diameter#1": 0.012}]
    assert result["metadata"]["experiment"] == "drop-tower-A"


def test_normalize_endpoint_rejects_unregistered_formats():
    response = client.post(
        "/api/v1/normalize",
        files={
            "file": (
                "dataset.xlsx",
                b"not csv",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
    )
    assert response.status_code == 415
