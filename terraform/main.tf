# =============================================================================
# TERRAFORM CONFIGURATION
# =============================================================================
# This file contains the main Terraform configuration including providers,
# random ID generation, and references to other configuration files.

terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 4.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# =============================================================================
# RESOURCE NAMING
# =============================================================================
# Generate a unique suffix for all resource names to avoid conflicts
resource "random_id" "suffix" {
  byte_length = 4
}

# =============================================================================
# INFRASTRUCTURE COMPONENTS
# =============================================================================
# The following files contain the infrastructure components:
# - vpc.tf: VPC, subnets, route tables, and VPC endpoints
# - api_gateway.tf: API Gateway REST API and endpoints
# - lambda.tf: Lambda functions and their configurations
# - s3.tf: S3 buckets for input, output, and logs
# - sqs.tf: SQS queue for event processing
# - dynamodb.tf: DynamoDB table for metadata storage
# - step_functions.tf: Step Functions state machine
# - cognito.tf: Cognito user pool and client
# - security.tf: IAM roles, policies, KMS keys, and security groups
# - monitoring.tf: CloudWatch log groups and basic monitoring
