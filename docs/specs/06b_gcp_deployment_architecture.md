# SPEC 6B: Complete Native GCP Production Deployment Architecture

**Product Name**: Cadence AI  
**Cloud Target**: Google Cloud Platform (GCP) Native  
**Document Version**: 1.0.0  
**Status**: APPROVED & FINALIZED  

---

## 1. GCP Architecture Topology

```
                                  ┌────────────────────────────────────────────────────────────┐
                                  │                  Cloud DNS (Global Anycast)                │
                                  └─────────────────────────────┬──────────────────────────────┘
                                                                │
                                                                ▼
                                  ┌────────────────────────────────────────────────────────────┐
                                  │       Global External Application Load Balancer (HTTPS)    │
                                  │       • Cloud Armor WAF (Layer 7 Defense & Rate Limiting)  │
                                  │       • Cloud CDN (Global edge caching)                    │
                                  │       • Path Routing:                                      │
                                  │         - /* ───────────► Cloud Storage Backend Bucket     │
                                  │         - /api/*, /ws/* ─► Serverless Network Endpoint (NEG)│
                                  └──────────────────────┬──────────────────────┬──────────────┘
                                                         │                      │
                               ┌─────────────────────────┘                      └─────────────────────────┐
                               ▼                                                                          ▼
                ┌──────────────────────────────┐                                           ┌──────────────────────────────┐
                │ Cloud Storage (GCS Bucket)   │                                           │ Serverless NEG (Cloud Run)   │
                │ (Vue 3 Static SPA Assets)    │                                           │ (Regional Backend Service)   │
                └──────────────────────────────┘                                           └──────────────┬───────────────┘
                                                                                                          │
                                              ┌───────────────────────────────────────────────────────────┴───────────────────────────────────────────────────────────┐
                                              │ Google Cloud VPC (10.128.0.0/16) - Region: us-central1 (Council Bluffs)                                               │
                                              │                                                                                                                       │
                                              │   ┌────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐  │
                                              │   │ Cloud Run Service (`cadence-backend-prod`)                                                                     │  │
                                              │   │                                                                                                                │  │
                                              │   │   • 2 vCPU, 4GB Memory per container instance                                                                  │  │
                                              │   │   • Concurrency: 80 concurrent requests/WebSockets per container                                               │  │
                                              │   │   • Auto-scaling: Min Instances = 2 (Warm Zero-Cold-Start), Max Instances = 20                                 │  │
                                              │   │   • Direct VPC Egress / Serverless VPC Access Connector                                                        │  │
                                              │   │   • Service Account: `cadence-runner@project.iam.gserviceaccount.com`                                          │  │
                                              │   └───────────────────────────────────────────────────────┬────────────────────────────────────────────────────────┘  │
                                              │                                                           │                                                           │
                                              │                                                           ▼ Internal IP (Direct VPC Egress)                           │
                                              │   ┌────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐  │
                                              │   │ Private Service Connect (PSA) Subnet                                                                           │  │
                                              │   │                                                                                                                │  │
                                              │   │   Cloud SQL for PostgreSQL 16 (`cadence-cloudsql-instance`)                                                    │  │
                                              │   │   • Tier: `db-custom-4-16384` (4 vCPU, 16GB RAM)                                                               │  │
                                              │   │   • Database flags: `cloudsql.enable_pgvector = on`                                                            │  │
                                              │   │   • High Availability (Regional failover across us-central1-a and us-central1-b)                               │  │
                                              │   │   • Private IP only (No public IPv4 assigned)                                                                  │  │
                                              │   │   • Automated point-in-time recovery & automated backups                                                       │  │
                                              │   └────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘  │
                                              └───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. GCP Compute Specification (Cloud Run v2)

- **Execution Environment**: Google Cloud Run v2 (Fully Managed Container Platform).
- **Resource Sizing**:
  - `cpu`: `2` (2 vCPU, dedicated CPU allocation during request handling)
  - `memory`: `4Gi` (4 GB RAM)
  - `concurrency`: `80` (optimized for long-lived WebSocket connections and async event processing)
  - `execution_environment`: `EXECUTION_ENVIRONMENT_GEN2`
- **Session Affinity & WebSockets**:
  - WebSockets enabled natively with HTTP/2 and streaming HTTP responses.
  - Session affinity enabled via generated client cookies to pin WebSocket reconnects to warm instances.
- **Scaling Thresholds**:
  - `min_instances`: `2` (eliminates cold starts; ensures multi-zone presence).
  - `max_instances`: `20` (auto-scales dynamically under peak concurrent event traffic).
- **Direct VPC Egress**:
  - Routes container traffic into the private VPC subnet without passing through the public internet, connecting directly to Cloud SQL.

---

## 3. Storage & Relational Database (Cloud SQL with pgvector)

- **Database Engine**: Cloud SQL for PostgreSQL 16 (Enterprise Plus Edition).
- **Extensions Bootstrapped via Terraform**:
  ```sql
  CREATE EXTENSION IF NOT EXISTS "vector";
  CREATE EXTENSION IF NOT EXISTS "btree_gist";
  CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
  ```
- **Database Flags**:
  - `cloudsql.enable_pgvector`: `on`
  - `max_connections`: `1000`
  - `shared_buffers`: `4GB`
- **Zero Public IP**: Configured exclusively via Private Service Access (RFC 1918 private peering).
- **Storage Auto-Resize**: Enabled up to 10 TB with automatic capacity scaling.

---

## 4. Security, IAM & Workload Identity

### 4.1 Service Account & Least-Privilege IAM
- Dedicated Service Account: `sa-cadence-agent@cadence-production.iam.gserviceaccount.com`
- Attached IAM Roles:
  - `roles/secretmanager.secretAccessor`: Access to `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, and `DB_PASSWORD`.
  - `roles/cloudsql.client`: Authorizes encrypted SSL connections to Cloud SQL.
  - `roles/storage.objectAdmin`: Access strictly scoped to `gs://cadence-event-briefs-prod/*`.
  - `roles/logging.logWriter` and `roles/cloudtrace.agent`: Telemetry shipping.

