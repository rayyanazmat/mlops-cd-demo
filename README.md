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

## Phase 6 – Automatic Staging Deployment (Section 19)

Add the `deploy-staging` job to `.github/workflows/cd.yml` (after the `build` job):

```yaml
  deploy-staging:
    needs: build
    runs-on: ubuntu-latest

    environment:
      name: staging

    steps:
      - name: Deploy to staging
        uses: appleboy/ssh-action@v1
        with:
          host: ${{ secrets.STAGING_HOST }}
          username: ${{ secrets.STAGING_USER }}
          key: ${{ secrets.STAGING_SSH_KEY }}

          script: |
            docker pull \
              ghcr.io/${{ github.repository }}:${{ needs.build.outputs.version }}

            docker stop mlops-api || true
            docker rm mlops-api || true

            docker run -d \
              --name mlops-api \
              --restart unless-stopped \
              -p 5000:5000 \
              ghcr.io/${{ github.repository }}:${{ needs.build.outputs.version }}
```

**Flow so far**

```
tag → test → build → registry → staging
```

---

## Phase 7 – Smoke / Health Test (Section 20)

A successful `docker run` does **not** prove the API is healthy. Add a verification step inside the `deploy-staging` job:

```yaml
      - name: Verify staging deployment
        run: |
          sleep 5

          curl --fail \
            http://${{ secrets.STAGING_HOST }}:5000/health
```

**Decision logic**

```
Deploy
  │
  ▼
Health endpoint
  │
  ├── FAIL  → Stop pipeline
  │
  SUCCESS
  │
  ▼
Candidate for production
```

---

## Phase 8 – Production Approval Gate (Section 21)

1. Confirm the `production` environment has **Required reviewers** enabled (done in Phase 5).
2. Add the `deploy-production` job:

```yaml
  deploy-production:
    needs:
      - build
      - deploy-staging
    runs-on: ubuntu-latest

    environment:
      name: production

    steps:
      - name: Deploy production
        uses: appleboy/ssh-action@v1
        with:
          host: ${{ secrets.PRODUCTION_HOST }}
          username: ${{ secrets.PRODUCTION_USER }}
          key: ${{ secrets.PRODUCTION_SSH_KEY }}

          script: |
            docker pull \
              ghcr.io/${{ github.repository }}:${{ needs.build.outputs.version }}

            docker stop mlops-api || true
            docker rm mlops-api || true

            docker run -d \
              --name mlops-api \
              --restart unless-stopped \
              -p 5000:5000 \
              ghcr.io/${{ github.repository }}:${{ needs.build.outputs.version }}
```

The workflow will pause at **“Waiting for approval”**.  
Once an authorized reviewer approves it, production deployment starts.  
**That is Continuous Delivery.**

---

## Phase 9 – Complete Workflow (Section 22)

