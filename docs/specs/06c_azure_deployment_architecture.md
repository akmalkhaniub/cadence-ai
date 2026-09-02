# SPEC 6C: Complete Native Azure Production Deployment Architecture

**Product Name**: Cadence AI  
**Cloud Target**: Microsoft Azure Native  
**Document Version**: 1.0.0  
**Status**: APPROVED & FINALIZED  

---

## 1. Azure Architecture Topology

```
                                  ┌────────────────────────────────────────────────────────────┐
                                  │                  Azure DNS (Global Anycast)                │
                                  └─────────────────────────────┬──────────────────────────────┘
                                                                │
                                                                ▼
                                  ┌────────────────────────────────────────────────────────────┐
                                  │       Azure Front Door Premium + Web Application Firewall  │
                                  │       • Global Layer 7 CDN with Edge TLS 1.3 Termination   │
                                  │       • Front Door WAF Policies (DDoS & Threat Protection) │
                                  │       • Routing Rules:                                     │
                                  │         - /* ───────────► Azure Storage Static Website     │
                                  │         - /api/*, /ws/* ─► Container Apps via Private Link │
                                  └──────────────────────┬──────────────────────┬──────────────┘
                                                         │                      │
                               ┌─────────────────────────┘                      └─────────────────────────┐
                               ▼                                                                          ▼
                ┌──────────────────────────────┐                                           ┌──────────────────────────────┐
                │ Azure Blob Storage Account   │                                           │ Azure Front Door Origin      │
                │ ($web Static Website Hosting)│                                           │ (Internal Ingress FQDN)      │
                └──────────────────────────────┘                                           └──────────────┬───────────────┘
                                                                                                          │
                                              ┌───────────────────────────────────────────────────────────┴───────────────────────────────────────────────────────────┐
                                              │ Azure Virtual Network (10.240.0.0/16) - East US 2 Region                                                              │
                                              │                                                                                                                       │
                                              │   ┌────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐  │
                                              │   │ Container Apps Subnet (10.240.1.0/23)                                                                          │  │
                                              │   │ Azure Container Apps (ACA) Environment (`cadence-aca-prod`)                                                    │  │
                                              │   │                                                                                                                │  │
                                              │   │   • 2.0 vCPU, 4.0 GiB Memory per replica                                                                       │  │
                                              │   │   • Native KEDA Auto-Scalers: HTTP Concurrent Requests > 60 or CPU > 70%                                       │  │
                                              │   │   • Replicas: Min = 2 (Zone Redundant), Max = 20                                                               │  │
                                              │   │   • System-Assigned Managed Identity (Passwordless Key Vault & ACR Auth)                                       │  │
                                              │   └───────────────────────────────────────────────────────┬────────────────────────────────────────────────────────┘  │
                                              │                                                           │                                                           │
                                              │                                                           ▼ Delegated VNet Ingress                                    │
                                              │   ┌────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐  │
                                              │   │ Delegated PostgreSQL Subnet (10.240.4.0/24)                                                                    │  │
                                              │   │                                                                                                                │  │
                                              │   │   Azure Database for PostgreSQL - Flexible Server (`cadence-pg-prod`)                                          │  │
                                              │   │   • SKU: `Standard_D4ds_v5` (4 vCPU, 16 GiB RAM)                                                               │  │
                                              │   │   • Engine: PostgreSQL 16 with `vector` and `btree_gist` extensions enabled                                    │  │
                                              │   │   • High Availability: Zone-Redundant (Synchronous standby replica in AZ 2)                                   │  │
                                              │   │   • Private VNet Integration (Completely unreachable from public internet)                                     │  │
                                              │   │   • Automated Geo-Redundant Backup Storage (GRS)                                                               │  │
                                              │   └────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘  │
                                              └───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Azure Compute Specification (Azure Container Apps)

- **Platform**: Azure Container Apps (built on managed Kubernetes and KEDA).
- **Workload Profile**:
  - `cpu`: `2.0`
  - `memory`: `4.0Gi`
- **Networking & Ingress**:
  - `external`: `true` (via Front Door Private Link)
  - `targetPort`: `8000`
  - `transport`: `http2` / `tcp` with native WebSocket support.
- **KEDA Auto-Scaling Triggers**:
  ```yaml
  scale:
    minReplicas: 2
    maxReplicas: 20
    rules:
      - name: http-scaling
        custom:
          type: http
          metadata:
            concurrentRequests: "60"
      - name: cpu-scaling
        custom:
          type: cpu
          metadata:
            type: Utilization
            value: "70"
  ```
- **Zone Redundancy**: Enabled across Availability Zones 1, 2, and 3.

---

## 3. Storage & Relational Database (PostgreSQL Flexible Server)

- **Service**: Azure Database for PostgreSQL Flexible Server.
- **Compute Tier**: General Purpose `Standard_D4ds_v5` (4 cores, 16 GB memory).
- **Extensions Activated via Server Parameters**:
  - `azure.extensions`: `"VECTOR,BTREE_GIST,UUID-OSSP"`
- **High Availability**: Zone-Redundant HA with automatic failure detection and failover under 60 seconds without data loss.
- **VNet Integration**: Delegated subnet `10.240.4.0/24`, enforcing zero public internet connectivity.

---

## 4. Security, Managed Identity & Azure Key Vault

### 4.1 System-Assigned Managed Identity
- Container Apps authenticate to Azure Container Registry (ACR) and Azure Key Vault without client secrets or passwords.
- Role Assignments:
  - `Key Vault Secrets User` on `kv-cadence-prod`.
  - `AcrPull` on `acrcadenceprod`.
  - `Storage Blob Data Contributor` on Event Briefs storage container.

### 4.2 Azure Key Vault Secrets
- Houses third-party API keys:
  - `OPENAI-API-KEY`
  - `ANTHROPIC-API-KEY`
  - `GEMINI-API-KEY`
  - `JWT-SIGNING-KEY`

---

## 5. Azure Terraform Implementation

Codified in `infra/terraform/azure/`:

```hcl
# infra/terraform/azure/main.tf
terraform {
  required_version = ">= 1.8.0"
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.100"
    }
  }
}

