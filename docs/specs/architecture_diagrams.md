# Architectural Visual Blueprints & Cloud Topology Diagrams

**Product Name**: Cadence AI  
**Document Version**: 1.0.0  
**Status**: APPROVED & FINALIZED  
**Scope**: High-Resolution Mermaid Diagrams for AWS, GCP, Azure, Multi-Cloud Federation, and Agentic Data Flows  

---

## 1. End-to-End System & Dual-Graph Workflow

This diagram illustrates how raw inputs flow through the FastAPI gateway, LangGraph state machines, FastMCP server, and down to the persistent database.

```mermaid
flowchart TB
    subgraph ClientLayer ["Client & Ingestion Layer"]
        UI["Vue 3 SPA Dashboard<br/>(Desktop Organizer / Live HUD)"]
        Upload["File Ingestion<br/>(PDF Briefs, CSV Rosters, Contracts)"]
        WS["WebSocket Stream<br/>(Live Tokens & State Events)"]
    end

    subgraph GatewayLayer ["API Gateway & Security"]
        WAF["Cloud WAF & DDoS Shield"]
        FastAPI["FastAPI Gateway (ASGI)<br/>Auth, Tenant RLS Context, WS Manager"]
        RedisCache["Redis 7<br/>Session Cache & Idempotency Store"]
    end

    subgraph AgentLayer ["LangGraph Agent Core"]
        direction TB
        subgraph GraphA ["Graph A: Pre-Event Provisioning Engine"]
            Parser["1. Intent & Brief Parser"] --> Planner["2. Topological DAG Planner"]
            Planner --> Verifier{"3. Physics & Constraint Verifier"}
            Verifier -- "Collision Detected (Iteration < 3)" --> Planner
            Verifier -- "Valid Plan" --> HITL["4. HITL Approval Gate (interrupt)"]
            HITL -- "User Rejection + Feedback" --> Planner
            HITL -- "User Approved" --> Dispatcher["5. Sub-Agent Dispatcher"]
            Dispatcher --> WorkerAgenda["Agenda Worker"]
            Dispatcher --> WorkerBooth["Booth Worker"]
            Dispatcher --> WorkerTicket["Ticket Worker"]
        end

        subgraph GraphB ["Graph B: Live Ops Incident Triage Engine"]
            Telemetry["Live Telemetry Event<br/>(Speaker No-Show / Stream 502)"] --> Analyzer["Impact & Ripple Analyzer"]
            Analyzer --> Remediation["Remediation Option Generator"]
            Remediation --> UrgentHITL{"Urgent HITL Gate (Single-Click)"}
            UrgentHITL --> CascadeExec["Cascade Shift & Push Broadcast"]
        end
    end

    subgraph ProtocolLayer ["Model Context Protocol (MCP)"]
        MCPClient["LangGraph MCP Client"]
        MCPServer["vFairs FastMCP Server<br/>(Strict JSONSchema & Validation)"]
        Journal["Transaction Journal<br/>(Saga Reverse Compensation Log)"]
    end

    subgraph PersistenceLayer ["Data & Vector Plane"]
        PG[("PostgreSQL 16 Engine")]
        GiST["GiST Exclusion Index<br/>(no_room_overlap)"]
        VectorStore["pgvector HNSW Indexes<br/>(Speakers, Abstracts, Attendees)"]
        Checkpoints["PostgresSaver<br/>(LangGraph Checkpoint Storage)"]
    end

    subgraph ObservabilityLayer ["Self-Hosted LLM Telemetry"]
        Langfuse["Langfuse Server<br/>(Spans, Cost Ledger, Prompt CMS)"]
    end

    UI --> WAF --> FastAPI
    Upload --> FastAPI
    FastAPI <--> WS
    FastAPI <--> RedisCache
    FastAPI --> GraphA
    FastAPI --> GraphB
    
    WorkerAgenda & WorkerBooth & WorkerTicket & CascadeExec --> MCPClient
    MCPClient <--> MCPServer
    MCPServer --> Journal
    MCPServer --> PG
    PG --- GiST
    PG --- VectorStore
    GraphA & GraphB <--> Checkpoints
    Checkpoints --> PG

    GraphA & GraphB -.->|Telemetry Spans| Langfuse
```

