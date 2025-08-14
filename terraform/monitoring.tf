# =============================================================================
# MONITORING AND LOGGING
# =============================================================================
# This file configures CloudWatch log groups for all Lambda functions.
# Log retention is set to 30 days to balance cost and debugging needs.

# =============================================================================
# LAMBDA FUNCTION LOG GROUPS
# =============================================================================

# Authentication handler logs
resource "aws_cloudwatch_log_group" "auth_handler" {
  name              = "/aws/lambda/${aws_lambda_function.auth_handler.function_name}"
  retention_in_days = 30
  tags = {
    Name = "auth-handler-logs"
  }
}

# Upload handler logs
resource "aws_cloudwatch_log_group" "upload_handler" {
  name              = "/aws/lambda/${aws_lambda_function.upload_handler.function_name}"
  retention_in_days = 30
  tags = {
    Name = "upload-handler-logs"
  }
}

# S3 event handler logs
resource "aws_cloudwatch_log_group" "s3_event_handler" {
  name              = "/aws/lambda/${aws_lambda_function.s3_event_handler.function_name}"
  retention_in_days = 30
  tags = {
    Name = "s3-event-handler-logs"
  }
}

# Orchestrator logs
resource "aws_cloudwatch_log_group" "orchestrator" {
  name              = "/aws/lambda/${aws_lambda_function.orchestrator.function_name}"
  retention_in_days = 30
  tags = {
    Name = "orchestrator-logs"
  }
}

# Validation function logs
resource "aws_cloudwatch_log_group" "validation" {
  name              = "/aws/lambda/${aws_lambda_function.validation.function_name}"
  retention_in_days = 30
  tags = {
    Name = "validation-logs"
  }
}

# Resize function logs
resource "aws_cloudwatch_log_group" "resize" {
  name              = "/aws/lambda/${aws_lambda_function.resize.function_name}"
  retention_in_days = 30
  tags = {
    Name = "resize-logs"
  }
}

# Watermark function logs
resource "aws_cloudwatch_log_group" "watermark" {
  name              = "/aws/lambda/${aws_lambda_function.watermark.function_name}"
  retention_in_days = 30
  tags = {
    Name = "watermark-logs"
  }
}

# Image retrieval function logs
resource "aws_cloudwatch_log_group" "image_retrieval" {
  name              = "/aws/lambda/${aws_lambda_function.image_retrieval.function_name}"
  retention_in_days = 30
  tags = {
    Name = "image-retrieval-logs"
  }
} 