provider "azurerm" {
  features {}
}

# PostgreSQL Flexible Server with Zone Redundancy
resource "azurerm_postgresql_flexible_server" "postgres" {
  name                   = "cadence-pg-prod"
  resource_group_name    = azurerm_resource_group.rg.name
  location               = azurerm_resource_group.rg.location
  version                = "16"
  delegated_subnet_id    = azurerm_subnet.postgres.id
  private_dns_zone_id    = azurerm_private_dns_zone.postgres.id
  sku_name               = "GP_Standard_D4ds_v5"
  storage_mb             = 131072
  zone                   = "1"

  high_availability {
    mode                      = "ZoneRedundant"
    standby_availability_zone = "2"
  }
}

resource "azurerm_postgresql_flexible_server_configuration" "pgvector" {
  name      = "azure.extensions"
  server_id = azurerm_postgresql_flexible_server.postgres.id
  value     = "VECTOR,BTREE_GIST,UUID-OSSP"
}

# Container App Environment & App
resource "azurerm_container_app_environment" "env" {
  name                     = "cadence-aca-env"
  resource_group_name      = azurerm_resource_group.rg.name
  location                 = azurerm_resource_group.rg.location
  infrastructure_subnet_id = azurerm_subnet.aca.id
  zone_redundancy_enabled  = true
}

resource "azurerm_container_app" "backend" {
  name                         = "cadence-backend"
  container_app_environment_id = azurerm_container_app_environment.env.id
  resource_group_name          = azurerm_resource_group.rg.name
  revision_mode                = "Single"

  identity {
    type = "SystemAssigned"
  }

  template {
    min_replicas = 2
    max_replicas = 20
    container {
      name   = "cadence-api"
      image  = "acrcadenceprod.azurecr.io/cadence-backend:v1.0.0"
      cpu    = 2.0
      memory = "4Gi"
      readiness_probe {
        path      = "/readyz"
        port      = 8000
        transport = "HTTP"
      }
    }
  }
}
```

---

## 6. Azure Monitor & Application Insights

- **Application Insights SDK**: Integrated into FastAPI via OpenTelemetry Azure exporter.
- **Dashboards**:
  - Live Stream telemetry (WebSocket count, connect/disconnect churn).
  - Flexible Server IOPS, storage burn rate, and replication lag.
  - End-to-end trace correlation linking Azure Front Door requests directly to LangGraph state transitions.
