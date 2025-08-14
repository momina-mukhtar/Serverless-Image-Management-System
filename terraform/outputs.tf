# =============================================================================
# TERRAFORM OUTPUTS
# =============================================================================
# This file defines all outputs that will be displayed after Terraform applies
# the configuration. These outputs provide important information for connecting
# to and using the deployed infrastructure.

# =============================================================================
# API GATEWAY OUTPUTS
# =============================================================================

output "api_gateway_url" {
  description = "URL of the API Gateway"
  value       = "${aws_api_gateway_stage.main.invoke_url}"
}

output "api_gateway_execution_arn" {
  description = "Execution ARN of the API Gateway"
  value       = aws_api_gateway_rest_api.main.execution_arn
}

# =============================================================================
# S3 BUCKET OUTPUTS
# =============================================================================

output "s3_input_bucket" {
  description = "Name of the input S3 bucket"
  value       = aws_s3_bucket.input.bucket
}

output "s3_input_bucket_arn" {
  description = "ARN of the input S3 bucket"
  value       = aws_s3_bucket.input.arn
}

output "s3_output_bucket" {
  description = "Name of the output S3 bucket"
  value       = aws_s3_bucket.output.bucket
}

output "s3_output_bucket_arn" {
  description = "ARN of the output S3 bucket"
  value       = aws_s3_bucket.output.arn
}

# =============================================================================
# SQS OUTPUTS
# =============================================================================

output "sqs_upload_events_url" {
  description = "URL of the SQS upload events queue"
  value       = aws_sqs_queue.upload_events.url
}

output "sqs_upload_events_arn" {
  description = "ARN of the SQS upload events queue"
  value       = aws_sqs_queue.upload_events.arn
}

# =============================================================================
# DYNAMODB OUTPUTS
# =============================================================================

output "dynamodb_table_name" {
  description = "Name of the DynamoDB table"
  value       = aws_dynamodb_table.image_metadata.name
}

output "dynamodb_table_arn" {
  description = "ARN of the DynamoDB table"
  value       = aws_dynamodb_table.image_metadata.arn
}

# =============================================================================
# KMS OUTPUTS
# =============================================================================

output "s3_kms_key_arn" {
  description = "ARN of the KMS key for S3 encryption"
  value       = aws_kms_key.s3.arn
}

output "dynamodb_kms_key_arn" {
  description = "ARN of the KMS key for DynamoDB encryption"
  value       = aws_kms_key.dynamodb.arn
}

# =============================================================================
# VPC OUTPUTS
# =============================================================================

output "vpc_id" {
  description = "ID of the VPC"
  value       = aws_vpc.main.id
}

output "private_subnet_ids" {
  description = "IDs of the private subnets"
  value       = [aws_subnet.private_a.id, aws_subnet.private_b.id]
}

# =============================================================================
# STEP FUNCTIONS OUTPUTS
# =============================================================================

output "step_functions_arn" {
  description = "ARN of the Step Functions state machine"
  value       = aws_sfn_state_machine.image_processing.arn
}

output "step_functions_name" {
  description = "Name of the Step Functions state machine"
  value       = aws_sfn_state_machine.image_processing.name
}

# =============================================================================
# COGNITO OUTPUTS
# =============================================================================

output "cognito_user_pool_id" {
  description = "ID of the Cognito user pool"
  value       = aws_cognito_user_pool.main.id
}

output "cognito_user_pool_arn" {
  description = "ARN of the Cognito user pool"
  value       = aws_cognito_user_pool.main.arn
}

output "cognito_user_pool_client_id" {
  description = "ID of the Cognito user pool client"
  value       = aws_cognito_user_pool_client.main.id
}

output "cognito_user_pool_domain" {
  description = "Domain of the Cognito user pool"
  value       = aws_cognito_user_pool_domain.main.domain
}

# =============================================================================
# LAMBDA FUNCTION OUTPUTS
# =============================================================================

output "lambda_auth_handler_arn" {
  description = "ARN of the auth handler Lambda function"
  value       = aws_lambda_function.auth_handler.arn
}

output "lambda_upload_handler_arn" {
  description = "ARN of the upload handler Lambda function"
  value       = aws_lambda_function.upload_handler.arn
}

output "lambda_s3_event_handler_arn" {
  description = "ARN of the S3 event handler Lambda function"
  value       = aws_lambda_function.s3_event_handler.arn
}

output "lambda_orchestrator_arn" {
  description = "ARN of the orchestrator Lambda function"
  value       = aws_lambda_function.orchestrator.arn
}

output "lambda_validation_arn" {
  description = "ARN of the validation Lambda function"
  value       = aws_lambda_function.validation.arn
}

output "lambda_resize_arn" {
  description = "ARN of the resize Lambda function"
  value       = aws_lambda_function.resize.arn
}

output "lambda_watermark_arn" {
  description = "ARN of the watermark Lambda function"
  value       = aws_lambda_function.watermark.arn
}

# =============================================================================
# NETWORKING OUTPUTS
# =============================================================================

output "vpc_cidr" {
  description = "CIDR block of the VPC"
  value       = aws_vpc.main.cidr_block
}

# =============================================================================
# API ENDPOINTS
# =============================================================================

output "api_endpoints" {
  description = "Available API endpoints"
  value = {
    signup = "${aws_api_gateway_stage.main.invoke_url}/auth/signup"
    signin = "${aws_api_gateway_stage.main.invoke_url}/auth/signin"
    verify = "${aws_api_gateway_stage.main.invoke_url}/auth/verify"
    forgot_password = "${aws_api_gateway_stage.main.invoke_url}/auth/forgot-password"
    confirm_forgot_password = "${aws_api_gateway_stage.main.invoke_url}/auth/confirm-forgot-password"
    upload = "${aws_api_gateway_stage.main.invoke_url}/upload"
  }
}
