from app import app


def test_health():
    response = app.test_client().get("/health")

    assert response.status_code == 200
    assert response.get_json() == {
        "status": "healthy",
        "application": "student-ml-api",
        "version": "1.0.0",
    }


def test_successful_prediction():
    response = app.test_client().post("/predict", json={"value": 10})

    assert response.status_code == 200
    assert response.get_json() == {"input": 10, "prediction": 20}


def test_prediction_rejects_missing_value():
    response = app.test_client().post("/predict", json={})

    assert response.status_code == 400
    assert "error" in response.get_json()


def test_prediction_rejects_non_numeric_value():
    response = app.test_client().post("/predict", json={"value": "ten"})

    assert response.status_code == 400
    assert "error" in response.get_json()


def test_prediction_rejects_invalid_json():
    response = app.test_client().post(
        "/predict", data="not-json", content_type="application/json"
    )

    assert response.status_code == 400
    assert "error" in response.get_json()


def test_prediction_rejects_non_finite_value():
    response = app.test_client().post("/predict", json={"value": float("nan")})

    assert response.status_code == 400
    assert "error" in response.get_json()


def test_prediction_rejects_boolean_value():
    response = app.test_client().post("/predict", json={"value": True})

    assert response.status_code == 400
    assert "error" in response.get_json()