---

## 2. AWS Native Production Deployment Architecture

```mermaid
flowchart TB
    subgraph Edge ["AWS Global Edge Network"]
        R53["Amazon Route 53 (DNS)"]
        CF["Amazon CloudFront CDN"]
        WAF_AWS["AWS WAF (Web Application Firewall)"]
        S3_Web["Amazon S3 Bucket<br/>(Vue 3 Static SPA Assets)"]
    end

    subgraph VPC ["AWS Virtual Private Cloud (10.0.0.0/16) - Multi-AZ"]
        subgraph PublicSubnets ["Public Subnets (10.0.1.0/24, 10.0.2.0/24)"]
            ALB["Application Load Balancer (ALB)<br/>(TLS 1.3, Path Routing /api & /ws)"]
            NAT["NAT Gateways (AZ-1a, AZ-1b)"]
        end

        subgraph PrivateAppSubnets ["Private Application Subnets (10.0.10.0/24, 10.0.20.0/24)"]
            subgraph ECSCluster ["AWS ECS Fargate Cluster"]
                Task1["ECS Task 1 (AZ-1a)<br/>FastAPI + LangGraph + FastMCP<br/>2 vCPU, 4GB RAM"]
                Task2["ECS Task 2 (AZ-1b)<br/>FastAPI + LangGraph + FastMCP<br/>2 vCPU, 4GB RAM"]
                AutoScaler["Fargate Auto-Scaler<br/>(Target Tracking: CPU > 70% | WS > 500)"]
            end
            LangfuseECS["Self-Hosted Langfuse Task<br/>(Private Subnet)"]
        end

        subgraph PrivateDBSubnets ["Private Isolated Database Subnets (10.0.30.0/24, 10.0.40.0/24)"]
            AuroraMaster[("Amazon Aurora Serverless v2<br/>PostgreSQL 16 + pgvector (Writer)")]
            AuroraReplica[("Amazon Aurora Serverless v2<br/>Read Replica (AZ-1b)")]
            RDSProxy["Amazon RDS Proxy<br/>(Connection Pooling)"]
        end
    end

    subgraph SecurityServices ["Security & Configuration"]
        SecretsMgr["AWS Secrets Manager<br/>(API Keys, DB Credentials)"]
        ECR["Amazon Elastic Container Registry (ECR)"]
        CloudWatch["CloudWatch Container Insights"]
    end

    R53 --> CF
    CF --> WAF_AWS
    WAF_AWS -->|Path: /*| S3_Web
    WAF_AWS -->|Path: /api/*, /ws/*| ALB
    ALB --> Task1 & Task2
    Task1 & Task2 --> RDSProxy --> AuroraMaster
    AuroraMaster -.->|Synchronous Replication| AuroraReplica
    Task1 & Task2 -.->|Egress via NAT| SecretsMgr
    Task1 & Task2 -.->|Telemetry| LangfuseECS
    Task1 & Task2 -.-> CloudWatch
```

---

## 3. GCP Native Production Deployment Architecture

