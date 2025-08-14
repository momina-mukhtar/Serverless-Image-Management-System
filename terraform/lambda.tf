
# IAM Role for Lambda functions
resource "aws_iam_role" "lambda_exec" {
  name = "lambda-exec-role-${random_id.suffix.hex}"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role.json
}

data "aws_iam_policy_document" "lambda_assume_role" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

# IAM Policy for Lambda execution
resource "aws_iam_role_policy_attachment" "lambda_basic" {
  role       = aws_iam_role.lambda_exec.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# IAM Policy for VPC access
resource "aws_iam_role_policy_attachment" "lambda_vpc" {
  role       = aws_iam_role.lambda_exec.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole"
}

# Custom IAM Policy for Lambda permissions
resource "aws_iam_policy" "lambda_custom" {
  name        = "lambda-custom-policy-${random_id.suffix.hex}"
  description = "Custom policy for Lambda functions"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject",
          "s3:ListBucket"
        ]
        Resource = [
          aws_s3_bucket.input.arn,
          "${aws_s3_bucket.input.arn}/*",
          aws_s3_bucket.output.arn,
          "${aws_s3_bucket.output.arn}/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "kms:Decrypt",
          "kms:GenerateDataKey",
          "kms:DescribeKey"
        ]
        Resource = aws_kms_key.s3.arn
      },
      {
        Effect = "Allow"
        Action = [
          "sqs:SendMessage",
          "sqs:ReceiveMessage",
          "sqs:DeleteMessage",
          "sqs:GetQueueAttributes"
        ]
        Resource = aws_sqs_queue.upload_events.arn
      },
      {
        Effect = "Allow"
        Action = [
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:UpdateItem",
          "dynamodb:DeleteItem",
          "dynamodb:Query",
          "dynamodb:Scan"
        ]
        Resource = aws_dynamodb_table.image_metadata.arn
      },
      {
        Effect = "Allow"
        Action = [
          "cognito-idp:SignUp",
          "cognito-idp:ConfirmSignUp",
          "cognito-idp:InitiateAuth",
          "cognito-idp:ForgotPassword",
          "cognito-idp:ConfirmForgotPassword",
          "cognito-idp:GetUser"
        ]
        Resource = aws_cognito_user_pool.main.arn
      },
      {
        Effect = "Allow"
        Action = [
          "states:StartExecution",
          "states:DescribeExecution",
          "states:StopExecution"
        ]
        Resource = aws_sfn_state_machine.image_processing.arn
      },

    ]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_custom" {
  role       = aws_iam_role.lambda_exec.name
  policy_arn = aws_iam_policy.lambda_custom.arn
}

# Security group for Lambda
resource "aws_security_group" "lambda" {
  name        = "lambda-sg-${random_id.suffix.hex}"
  description = "Allow Lambda to access VPC endpoints"
  vpc_id      = aws_vpc.main.id

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "lambda-security-group"
  }
}

# Auth Handler Lambda
resource "aws_lambda_function" "auth_handler" {
  function_name = "auth-handler-${random_id.suffix.hex}"
  handler       = "main.main"
  runtime       = "python3.11"
  role          = aws_iam_role.lambda_exec.arn
  filename      = data.archive_file.auth_handler.output_path
  source_code_hash = data.archive_file.auth_handler.output_base64sha256
  timeout       = 30
  memory_size   = 256

  environment {
    variables = {
      USER_POOL_ID = aws_cognito_user_pool.main.id
      CLIENT_ID    = aws_cognito_user_pool_client.main.id
      # SNS_TOPIC_ARN removed - no longer using notifications
    }
  }

  vpc_config {
    subnet_ids         = [aws_subnet.private_a.id, aws_subnet.private_b.id]
    security_group_ids = [aws_security_group.lambda.id]
  }

  # Enable X-Ray tracing
  tracing_config {
    mode = "Active"
  }

  tags = {
    Name = "auth-handler"
  }
}

# Upload Handler Lambda
resource "aws_lambda_function" "upload_handler" {
  function_name = "upload-handler-${random_id.suffix.hex}"
  handler       = "main.main"
  runtime       = "python3.11"
  role          = aws_iam_role.lambda_exec.arn
  filename      = data.archive_file.upload_handler.output_path
  source_code_hash = data.archive_file.upload_handler.output_base64sha256
  timeout       = 30
  memory_size   = 256

  environment {
    variables = {
      INPUT_BUCKET = aws_s3_bucket.input.bucket
      USER_POOL_ID = aws_cognito_user_pool.main.id
      CLIENT_ID    = aws_cognito_user_pool_client.main.id
      # SNS_TOPIC_ARN removed - no longer using notifications
      S3_KMS_KEY_ID = aws_kms_key.s3.arn
    }
  }

  vpc_config {
    subnet_ids         = [aws_subnet.private_a.id, aws_subnet.private_b.id]
    security_group_ids = [aws_security_group.lambda.id]
  }

  # Enable X-Ray tracing
  tracing_config {
    mode = "Active"
  }

  tags = {
    Name = "upload-handler"
  }
}

