import math
from pathlib import Path

from flask import Flask, jsonify, request

app = Flask(__name__)
APPLICATION_NAME = "student-ml-api"
APPLICATION_VERSION = (Path(__file__).parent / "VERSION").read_text().strip()


@app.get("/")
def home():
    return jsonify({"service": APPLICATION_NAME, "status": "running"})


@app.get("/health")
def health():
    return jsonify(
        {
            "status": "healthy",
            "application": APPLICATION_NAME,
            "version": APPLICATION_VERSION,
        }
    )


@app.post("/predict")
def predict():
    data = request.get_json(silent=True)
    if not isinstance(data, dict) or "value" not in data:
        return jsonify({"error": "A numeric 'value' is required."}), 400

    value = data["value"]
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return jsonify({"error": "'value' must be a finite number."}), 400
    if isinstance(value, float) and not math.isfinite(value):
        return jsonify({"error": "'value' must be a finite number."}), 400

    return jsonify({"input": value, "prediction": value * 2})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
