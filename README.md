# MLOps Continuous Delivery Tutorial

**Hands-on tutorial**: Continuous Delivery (CD) for an ML Application  
**Stack**: GitHub Actions • Docker • GHCR • Staging • Approval Gates • Rollback

---

## Overview

This project implements a complete **Continuous Delivery** pipeline for a simple ML inference API.  
The pipeline follows the principle of **build once, deploy many** using immutable Docker artifacts.

### What this repository demonstrates

| Concept                        | Implementation                                      |
|--------------------------------|-----------------------------------------------------|
| Continuous Integration         | `pytest` runs on every relevant trigger             |
| Continuous Delivery            | Semantic version tags trigger packaging + deployment|
| Immutable artifacts            | Docker image built once and promoted                |
| Container Registry             | GitHub Container Registry (GHCR)                    |
| Staging environment            | Automatic deployment + smoke test                   |
| Production gate                | Manual approval required                            |
| Rollback                       | Redeploy a previous versioned image                 |

---

## Project Structure

```
mlops-cd-demo/
├── app.py                      # Flask ML inference API
├── requirements.txt            # Python dependencies
├── Dockerfile                  # Container definition
├── VERSION                     # Application version (1.0.0)
├── tests/
│   └── test_app.py             # Unit tests
└── .github/
    └── workflows/
        └── cd.yml              # Continuous Delivery workflow
```

---

## Prerequisites

- Git
- Python 3.12+
- Docker
- GitHub account
- An Ubuntu server (VM or cloud instance) with Docker installed
- SSH access to that server

---

## Phase 1 – Create the Demo ML Application

### 1.1 Initialize the project

```bash
mkdir mlops-cd-demo
cd mlops-cd-demo
git init
```

### 1.2 Application code (`app.py`)

```python
from flask import Flask, jsonify, request

app = Flask(__name__)

MODEL_VERSION = "1.0"

@app.route("/")
def home():
    return jsonify({
        "service": "mlops-demo",
        "status": "running"
    })

@app.route("/health")
def health():
    return jsonify({
        "status": "healthy",
        "model_version": MODEL_VERSION
    })

@app.route("/predict", methods=["POST"])
def predict():
    data = request.get_json()
    value = float(data["value"])

    # Dummy ML prediction for teaching
    prediction = value * 2

    return jsonify({
        "input": value,
        "prediction": prediction,
        "model_version": MODEL_VERSION
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
```

### 1.3 Dependencies (`requirements.txt`)

```
flask==3.1.2
pytest==8.4.2
```

### 1.4 Local setup & test

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

In another terminal:

```bash
curl http://localhost:5000/health
```

Expected response:

```json
{
  "model_version": "1.0",
  "status": "healthy"
}
```

### 1.5 Unit tests (`tests/test_app.py`)

```python
from app import app

def test_health():
    client = app.test_client()
    response = client.get("/health")
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "healthy"

def test_prediction():
    client = app.test_client()
    response = client.post("/predict", json={"value": 5})
    assert response.status_code == 200
    data = response.get_json()
    assert data["prediction"] == 10
```

Run tests:

```bash
pytest
```

---

## Phase 2 – Containerize the Application

### 2.1 Dockerfile

```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .

EXPOSE 5000

CMD ["python", "app.py"]
```

### 2.2 Build & run locally

```bash
docker build -t mlops-cd-demo:local .
docker run --rm -p 5000:5000 mlops-cd-demo:local
```

Verify:

```bash
curl http://localhost:5000/health
```

---

## Phase 3 – Versioning & GitHub Repository

### 3.1 Create VERSION file

```
1.0.0
```

### 3.2 Initial commit

```bash
git add .
git commit -m "feat: add inference service"
```

### 3.3 Create GitHub repository & push

```bash
git remote add origin https://github.com/YOUR_USERNAME/mlops-cd-demo.git
git branch -M main
git push -u origin main
```

**Semantic versioning convention used in this project**

| Git Tag   | Docker Image                          |
|-----------|---------------------------------------|
| `v1.0.0`  | `ghcr.io/YOUR_USERNAME/mlops-cd-demo:1.0.0` |
| `v1.1.0`  | `ghcr.io/YOUR_USERNAME/mlops-cd-demo:1.1.0` |
| `v2.0.0`  | `ghcr.io/YOUR_USERNAME/mlops-cd-demo:2.0.0` |

---

## Phase 4 – Continuous Delivery Workflow

The workflow lives at `.github/workflows/cd.yml`.

### Key design decisions

- **Trigger**: only semantic version tags (`v*.*.*`)
- **Build once, deploy many**: the exact same image is used for staging and production
- **Immutable artifacts**: every release is tagged with an explicit version
- **Permissions**: `packages: write` is required to push to GHCR

### Full workflow (test + build + push)

```yaml
name: Continuous Delivery

on:
  push:
    tags:
      - "v*.*.*"

permissions:
  contents: read
  packages: write

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Run tests
        run: pytest

  build:
    needs: test
    runs-on: ubuntu-latest

    outputs:
      version: ${{ steps.version.outputs.version }}

    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Get version
        id: version
        run: |
          VERSION=${GITHUB_REF_NAME#v}
          echo "version=$VERSION" >> "$GITHUB_OUTPUT"

      - name: Show version
        run: |
          echo "Building version ${{ steps.version.outputs.version }}"

      - name: Login to GHCR
        uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Build Docker image
        run: |
          docker build \
            -t ghcr.io/${{ github.repository }}:${{ steps.version.outputs.version }} \
            -t ghcr.io/${{ github.repository }}:latest \
            .

      - name: Push Docker images
        run: |
          docker push ghcr.io/${{ github.repository }}:${{ steps.version.outputs.version }}
          docker push ghcr.io/${{ github.repository }}:latest
```