# S3 Event Handler Lambda
resource "aws_lambda_function" "s3_event_handler" {
  function_name = "s3-event-handler-${random_id.suffix.hex}"
  handler       = "main.main"
  runtime       = "python3.11"
  role          = aws_iam_role.lambda_exec.arn
  filename      = data.archive_file.s3_event_handler.output_path
  source_code_hash = data.archive_file.s3_event_handler.output_base64sha256
  timeout       = 60
  memory_size   = 256

  environment {
    variables = {
      SQS_QUEUE_URL = aws_sqs_queue.upload_events.url
      # SNS_TOPIC_ARN removed - no longer using notifications
    }
  }

  vpc_config {
    subnet_ids         = [aws_subnet.private_a.id, aws_subnet.private_b.id]
    security_group_ids = [aws_security_group.lambda.id]
  }

  # Enable X-Ray tracing
  tracing_config {
    mode = "Active"
  }

  tags = {
    Name = "s3-event-handler"
  }
}

# Orchestrator Lambda
resource "aws_lambda_function" "orchestrator" {
  function_name = "orchestrator-${random_id.suffix.hex}"
  handler       = "main.main"
  runtime       = "python3.11"
  role          = aws_iam_role.lambda_exec.arn
  filename      = data.archive_file.orchestrator.output_path
  source_code_hash = data.archive_file.orchestrator.output_base64sha256
  timeout       = 60
  memory_size   = 256

  environment {
    variables = {
      STATE_MACHINE_ARN = aws_sfn_state_machine.image_processing.arn
      DYNAMODB_TABLE    = aws_dynamodb_table.image_metadata.name
      # SNS_TOPIC_ARN removed - no longer using notifications
    }
  }

  vpc_config {
    subnet_ids         = [aws_subnet.private_a.id, aws_subnet.private_b.id]
    security_group_ids = [aws_security_group.lambda.id]
  }

  # Enable X-Ray tracing
  tracing_config {
    mode = "Active"
  }

  tags = {
    Name = "orchestrator"
  }
}

# Validation Lambda
resource "aws_lambda_function" "validation" {
  function_name = "validation-${random_id.suffix.hex}"
  handler       = "main.main"
  runtime       = "python3.11"
  role          = aws_iam_role.lambda_exec.arn
  filename      = data.archive_file.validation.output_path
  source_code_hash = data.archive_file.validation.output_base64sha256
  timeout       = 120
  memory_size   = 512

  environment {
    variables = {
      INPUT_BUCKET   = aws_s3_bucket.input.bucket
      OUTPUT_BUCKET  = aws_s3_bucket.output.bucket
      DYNAMODB_TABLE = aws_dynamodb_table.image_metadata.name
      # SNS_TOPIC_ARN removed - no longer using notifications
    }
  }

  vpc_config {
    subnet_ids         = [aws_subnet.private_a.id, aws_subnet.private_b.id]
    security_group_ids = [aws_security_group.lambda.id]
  }

  # Enable X-Ray tracing
  tracing_config {
    mode = "Active"
  }

  tags = {
    Name = "validation"
  }
}

# Resize Lambda
resource "aws_lambda_function" "resize" {
  function_name = "resize-${random_id.suffix.hex}"
  handler       = "main.main"
  runtime       = "python3.11"
  role          = aws_iam_role.lambda_exec.arn
  filename      = data.archive_file.resize.output_path
  source_code_hash = data.archive_file.resize.output_base64sha256
  timeout       = 300
  memory_size   = 1024

  layers = ["arn:aws:lambda:us-east-1:770693421928:layer:Klayers-p311-Pillow:8"]

  environment {
    variables = {
      INPUT_BUCKET   = aws_s3_bucket.input.bucket
      OUTPUT_BUCKET  = aws_s3_bucket.output.bucket
      DYNAMODB_TABLE = aws_dynamodb_table.image_metadata.name
      # SNS_TOPIC_ARN removed - no longer using notifications
      KMS_KEY_ID     = aws_kms_key.s3.arn
    }
  }

  vpc_config {
    subnet_ids         = [aws_subnet.private_a.id, aws_subnet.private_b.id]
    security_group_ids = [aws_security_group.lambda.id]
  }

  # Enable X-Ray tracing
  tracing_config {
    mode = "Active"
  }

  tags = {
    Name = "resize"
  }
}

