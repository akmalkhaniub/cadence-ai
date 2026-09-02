# GCP Native Production Terraform
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

variable "gcp_project_id" {
  type    = string
  default = "cadence-production"
}

variable "gcp_region" {
  type    = string
  default = "us-central1"
}

resource "google_sql_database_instance" "postgres" {
  name             = "cadence-cloudsql-prod"
  database_version = "POSTGRES_16"
  region           = var.gcp_region

  settings {
    tier = "db-custom-4-16384"
    database_flags {
      name  = "cloudsql.enable_pgvector"
      value = "on"
    }
  }
}
