# =============================================================================
# TERRAFORM VARIABLES
# =============================================================================
# This file defines all input variables used throughout the Terraform configuration.
# Variables allow for customization of the infrastructure deployment.

# =============================================================================
# AWS CONFIGURATION
# =============================================================================
variable "aws_region" {
  description = "AWS region to deploy resources in"
  type        = string
  default     = "us-east-1"
}

# =============================================================================
# PROJECT CONFIGURATION
# =============================================================================
variable "project_name" {
  description = "Name of the project for resource naming"
  type        = string
  default     = "image-processing"
}

variable "environment" {
  description = "Environment name (e.g., dev, staging, prod)"
  type        = string
  default     = "production"
}

# =============================================================================
# NETWORKING CONFIGURATION
# =============================================================================
variable "vpc_cidr" {
  description = "CIDR block for the VPC"
  type        = string
  default     = "10.0.0.0/16"
}

# =============================================================================
# APPLICATION CONFIGURATION
# =============================================================================
variable "lambda_source_path" {
  description = "Path to Lambda function source code"
  type        = string
  default     = "../src/lambda"
}