### 4.2 Cloud Armor WAF & DDoS
- Attached to Global External Load Balancer:
  - Rate limiting: Max 100 requests per 10 seconds per client IP.
  - Geo-blocking: Configurable per tenant restrictions.
  - OWASP Top 10 pre-configured rulesets blocking SQLi, XSS, and LFI.

---

## 5. GCP Terraform Implementation

Codified under `infra/terraform/gcp/`:

```hcl
# infra/terraform/gcp/main.tf
terraform {
  required_version = ">= 1.8.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.30"
    }
  }
}

provider "google" {
  project = var.gcp_project_id
  region  = var.gcp_region
}

# Cloud SQL PostgreSQL 16 with pgvector
resource "google_sql_database_instance" "postgres" {
  name             = "cadence-cloudsql-prod"
  database_version = "POSTGRES_16"
  region           = var.gcp_region

  settings {
    tier              = "db-custom-4-16384"
    availability_type = "REGIONAL" # Multi-Zone HA
    disk_size         = 50
    disk_autoresize   = true

    database_flags {
      name  = "cloudsql.enable_pgvector"
      value = "on"
    }

    ip_configuration {
      ipv4_enabled    = false
      private_network = google_compute_network.vpc.id
    }

    backup_configuration {
      enabled                        = true
      point_in_time_recovery_enabled = true
    }
  }
}

# Cloud Run Service (v2)
resource "google_cloud_run_v2_service" "backend" {
  name     = "cadence-backend-prod"
  location = var.gcp_region
  ingress  = "INGRESS_TRAFFIC_INTERNAL_LOAD_BALANCER"

  template {
    scaling {
      min_instance_count = 2
      max_instance_count = 20
    }
    containers {
      image = "gcr.io/${var.gcp_project_id}/cadence-backend:v1.0.0"
      resources {
        limits = {
          cpu    = "2"
          memory = "4Gi"
        }
      }
      ports {
        container_port = 8000
      }
      liveness_probe {
        http_get {
          path = "/healthz"
          port = 8000
        }
        period_seconds = 30
      }
    }
    vpc_access {
      network_interfaces {
        network    = google_compute_network.vpc.id
        subnetwork = google_compute_subnetwork.subnet.id
      }
    }
  }
}
```

---

## 6. Observability & SLO Management

- **Google Cloud Trace**: End-to-end distributed transaction tracing with sub-millisecond span resolution.
- **Google Cloud Monitoring (Stackdriver)**: Custom dashboards tracking:
  - Active WebSocket connections per container instance.
  - LangGraph task execution duration percentiles (p50, p95, p99).
  - Cloud SQL IOPS and connection pool saturation alerts.