Here is the **full final** `.github/workflows/cd.yml`:

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
      - name: Checkout
        uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Test
        run: pytest

  build:
    needs: test
    runs-on: ubuntu-latest

    outputs:
      version: ${{ steps.version.outputs.version }}

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Get version
        id: version
        run: |
          VERSION=${GITHUB_REF_NAME#v}
          echo "version=$VERSION" >> "$GITHUB_OUTPUT"

      - name: Login GHCR
        uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Build
        run: |
          docker build \
            -t ghcr.io/${{ github.repository }}:${{ steps.version.outputs.version }} \
            -t ghcr.io/${{ github.repository }}:latest \
            .

      - name: Push
        run: |
          docker push ghcr.io/${{ github.repository }}:${{ steps.version.outputs.version }}
          docker push ghcr.io/${{ github.repository }}:latest

  deploy-staging:
    needs: build
    runs-on: ubuntu-latest

    environment:
      name: staging

    steps:
      - name: Deploy staging
        uses: appleboy/ssh-action@v1
        with:
          host: ${{ secrets.STAGING_HOST }}
          username: ${{ secrets.STAGING_USER }}
          key: ${{ secrets.STAGING_SSH_KEY }}

          script: |
            docker pull \
              ghcr.io/${{ github.repository }}:${{ needs.build.outputs.version }}

            docker stop mlops-api || true
            docker rm mlops-api || true

            docker run -d \
              --name mlops-api \
              --restart unless-stopped \
              -p 5000:5000 \
              ghcr.io/${{ github.repository }}:${{ needs.build.outputs.version }}

      - name: Smoke test
        run: |
          sleep 5
          curl --fail \
            http://${{ secrets.STAGING_HOST }}:5000/health

  deploy-production:
    needs:
      - build
      - deploy-staging
    runs-on: ubuntu-latest

    environment:
      name: production

    steps:
      - name: Deploy production
        uses: appleboy/ssh-action@v1
        with:
          host: ${{ secrets.PRODUCTION_HOST }}
          username: ${{ secrets.PRODUCTION_USER }}
          key: ${{ secrets.PRODUCTION_SSH_KEY }}

          script: |
            docker pull \
              ghcr.io/${{ github.repository }}:${{ needs.build.outputs.version }}

            docker stop mlops-api || true
            docker rm mlops-api || true

            docker run -d \
              --name mlops-api \
              --restart unless-stopped \
              -p 5000:5000 \
              ghcr.io/${{ github.repository }}:${{ needs.build.outputs.version }}
```

Commit and push the complete workflow:

```bash
git add .github/workflows/cd.yml
git commit -m "ci: complete CD pipeline with staging, smoke test and production gate"
git push
```

---

## Phase 10 – Release Version 1.0.0 (Section 23)

```bash
git checkout main
git pull

git tag v1.0.0
git push origin v1.0.0
```

Watch **GitHub → Actions → Continuous Delivery**:

```
✓ test
✓ build
✓ deploy-staging
⏸ deploy-production   ← Waiting for approval
```

After you approve:

```
✓ deploy-production
```

---

## Phase 11 – Demonstrate a New Release (Section 24)

1. Change the model version in `app.py`:

```python
MODEL_VERSION = "1.1"
```

2. Follow the normal flow: branch → commit → push → PR → CI → review → merge to `main`.

3. Tag and push the new version:

```bash
git checkout main
git pull

git tag v1.1.0
git push origin v1.1.0
```

Registry now contains:

```
1.0.0
1.1.0
latest
```

Production promotion path: `1.0.0 → 1.1.0`

---

## Phase 12 – Rollback (Section 25)

**Scenario**: version `1.1.0` has a serious prediction problem.

Because earlier images are versioned and immutable, rollback is simple:

```bash
# On the production server
docker stop mlops-api
docker rm mlops-api

docker run -d \
  --name mlops-api \
  --restart unless-stopped \
  -p 5000:5000 \
  ghcr.io/YOUR_USERNAME/mlops-cd-demo:1.0.0
```

Verify:

```bash
curl http://SERVER_IP:5000/health
```

**Teaching note**: Relying only on the `latest` tag is insufficient.  
Explicit version tags let you reproduce and restore a known-good deployment.

---

## Phase 13 – Promotion, Not Rebuilding (Section 26)

### Bad approach (rebuild for every environment)

```
main
 │
 build staging
 │
 test staging
 │
 rebuild production
 │
 production
```

### Correct approach (build once, promote the same artifact)

```
main
 │
 BUILD 1.1.0
 │
 Registry
 │
 1.1.0
  ├── staging
  └── production
```

The artifact moves through environments; the source code is **not** rebuilt at every stage.

---

## Phase 14 – Connect CD with MLOps (Section 27)

### Normal software delivery

```
Source Code
     │
Docker image
     │
Deployment
```

### ML delivery

```
Code
 +
Model
 +
Dependencies
 +
Preprocessing
 +
Configuration
       │
Reproducible artifact
       │
Deployment
```

**Example ML artifact**

```
ml-api:1.4.0

contains:
  - Flask API
  - scikit-learn runtime
  - preprocessing.py
  - model.pkl
  - feature schema
  - runtime dependencies
```

MLOps delivery is more complex because software and model versions can change independently.

---

## Phase 15 – Model / Application Versioning (Section 28)

Example of independent versioning:

```
Application Version: 2.3.0
Model Version:       fraud-model-17
Dataset Version:     transactions-v31

Deployment
├── app     = 2.3.0
├── model   = 17
├── dataset = 31
└── image   = sha256:abcd...
```

**Key question to ask**:  
“If prediction accuracy deteriorates, what exactly should we rollback?”

This prepares the ground for DVC, MLflow Model Registry, model promotion, and monitoring.

---

## Phase 16 – Recommended Classroom Timing (Section 29)

| Time       | Activity                              |
|------------|---------------------------------------|
| 0–10 min   | CI vs CD vs Continuous Deployment     |
| 10–20 min  | Flask ML API + tests                  |
| 20–30 min  | Docker artifact                       |
| 30–40 min  | Registry + immutable artifacts        |
| 40–55 min  | GitHub Actions build/push             |
| 55–65 min  | Staging environment                   |
| 65–75 min  | Health check + production approval     |
| 75–82 min  | Release v1.0.0 → v1.1.0               |
| 82–87 min  | Rollback                              |
| 87–90 min  | MLOps discussion                      |

---

## Phase 17 – Student Exercise: Build a Professional CD Pipeline (Section 30)

Students should complete the following independently:

- [ ] PRs continue to run CI only
- [ ] A semantic version tag such as `v1.3.0` starts CD
- [ ] Publish `ghcr.io/student/ml-api:1.3.0` and `ghcr.io/student/ml-api:latest`
- [ ] Deploy to staging automatically
- [ ] Require `GET /health` to pass before production becomes available
- [ ] Require manual approval for production
- [ ] Return `application_version`, `model_version`, and `status` from `/health`
- [ ] Demonstrate rollback from `1.3.0` to `1.2.0`

**Target `/health` response**

```json
{
  "application_version": "1.3.0",
  "model_version": "model-7",
  "status": "healthy"
}
```

---

## Bonus Exercise – Production Traceability

Capture the Git commit:

```bash
git rev-parse --short HEAD
```

Expose it through `/health`:

```json
{
  "application_version": "1.3.0",
  "model_version": "model-7",
  "git_commit": "f72ab81",
  "status": "healthy"
}
```

Traceability chain:

```
Production
  │
Container 1.3.0
  │
Git commit f72ab81
  │
Pull Request #27
```

---

## Recommended Next Lecture

**Production Deployment Strategies**: Rolling, Recreate, Blue/Green, and Canary Releases.

### Suggested course progression

1. Git
2. Branching / PR
3. Semantic Versioning
4. CI with GitHub Actions
5. **Continuous Delivery** ← this tutorial
6. Docker Compose deployment
7. Deployment strategies
   - Rolling
   - Recreate
   - Blue/Green
   - Canary
8. Kubernetes
9. Kubernetes-based CD
10. GitOps with Argo CD
11. ML model delivery
    - DVC
    - MLflow Registry
    - model promotion
12. Monitoring + rollback

**Teaching bridge**: students first learn how to deliver version `1.1.0`, then learn how to replace version `1.0.0` safely with controlled risk and minimal downtime.

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

# Rollback on server
docker stop mlops-api
docker rm mlops-api
docker run -d --name mlops-api --restart unless-stopped -p 5000:5000 \
  ghcr.io/YOUR_USERNAME/mlops-cd-demo:1.0.0

# Inspect image in GHCR
# GitHub → Packages (right sidebar of the repository)
```

---

## Important Principles (Summary)

1. **CI vs CD vs Continuous Deployment**  
   - CI = code is good enough to integrate  
   - CD = artifact is good enough to release (human approval for production)  
   - Continuous Deployment = automatic production release

2. **Build once, deploy many** – the exact artifact tested in staging is promoted to production.

3. **Immutable artifacts** – every release is tagged with an explicit semantic version.

4. **Secrets management** – never hard-code credentials; use GitHub Environment secrets.

5. **Promotion, not rebuilding** – the artifact moves through environments; source is not rebuilt.

6. **Rollback is simple** when you keep versioned immutable images.

---

## Final Status Checklist

✅ Application + tests  
✅ Dockerfile  
✅ Semantic versioning  
✅ Full test + build + push workflow to GHCR  
✅ GitHub Environments (`staging` / `production`)  
✅ Deployment secrets stored securely  
✅ Automatic staging deployment  
✅ Smoke / health test  
✅ Manual approval gate for production  
✅ Production deployment  
✅ Rollback procedure demonstrated  
✅ Connection to MLOps concepts explained  

**Tutorial complete.**
