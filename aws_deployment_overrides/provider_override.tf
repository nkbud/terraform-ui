# Example AWS deployment override
# This file demonstrates override .tf files that can be copied
# into cloned repositories during the override stage

variable "aws_region" {
  description = "AWS region for deployment override"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Environment name for deployment"
  type        = string
  default     = "production"
}

# Provider configuration override
terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
  
  default_tags {
    tags = {
      Environment = var.environment
      ManagedBy   = "terraform-ui-pipeline"
    }
  }
}