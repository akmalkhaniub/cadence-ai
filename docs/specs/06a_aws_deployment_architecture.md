# SPEC 6A: Complete Native AWS Production Deployment Architecture

**Product Name**: Cadence AI  
**Cloud Target**: Amazon Web Services (AWS) Native  
**Document Version**: 1.0.0  
**Status**: APPROVED & FINALIZED  

---

## 1. AWS Architecture Topology

```
                                  ┌────────────────────────────────────────────────────────────┐
                                  │                  Route 53 (DNS / Anycast)                  │
                                  └─────────────────────────────┬──────────────────────────────┘
                                                                │
                                                                ▼
                                  ┌────────────────────────────────────────────────────────────┐
                                  │         CloudFront CDN + AWS WAF (Web App Firewall)        │
                                  │         • DDoS Shield Advanced & SSL Termination           │
                                  │         • Path Routing:                                    │
                                  │           - /assets/*, /* ──► S3 (Vue 3 Static SPA)        │
                                  │           - /api/*, /ws/* ──► ALB (Application Load Bal.) │
                                  └──────────────────────┬──────────────────────┬──────────────┘
                                                         │                      │
                               ┌─────────────────────────┘                      └─────────────────────────┐
                               ▼                                                                          ▼
                ┌──────────────────────────────┐                                           ┌──────────────────────────────┐
                │   S3 Static Website Bucket   │                                           │  Application Load Balancer   │
                │   (Vue 3 SPA, Origin Access) │                                           │  (Public Subnets across AZs) │
                └──────────────────────────────┘                                           └──────────────┬───────────────┘
                                                                                                          │
                                              ┌───────────────────────────────────────────────────────────┴───────────────────────────────────────────────────────────┐
                                              │ AWS VPC (10.0.0.0/16) - Private Application Subnets (Multi-AZ: us-east-1a, us-east-1b)                              │
                                              │                                                                                                                       │
                                              │   ┌────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐  │
                                              │   │ ECS Fargate Cluster (`cadence-prod-cluster`)                                                                   │  │
                                              │   │                                                                                                                │  │
                                              │   │   ┌──────────────────────────────────────────────┐       ┌──────────────────────────────────────────────┐      │  │
                                              │   │   │ Task 1 (AZ-1a): 2 vCPU, 4GB RAM              │       │ Task 2 (AZ-1b): 2 vCPU, 4GB RAM              │      │  │
                                              │   │   │ • FastAPI Gateway + LangGraph Engine         │       │ • FastAPI Gateway + LangGraph Engine         │      │  │
                                              │   │   │ • In-Process FastMCP Server (vFairs Standard)│       │ • In-Process FastMCP Server (vFairs Standard)│      │  │
                                              │   │   └──────────────────────────────────────────────┘       └──────────────────────────────────────────────┘      │  │
                                              │   │                                Auto-Scaling Policy: Target Tracking (CPU > 70% or WS Connections > 500)       │  │
                                              │   └───────────────────────────────────────────────────────┬────────────────────────────────────────────────────────┘  │
                                              │                                                           │                                                           │
                                              │                                                           ▼                                                           │
                                              │   ┌────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐  │
                                              │   │ AWS Private Database Subnets (No Public Route, Strict Security Group Ingress from ECS SG)                      │  │
                                              │   │                                                                                                                │  │
                                              │   │   Amazon Aurora PostgreSQL Serverless v2 (`cadence-aurora-cluster`)                                            │  │
                                              │   │   • PostgreSQL 16.2 with `pgvector` and `btree_gist` extensions                                                │  │
                                              │   │   • Dynamic scaling: 0.5 ACU to 8.0 ACU (1 ACU = ~2GB RAM)                                                     │  │
                                              │   │   • Multi-AZ Synchronous Replication (Zero data loss failover)                                                 │  │
                                              │   │   • Automated Daily Snapshots + 35-day Point-in-Time Recovery (PITR)                                           │  │
                                              │   └────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘  │
                                              └───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. AWS Compute & Container Specification (ECS Fargate)

- **Compute Type**: AWS Fargate (Serverless Container Execution). Zero EC2 instance patching or OS overhead.
- **Task Definition**:
  - `cpu`: `2048` (2 vCPU)
  - `memory`: `4096` (4 GB)
  - `networkMode`: `awsvpc` (Dedicated ENI with private IP in VPC)
- **Container Definition**:
  - `image`: `<aws_account_id>.dkr.ecr.us-east-1.amazonaws.com/cadence-backend:v1.0.0`
  - `essential`: `true`
  - `portMappings`: Port `8000` (HTTP/WebSocket)
  - `healthCheck`:
    - Command: `["CMD-SHELL", "curl -f http://localhost:8000/healthz || exit 1"]`
    - Interval: 30s, Timeout: 5s, Retries: 3, StartPeriod: 15s
- **Auto-Scaling Strategy**:
  - Minimum Tasks: 2 (Multi-AZ redundancy).
  - Maximum Tasks: 10.
  - Scaling Metric 1: Average CPU Utilization > 70% over 2 minutes.
  - Scaling Metric 2: Application Load Balancer `ActiveConnectionCount` > 500 per task (handles concurrent long-lived WebSockets).

---

## 3. Storage & Relational Database (Aurora PostgreSQL + pgvector)

- **Database Engine**: Amazon Aurora PostgreSQL Serverless v2 (PostgreSQL 16.2).
- **Extensions Bootstrapped via Terraform**:
  ```sql
  CREATE EXTENSION IF NOT EXISTS "vector";
  CREATE EXTENSION IF NOT EXISTS "btree_gist";
  CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
  ```
- **Storage Auto-Scaling**: 10 GB up to 128 TB automatically without downtime.
- **Connection Pooling**: AWS RDS Proxy enabled to manage up to 5,000 pooled connections, mitigating connection thrashing during bursty multi-agent fan-out.
- **High Availability**: Multi-AZ reader endpoint configured in alternate availability zone for read-heavy vector similarity queries.

---

## 4. Networking, Security & IAM Least-Privilege

### 4.1 VPC Subnet Topology
- **VPC CIDR**: `10.0.0.0/16`
- **Public Subnets**: `10.0.1.0/24` (AZ-a), `10.0.2.0/24` (AZ-b) — Hosts NAT Gateways and ALB.
- **Private App Subnets**: `10.0.10.0/24` (AZ-a), `10.0.20.0/24` (AZ-b) — Hosts ECS Fargate tasks.
- **Private DB Subnets**: `10.0.30.0/24` (AZ-a), `10.0.40.0/24` (AZ-b) — Hosts Aurora Serverless cluster.

### 4.2 Security Group Rules
- **ALB Security Group**: Ingress port 443/80 from `0.0.0.0/0`. Egress port 8000 to ECS SG.
- **ECS Security Group**: Ingress port 8000 strictly from ALB SG. Egress port 5432 to Aurora SG; egress 443 to NAT Gateway (for LLM API calls).
- **Aurora Security Group**: Ingress port 5432 strictly from ECS SG and RDS Proxy SG. Zero egress.

### 4.3 IAM Roles & Secrets Management
- **ECS Task Execution Role**: Grants permissions to pull images from ECR and write logs to CloudWatch Logs.
- **ECS Task Role**:
  - `secretsmanager:GetSecretValue`: Retrieves `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, and `DATABASE_URL` from AWS Secrets Manager.
  - `s3:PutObject` / `s3:GetObject`: Scoped access to event brief bucket (`s3://cadence-briefs-prod/*`).