```mermaid
flowchart TB
    subgraph GCPEdge ["Google Cloud Global Edge"]
        CloudDNS["Google Cloud DNS"]
        GLB["Global External HTTPS Load Balancer"]
        CloudArmor["Cloud Armor WAF (Layer 7 Defense)"]
        CloudCDN["Cloud CDN"]
        GCS_Bucket["Google Cloud Storage Bucket<br/>(Vue 3 SPA Assets)"]
    end

    subgraph GCPVPC ["Google Cloud VPC Network (10.128.0.0/16) - us-central1"]
        subgraph ServerlessNEG ["Serverless Network Endpoint Group"]
            subgraph CloudRunService ["Cloud Run (v2) Service: cadence-backend-prod"]
                CR_Inst1["Cloud Run Instance 1<br/>2 vCPU, 4GB RAM, Concurrency: 80"]
                CR_Inst2["Cloud Run Instance 2<br/>2 vCPU, 4GB RAM, Concurrency: 80"]
                CR_Autoscale["Cloud Run Auto-Scaler<br/>(Min: 2 instances, Max: 20 instances)"]
            end
        end

        VPCAccess["Direct VPC Egress / Serverless VPC Access Connector"]

        subgraph PrivateServiceConnect ["Private Service Access (PSA) Subnet"]
            CloudSQLMaster[("Cloud SQL for PostgreSQL 16<br/>Enterprise Plus (Regional Master)<br/>pgvector enabled")]
            CloudSQLStandby[("Cloud SQL Standby Replica<br/>(Automatic Regional Failover)")]
        end

        subgraph LangfuseSubnet ["Telemetry Subnet"]
            LangfuseCR["Langfuse Cloud Run Instance"]
        end
    end

    subgraph GCPSecurity ["Identity & Security"]
        SecretMgr["Google Secret Manager"]
        WorkloadID["Workload Identity Federation"]
        CloudTrace["Google Cloud Trace & Logging"]
    end

    CloudDNS --> GLB
    GLB --> CloudArmor
    CloudArmor --> CloudCDN
    CloudCDN -->|Path: /*| GCS_Bucket
    CloudCDN -->|Path: /api/*, /ws/*| ServerlessNEG
    ServerlessNEG --> CR_Inst1 & CR_Inst2
    CR_Inst1 & CR_Inst2 --> VPCAccess --> CloudSQLMaster
    CloudSQLMaster -.->|High Availability Sync| CloudSQLStandby
    CR_Inst1 & CR_Inst2 -.-> SecretMgr
    CR_Inst1 & CR_Inst2 -.-> LangfuseCR
    CR_Inst1 & CR_Inst2 -.-> CloudTrace
```

---

## 4. Azure Native Production Deployment Architecture

```mermaid
flowchart TB
    subgraph AzureEdge ["Azure Global Network"]
        AzureDNS["Azure DNS (Anycast)"]
        AFD["Azure Front Door Premium (Global CDN)"]
        AFDWAF["Front Door WAF Policies"]
        BlobStatic["Azure Blob Storage ($web)<br/>(Vue 3 SPA Static Hosting)"]
    end

    subgraph AzureVNet ["Azure Virtual Network (10.240.0.0/16) - East US 2"]
        subgraph ACASubnet ["Container Apps Subnet (10.240.1.0/23)"]
            subgraph ACAEnv ["Azure Container Apps (ACA) Environment"]
                Replica1["ACA Replica 1 (Zone 1)<br/>FastAPI + LangGraph + FastMCP<br/>2.0 vCPU, 4.0 GiB RAM"]
                Replica2["ACA Replica 2 (Zone 2)<br/>FastAPI + LangGraph + FastMCP<br/>2.0 vCPU, 4.0 GiB RAM"]
                KEDA["KEDA Scaler (HTTP Concurrency > 60)"]
            end
            LangfuseACA["Langfuse Container App"]
        end

        subgraph DBSubnet ["Delegated PostgreSQL Subnet (10.240.4.0/24)"]
            PG_FlexMaster[("Azure Database for PostgreSQL<br/>Flexible Server (Primary Node)<br/>pgvector & btree_gist")]
            PG_FlexStandby[("Zone-Redundant Standby Replica<br/>(Synchronous Zone 2)")]
        end
    end

    subgraph AzureIdentity ["Identity & Secrets"]
        KeyVault["Azure Key Vault (Managed Identity)"]
        ACR["Azure Container Registry (ACR)"]
        AppInsights["Azure Application Insights"]
    end

    AzureDNS --> AFD
    AFD --> AFDWAF
    AFDWAF -->|Path: /*| BlobStatic
    AFDWAF -->|Path: /api/*, /ws/* via Private Link| Replica1 & Replica2
    Replica1 & Replica2 --> PG_FlexMaster
    PG_FlexMaster -.->|Zone Redundant Sync| PG_FlexStandby
    Replica1 & Replica2 -.-> KeyVault
    Replica1 & Replica2 -.-> LangfuseACA
    Replica1 & Replica2 -.-> AppInsights
```

---

## 5. Multi-Cloud Federation & Cross-Cloud Disaster Recovery Topology

