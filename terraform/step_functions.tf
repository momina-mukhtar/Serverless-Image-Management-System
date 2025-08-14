# Step Functions IAM Role
resource "aws_iam_role" "step_functions" {
  name = "step-functions-role-${random_id.suffix.hex}"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "states.amazonaws.com"
        }
      }
    ]
  })
}

# Step Functions IAM Policy
resource "aws_iam_role_policy" "step_functions" {
  name = "step-functions-policy-${random_id.suffix.hex}"
  role = aws_iam_role.step_functions.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "lambda:InvokeFunction"
        ]
        Resource = [
          aws_lambda_function.validation.arn,
          aws_lambda_function.resize.arn,
          aws_lambda_function.watermark.arn
        ]
      }
    ]
  })
}

# Step Functions State Machine
resource "aws_sfn_state_machine" "image_processing" {
  name     = "image-processing-workflow-${random_id.suffix.hex}"
  role_arn = aws_iam_role.step_functions.arn

  definition = jsonencode({
    Comment = "Image processing workflow with validation, resize, and watermark"
    StartAt = "Validation"
    States = {
      "Validation" = {
        Type = "Task"
        Resource = aws_lambda_function.validation.arn
        Retry = [
          {
            ErrorEquals = ["Lambda.ServiceException", "Lambda.AWSLambdaException", "Lambda.SdkClientException"]
            IntervalSeconds = 2
            MaxAttempts = 3
            BackoffRate = 2.0
          }
        ]
        Catch = [
          {
            ErrorEquals = ["States.ALL"]
            Next = "ValidationFailed"
          }
        ]
        Next = "Resize"
        ResultPath = "$.validation_result"
      }
      
      "ValidationFailed" = {
        Type = "Fail"
        Cause = "Image validation failed"
        Error = "ValidationError"
      }
      
      "Resize" = {
        Type = "Task"
        Resource = aws_lambda_function.resize.arn
        Retry = [
          {
            ErrorEquals = ["Lambda.ServiceException", "Lambda.AWSLambdaException", "Lambda.SdkClientException"]
            IntervalSeconds = 2
            MaxAttempts = 3
            BackoffRate = 2.0
          }
        ]
        Catch = [
          {
            ErrorEquals = ["States.ALL"]
            Next = "ResizeFailed"
          }
        ]
        Next = "Watermark"
        ResultPath = "$.resize_result"
      }
      
      "ResizeFailed" = {
        Type = "Fail"
        Cause = "Image resize failed"
        Error = "ResizeError"
      }
      
      "Watermark" = {
        Type = "Task"
        Resource = aws_lambda_function.watermark.arn
        Retry = [
          {
            ErrorEquals = ["Lambda.ServiceException", "Lambda.AWSLambdaException", "Lambda.SdkClientException"]
            IntervalSeconds = 2
            MaxAttempts = 3
            BackoffRate = 2.0
          }
        ]
        Catch = [
          {
            ErrorEquals = ["States.ALL"]
            Next = "WatermarkFailed"
          }
        ]
        Next = "Success"
        ResultPath = "$.watermark_result"
      }
      
      "WatermarkFailed" = {
        Type = "Fail"
        Cause = "Image watermark failed"
        Error = "WatermarkError"
      }
      
      "Success" = {
        Type = "Succeed"
        Comment = "Image processing completed successfully"
      }
    }
  })

  tags = {
    Name = "image-processing-workflow"
  }
}