# Watermark Lambda
resource "aws_lambda_function" "watermark" {
  function_name = "watermark-${random_id.suffix.hex}"
  handler       = "main.main"
  runtime       = "python3.11"
  role          = aws_iam_role.lambda_exec.arn
  filename      = data.archive_file.watermark.output_path
  source_code_hash = data.archive_file.watermark.output_base64sha256
  timeout       = 300
  memory_size   = 1024

  layers = ["arn:aws:lambda:us-east-1:770693421928:layer:Klayers-p311-Pillow:8"]

  environment {
    variables = {
      INPUT_BUCKET   = aws_s3_bucket.input.bucket
      OUTPUT_BUCKET  = aws_s3_bucket.output.bucket
      DYNAMODB_TABLE = aws_dynamodb_table.image_metadata.name
      KMS_KEY_ID     = aws_kms_key.s3.arn
      WATERMARK_TEXT = "PROCESSED"
      WATERMARK_FONT_SIZE = "24"
      WATERMARK_OPACITY = "128"
      WATERMARK_POSITION = "bottom-right"
    }
  }

  vpc_config {
    subnet_ids         = [aws_subnet.private_a.id, aws_subnet.private_b.id]
    security_group_ids = [aws_security_group.lambda.id]
  }

  # Enable X-Ray tracing
  tracing_config {
    mode = "Active"
  }

  tags = {
    Name = "watermark"
  }
}

# Image Retrieval Lambda
resource "aws_lambda_function" "image_retrieval" {
  function_name = "image-retrieval-${random_id.suffix.hex}"
  handler       = "main.main"
  runtime       = "python3.11"
  role          = aws_iam_role.lambda_exec.arn
  filename      = data.archive_file.image_retrieval.output_path
  source_code_hash = data.archive_file.image_retrieval.output_base64sha256
  timeout       = 30
  memory_size   = 256

  environment {
    variables = {
      OUTPUT_BUCKET  = aws_s3_bucket.output.bucket
      DYNAMODB_TABLE = aws_dynamodb_table.image_metadata.name
      USER_POOL_ID   = aws_cognito_user_pool.main.id
      CLIENT_ID      = aws_cognito_user_pool_client.main.id
      S3_KMS_KEY_ARN = aws_kms_key.s3.arn
    }
  }

  vpc_config {
    subnet_ids         = [aws_subnet.private_a.id, aws_subnet.private_b.id]
    security_group_ids = [aws_security_group.lambda.id]
  }

  # Enable X-Ray tracing
  tracing_config {
    mode = "Active"
  }

  tags = {
    Name = "image-retrieval"
  }
}

# S3 Event Notification for S3 Event Handler
resource "aws_s3_bucket_notification" "input_bucket_notification" {
  bucket = aws_s3_bucket.input.id

  lambda_function {
    lambda_function_arn = aws_lambda_function.s3_event_handler.arn
    events              = ["s3:ObjectCreated:*"]
    filter_prefix       = "uploads/"
  }

  depends_on = [aws_lambda_permission.s3_event_handler]
}

# Lambda permission for S3 to invoke S3 Event Handler
resource "aws_lambda_permission" "s3_event_handler" {
  statement_id  = "AllowS3Invoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.s3_event_handler.function_name
  principal     = "s3.amazonaws.com"
  source_arn    = aws_s3_bucket.input.arn
}

# SQS Event Source Mapping for Orchestrator
resource "aws_lambda_event_source_mapping" "orchestrator_sqs" {
  event_source_arn = aws_sqs_queue.upload_events.arn
  function_name    = aws_lambda_function.orchestrator.arn
  batch_size       = 1
}

# Data sources for Lambda function archives
data "archive_file" "auth_handler" {
  type        = "zip"
  source_dir  = "${var.lambda_source_path}/auth_handler"
  output_path = "${var.lambda_source_path}/auth_handler.zip"
}

data "archive_file" "upload_handler" {
  type        = "zip"
  source_dir  = "${var.lambda_source_path}/upload_handler"
  output_path = "${var.lambda_source_path}/upload_handler.zip"
}

data "archive_file" "s3_event_handler" {
  type        = "zip"
  source_dir  = "${var.lambda_source_path}/s3_event_handler"
  output_path = "${var.lambda_source_path}/s3_event_handler.zip"
}

data "archive_file" "orchestrator" {
  type        = "zip"
  source_dir  = "${var.lambda_source_path}/orchestrator"
  output_path = "${var.lambda_source_path}/orchestrator.zip"
}

data "archive_file" "validation" {
  type        = "zip"
  source_dir  = "${var.lambda_source_path}/validation"
  output_path = "${var.lambda_source_path}/validation.zip"
}

data "archive_file" "resize" {
  type        = "zip"
  source_dir  = "${var.lambda_source_path}/resize"
  output_path = "${var.lambda_source_path}/resize.zip"
}

data "archive_file" "watermark" {
  type        = "zip"
  source_dir  = "${var.lambda_source_path}/watermark"
  output_path = "${var.lambda_source_path}/watermark.zip"
}

data "archive_file" "image_retrieval" {
  type        = "zip"
  source_dir  = "${var.lambda_source_path}/image_retrieval"
  output_path = "${var.lambda_source_path}/image_retrieval.zip"
}