### How the version is extracted

If the tag is `v1.3.0`, the expression `${GITHUB_REF_NAME#v}` produces `1.3.0`.

### First release (test Phase 4)

```bash
git checkout main
git pull
git tag v1.0.0
git push origin v1.0.0
```

Go to the **Actions** tab. You should see:

- `test` job → success
- `build` job → success  
- Image appears in GitHub Packages as `ghcr.io/YOUR_USERNAME/mlops-cd-demo:1.0.0` and `:latest`

---

## Phase 5 – GitHub Environments & Secrets

### 5.1 Create Environments

1. Repository → **Settings** → **Environments**
2. Create environment named `staging`
3. Create environment named `production`

**Production protection rule**

- Enable **Required reviewers**
- Add your GitHub username as a reviewer
- Save

Result:

```
staging     → automatic
production  → waits for manual approval
```

### 5.2 Prepare the deployment server

On an Ubuntu server:

```bash
sudo apt update
sudo apt install docker.io -y
sudo systemctl enable docker
sudo systemctl start docker
docker --version
```

(Optional) Allow your user to run Docker without sudo:

```bash
sudo usermod -aG docker $USER
# log out and back in
```

### 5.3 Generate a dedicated SSH key (on your local machine)

```bash
ssh-keygen -t ed25519 -f deploy_key -C "github-actions-deploy"
# Leave passphrase empty
```

Copy the public key to the server:

```bash
ssh-copy-id -i deploy_key.pub USER@SERVER_IP
```

Test the connection:

```bash
ssh -i deploy_key USER@SERVER_IP
```

### 5.4 Store secrets in GitHub Environments

#### Staging environment secrets

| Secret Name       | Value                                      |
|-------------------|--------------------------------------------|
| `STAGING_HOST`    | Server IP address                          |
| `STAGING_USER`    | SSH username (e.g. `ubuntu`)               |
| `STAGING_SSH_KEY` | Full content of the private key (`deploy_key`) |

#### Production environment secrets

| Secret Name           | Value                                      |
|-----------------------|--------------------------------------------|
| `PRODUCTION_HOST`     | Server IP (same or different)              |
| `PRODUCTION_USER`     | SSH username                               |
| `PRODUCTION_SSH_KEY`  | Full content of the private key            |

**How to copy the private key**

```bash
cat deploy_key
```

Copy everything including the `BEGIN` / `END` lines.

### 5.5 Verification checklist

- [ ] Environments `staging` and `production` exist
- [ ] Production has required reviewers configured
- [ ] Staging secrets: `STAGING_HOST`, `STAGING_USER`, `STAGING_SSH_KEY`
- [ ] Production secrets: `PRODUCTION_HOST`, `PRODUCTION_USER`, `PRODUCTION_SSH_KEY`
- [ ] SSH login works with the deploy key
- [ ] Docker is running on the server

---

## Pipeline Flow (current state)

```
Developer
    │
    ▼
Feature Branch → Pull Request → CI (tests)
    │
    ▼
Merge to main
    │
    ▼
git tag vX.Y.Z → git push origin vX.Y.Z
    │
    ▼
┌─────────────────────────────────────┐
│  GitHub Actions – Continuous Delivery │
│                                       │
│  1. test          (pytest)            │
│  2. build         (Docker + GHCR)     │
│                                       │
│  (deploy-staging + smoke test         │
│   + production approval will be       │
│   added in the next phase)            │
└─────────────────────────────────────┘
```

---

## Important Principles Covered So Far

1. **CI vs CD**  
   CI proves the code is good enough to integrate.  
   CD proves the resulting artifact is good enough to release.

2. **Build once, deploy many**  
   The exact same Docker image that is tested is the one that will later be promoted to production.

3. **Immutable artifacts**  
   Every release is tagged with an explicit semantic version.  
   `latest` is only a convenience tag.

4. **Secrets management**  
   Never hard-code credentials in YAML. Use GitHub Environment secrets.

---

## Next Steps (Phase 6 onwards)

The following will be added in subsequent phases:

- Automatic deployment to the `staging` environment
- Smoke / health-check test after staging deployment
- Manual approval gate for production
- Production deployment job
- Rollback procedure
- Enhanced `/health` endpoint returning `application_version` + `model_version`

---

## Useful Commands Reference

```bash
# Local development
source .venv/bin/activate
python app.py
pytest

# Docker
docker build -t mlops-cd-demo:local .
docker run --rm -p 5000:5000 mlops-cd-demo:local

# Release a new version
git tag v1.0.0
git push origin v1.0.0

# Inspect image in GHCR
# GitHub → Packages (right sidebar of the repository)
```

---

## Teaching Notes

- The workflow is intentionally triggered by tags, not by every commit to `main`.  
  A tag such as `v1.0.0` represents a deliberate, releasable version.
- Tests are a gate that allows an artifact to enter the delivery pipeline; they are not the delivery pipeline itself.
- Environment-scoped secrets keep staging and production credentials isolated.

---

**Status of this repository (as of Phase 5 completion)**

✅ Application + tests  
✅ Dockerfile  
✅ Semantic versioning  
✅ Full test + build + push workflow to GHCR  
✅ GitHub Environments (`staging` / `production`)  
✅ Deployment secrets stored securely  

Ready for Phase 6: Automatic Staging Deployment + Smoke Test + Production Approval Gate.
```