```mermaid
flowchart TB
    subgraph AnycastEdge ["Global Traffic Orchestration"]
        CF_Anycast["Cloudflare Global Anycast Network"]
        CF_TrafficMgr["Multi-Cloud Traffic Manager & Health Probes"]
        CF_WAF["Cloudflare Web Application Firewall"]
    end

    subgraph CloudAWS ["Cloud 1: AWS (Primary Region - 70% Traffic)"]
        AWS_ALB["AWS Application Load Balancer"]
        AWS_Fargate["AWS ECS Fargate Cluster"]
        AWS_Aurora[("Amazon Aurora PostgreSQL v2<br/>(Global Master Write Node)")]
    end

    subgraph CloudGCP ["Cloud 2: GCP (Secondary Region - 30% Traffic)"]
        GCP_GLB["Google Cloud Load Balancer"]
        GCP_CloudRun["Cloud Run Backend Service"]
        GCP_CloudSQL[("GCP Cloud SQL PostgreSQL 16<br/>(Logical Read/Standby Replica)")]
    end

    subgraph CloudAzure ["Cloud 3: Azure (Disaster Recovery Hot Standby)"]
        Azure_AFD["Azure Front Door"]
        Azure_ACA["Azure Container Apps"]
        Azure_PGFlex[("Azure PostgreSQL Flexible Server<br/>(Disaster Recovery Replica)")]
    end

    CF_Anycast --> CF_WAF --> CF_TrafficMgr
    CF_TrafficMgr -- "Primary (Health OK)" --> AWS_ALB
    CF_TrafficMgr -- "Secondary (Geo EMEA/APAC)" --> GCP_GLB
    CF_TrafficMgr -- "Failover Trigger (RTO < 3m)" --> Azure_AFD

    AWS_ALB --> AWS_Fargate --> AWS_Aurora
    GCP_GLB --> GCP_CloudRun --> GCP_CloudSQL
    Azure_AFD --> Azure_ACA --> Azure_PGFlex

    AWS_Aurora == "Asynchronous Logical Stream (pglogical)" ==> GCP_CloudSQL
    AWS_Aurora == "Asynchronous Logical Stream (pglogical)" ==> Azure_PGFlex
```

---

## 6. Live Incident Cascade Sequence Diagram

This sequence diagram illustrates how Graph B handles a real-time speaker no-show under 3 seconds:

```mermaid
sequenceDiagram
    autonumber
    actor Organizer as Event Director (Vue 3 HUD)
    participant Telemetry as Backstage Telemetry
    participant Gateway as FastAPI Gateway
    participant GraphB as LangGraph Incident Engine
    participant VectorDB as PostgreSQL + pgvector
    participant MCP as vFairs FastMCP Server
    participant Attendees as 450 Registered Attendees

    Telemetry->>Gateway: Webhook: SPEAKER_ABSENT (Session 402, 15m to start)
    Gateway->>GraphB: Initialize Live Triage Thread (incident_772)
    GraphB->>VectorDB: Query pre-recorded assets & matching speaker embeddings
    VectorDB-->>GraphB: Candidate: "Autonomous Tool Use" (Similarity: 0.89, Asset Ready)
    GraphB->>GraphB: Calculate Ripple Shift on downstream Track 1 sessions
    GraphB->>Gateway: Emit HITL_INTERRUPT over WebSocket
    Gateway->>Organizer: Display Urgent Triage Card (Ranked 3 Options)
    
    Note over Organizer: Review card (1.8s elapsed)<br/>Selects Option 1: Swap Asset
    
    Organizer->>Gateway: Submit Decision: APPROVED_OPTION_1
    Gateway->>GraphB: Resume LangGraph interrupt()
    GraphB->>MCP: sessions.update_session_media(session_402, asset_url)
    MCP->>VectorDB: Update session state to BACKSTAGE_READY
    GraphB->>MCP: notifications.broadcast_push(title="Speaker Update", session_402)
    MCP->>Attendees: Send Mobile Push Notification & In-Lobby Alert
    GraphB->>Gateway: Emit INCIDENT_RESOLVED
    Gateway->>Organizer: Update Live Timeline (Green Status)
```
