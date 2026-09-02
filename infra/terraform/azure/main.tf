# Azure Native Production Terraform
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

variable "location" {
  type    = string
  default = "eastus2"
}

resource "azurerm_resource_group" "rg" {
  name     = "rg-cadence-prod"
  location = var.location
}
