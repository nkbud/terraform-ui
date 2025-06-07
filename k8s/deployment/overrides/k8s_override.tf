# Example Kubernetes deployment override
# This file demonstrates override .tf files for Kubernetes deployments

variable "kubernetes_namespace" {
  description = "Kubernetes namespace for deployment"
  type        = string
  default     = "default"
}

variable "cluster_name" {
  description = "Kubernetes cluster name"
  type        = string
  default     = "production-cluster"
}

# Provider configuration override for Kubernetes
terraform {
  required_providers {
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.0"
    }
  }
}

provider "kubernetes" {
  config_path = "~/.kube/config"
  
  # Additional provider configuration can be added here
}

# Common labels for all Kubernetes resources
locals {
  common_labels = {
    "app.kubernetes.io/managed-by" = "terraform-ui-pipeline"
    "environment"                  = "production"
  }
}