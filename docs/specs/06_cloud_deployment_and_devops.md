# SPEC 6: Cloud Infrastructure, Multi-Cloud Deployment & Production DevOps

**Product Name**: Cadence AI  
**Document Version**: 1.0.0  
**Status**: APPROVED & FINALIZED  
**Scope**: Multi-Cloud Deployment (AWS, GCP, Azure), Containerization, Terraform IaC, Secret Management, and Zero-Downtime Operations  

---

## 1. Multi-Cloud Production Architecture

To demonstrate production engineering maturity, Cadence AI is architected with cloud-neutral abstractions. It supports one-command deployment across **AWS** (primary target), **GCP**, and **Azure** using containerized microservices and managed PostgreSQL with `pgvector`.

```
                        ┌───────────────────────────────────────────────┐
                        │             CloudFlare / Cloud CDN            │
                        │     • DDoS Mitigation & TLS 1.3 Termination   │
                        │     • WAF (Web Application Firewall)          │
                        └───────────────────────┬───────────────────────┘
                                                │
                 ┌──────────────────────────────┴──────────────────────────────┐
                 ▼                                                             ▼
  ┌─────────────────────────────┐                               ┌─────────────────────────────┐
  │      Static Edge / CDN      │                               │    Application Load Balancer│
  │   (AWS S3 / GCP Cloud Storage│                              │  (AWS ALB / GCP Cloud Load  │
  │   / Azure Blob Storage)     │                               │   Balancer / Azure App GW)  │
  │                             │                               └──────────────┬──────────────┘
  │   • Vue 3 SPA Assets        │                                              │ HTTP / WSS
  │   • Tailwind Bundles        │                                              ▼
  └─────────────────────────────┘                               ┌─────────────────────────────┐
                                                                │  Container Orchestration    │
                                                                │  (AWS ECS Fargate / GCP     │
                                                                │   Cloud Run / Azure ACA)    │
                                                                │                             │
                                                                │  ┌────────────────────────┐ │
                                                                │  │  FastAPI Agent Gateway │ │
                                                                │  │  + LangGraph Runtime   │ │
                                                                │  └───────────┬────────────┘ │
                                                                │              │ In-Memory/   │
                                                                │              ▼ Unix Socket  │
                                                                │  ┌────────────────────────┐ │
                                                                │  │ vFairs Core MCP Server │ │
                                                                │  │ (FastMCP Standard)     │ │
                                                                │  └────────────────────────┘ │
                                                                └──────────────┬──────────────┘
                                                                               │ Private Subnet
                                                                               ▼
                                                                ┌─────────────────────────────┐
                                                                │  Managed Relational DB      │
                                                                │  (AWS Aurora Serverless v2  │
                                                                │   / GCP Cloud SQL / Azure   │
                                                                │   Flexible Server Postgres) │
                                                                │                             │
                                                                │  • PostgreSQL 16+           │
                                                                │  • pgvector Extension       │
                                                                │  • GiST Exclusion Indexes   │
                                                                │  • Automated Daily Backups  │
                                                                └─────────────────────────────┘
```

---

## 2. Infrastructure as Code (Terraform / OpenTofu)

The repository provides a unified multi-cloud Terraform module structure under `infra/terraform/`:

```
infra/terraform/
├── modules/
│   ├── networking/             # VPC, Public/Private Subnets, NAT Gateways
│   ├── database/               # Managed Postgres 16 with pgvector enabled
│   ├── container_service/      # ECS Fargate / Cloud Run / Azure Container Apps
│   └── secrets/                # AWS Secrets Manager / GCP Secret Manager
├── environments/
│   ├── aws/                    # AWS production environment definitions
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   └── terraform.tfvars.example
│   ├── gcp/                    # GCP production definitions
│   └── azure/                  # Azure production definitions
```

### 2.1 AWS Target Specification (Reference Implementation)
- **Compute**: AWS ECS Fargate (Serverless Containers).
  - CPU/RAM: 2 vCPU, 4GB RAM per task (auto-scaling 2 to 10 tasks based on CPU > 70% or concurrent WebSocket connections).
- **Database**: AWS Aurora PostgreSQL Serverless v2.
  - Scaling: 0.5 to 4 ACUs (Aurora Capacity Units).
  - Extension: `vector` and `btree_gist` pre-installed via Terraform bootstrapping.
- **Networking**: Dual-AZ VPC with public subnets (ALB, NAT) and private isolated subnets (ECS tasks, Aurora DB).
- **Secrets Management**: AWS Secrets Manager automatically injecting LLM API keys (`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GEMINI_API_KEY`), database credentials, and JWT signing secrets directly into container environment variables.

---

## 3. Production Containerization (Multi-Stage Dockerfiles)

### 3.1 Backend Multi-Stage Dockerfile (`backend/Dockerfile`)
```dockerfile
# Stage 1: Dependency Builder using uv
FROM python:3.12-slim-bookworm AS builder
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev git \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project --no-dev

# Stage 2: Runtime Image
FROM python:3.12-slim-bookworm AS runtime
WORKDIR /app

# Non-root security user
RUN groupadd -r cadence && useradd -r -g cadence cadence

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /app/.venv /app/.venv
COPY . /app

ENV PATH="/app/.venv/bin:$PATH"
USER cadence

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD curl -f http://localhost:8000/healthz || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2", "--ws", "websockets"]
```

---

## 4. Production CI/CD & Deployment Pipeline (GitHub Actions)

Every pull request and merge to `main` undergoes a 4-stage pipeline:

```
[ Code Push ] ──► [ Lint & Typecheck ] ──► [ 25-Scenario Eval Suite ] ──► [ Build & Deploy ]
                     • ruff (Lint/Format)     • pytest -m eval              • Push to ECR/Artifact Reg
                     • mypy (Strict Types)    • Zero Hallucination Gate     • ECS / Cloud Run Rolling Update
```

### 4.1 Zero-Downtime Rolling Deployment Strategy
1. **Health Probes**:
   - `/healthz`: Shallow liveness probe (checks process responsiveness).
   - `/readyz`: Deep readiness probe (checks database connection pool, pgvector availability, and MCP tool registry).
2. **Graceful WebSocket Draining**:
   - On `SIGTERM`, the FastAPI gateway stops accepting new WebSocket handshakes.
   - Active LangGraph execution runs are given up to 45 seconds to reach an `interrupt()` or completion checkpoint before container shutdown.

---

## 5. Security Hardening Checklist

- [x] **Non-Root Containers**: Service runs under unprivileged `cadence` user.
- [x] **Zero Plaintext Secrets**: Zero `.env` files committed; all secrets resolved at runtime via IAM role authorization.
- [x] **VPC Data Plane Isolation**: Database resides in private subnets with no public IP address; accessed only via Security Group whitelist from ECS tasks.
- [x] **Egress Filtering**: Outbound network traffic restricted to LLM API endpoints and approved CDN asset storage.
