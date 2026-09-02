# AWS Native Production Terraform
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
}

variable "aws_region" {
  type    = string
  default = "us-east-1"
}

resource "aws_ecs_cluster" "cadence" {
  name = "cadence-prod-cluster"
}

resource "aws_rds_cluster" "aurora" {
  cluster_identifier = "cadence-aurora-cluster"
  engine             = "aurora-postgresql"
  engine_version     = "16.2"
  database_name      = "cadence_prod"
  master_username    = "cadence_admin"
  manage_master_user_password = true

  serverlessv2_scaling_configuration {
    min_capacity = 0.5
    max_capacity = 8.0
  }
  skip_final_snapshot = true
}