---

## 5. AWS Terraform Implementation

The full AWS infrastructure is codified in `infra/terraform/aws/`:

```hcl
# infra/terraform/aws/main.tf
terraform {
  required_version = ">= 1.8.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.50"
    }
  }
}

provider "aws" {
  region = var.aws_region
  default_tags {
    tags = {
      Environment = "Production"
      Project     = "Cadence-AI"
      ManagedBy   = "Terraform"
    }
  }
}

# ECS Fargate Cluster
resource "aws_ecs_cluster" "cadence" {
  name = "cadence-prod-cluster"
  setting {
    name  = "containerInsights"
    value = "enabled"
  }
}

# Aurora PostgreSQL Serverless v2
resource "aws_rds_cluster" "aurora" {
  cluster_identifier      = "cadence-aurora-cluster"
  engine                  = "aurora-postgresql"
  engine_version          = "16.2"
  database_name           = "cadence_prod"
  master_username         = "cadence_admin"
  manage_master_user_password = true
  serverlessv2_scaling_configuration {
    min_capacity = 0.5
    max_capacity = 8.0
  }
  vpc_security_group_ids  = [aws_security_group.db.id]
  db_subnet_group_name    = aws_db_subnet_group.cadence.name
  skip_final_snapshot     = false
  final_snapshot_identifier = "cadence-aurora-final"
}
```

---

## 6. Monitoring, Observability & SLOs

- **Metrics**: AWS CloudWatch Container Insights collects CPU, memory, and network I/O per task.
- **Distributed Tracing**: AWS X-Ray and OpenTelemetry Collector sidecar shipping traces to LangSmith / Phoenix.
- **Alarms**:
  - `P1 Alert`: Aurora CPU > 85% for 5 minutes.
  - `P1 Alert`: ALB 5XX rate > 1% over 2 minutes.
  - `P2 Alert`: ECS auto-scaling hits maximum 10 tasks.
