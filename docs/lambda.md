# Lambda Functions Documentation

## Overview

The Serverless Image Processing Platform uses AWS Lambda functions as the core compute layer, providing serverless, event-driven processing capabilities. Each Lambda function has a specific role in the architecture, from authentication handling to image processing operations.

## Architecture

```mermaid
graph TB
    subgraph "API Layer"
        APIGW[API Gateway]
    end
    
    subgraph "Authentication Functions"
        AuthHandler[Auth Handler]
        Cognito[Cognito User Pool]
    end
    
    subgraph "Upload Functions"
        UploadHandler[Upload Handler]
        S3EventHandler[S3 Event Handler]
    end
    
    subgraph "Processing Functions"
        Orchestrator[Orchestrator]
        Validation[Validation]
        Resize[Resize]
        Watermark[Watermark]
    end
    
    subgraph "Infrastructure"
        S3Input[S3 Input Bucket]
        S3Output[S3 Output Bucket]
        SQS[SQS Queue]
        StepFn[Step Functions]
        DynamoDB[DynamoDB]
    end
    
    APIGW --> AuthHandler
    APIGW --> UploadHandler
    AuthHandler --> Cognito
    UploadHandler --> S3Input
    S3Input --> S3EventHandler
    S3EventHandler --> SQS
    SQS --> Orchestrator
    Orchestrator --> StepFn
    StepFn --> Validation
    StepFn --> Resize
    StepFn --> Watermark
    Validation --> S3Output
    Resize --> S3Output
    Watermark --> S3Output
    Validation --> DynamoDB
    Resize --> DynamoDB
    Watermark --> DynamoDB
```

## Function Categories

### 1. Authentication Functions

#### Auth Handler Lambda
**Purpose**: Handles all authentication and authorization requests from API Gateway

**Configuration**:
```hcl
resource "aws_lambda_function" "auth_handler" {
  filename         = data.archive_file.auth_handler.output_path
  function_name    = "${var.project_name}-auth-handler"
  role            = aws_iam_role.auth_handler_role.arn
  handler         = "auth_handler.lambda_handler"
  runtime         = "python3.9"
  timeout         = 30
  memory_size     = 256
  
  environment {
    variables = {
      COGNITO_USER_POOL_ID = aws_cognito_user_pool.main.id
      COGNITO_CLIENT_ID    = aws_cognito_user_pool_client.main.id
      DYNAMODB_TABLE       = aws_dynamodb_table.image_metadata.name
    }
  }
  
  vpc_config {
    subnet_ids         = aws_subnet.private[*].id
    security_group_ids = [aws_security_group.lambda_sg.id]
  }
  
  tags = {
    Environment = var.environment
    Service     = "auth"
  }
}
```

**Key Features**:
- User registration and sign-up
- User authentication and sign-in
- Email verification
- Password reset functionality
- JWT token validation
- User profile management

**Input Events**:
```json
{
  "httpMethod": "POST",
  "path": "/auth/signup",
  "body": {
    "email": "user@example.com",
    "password": "SecurePassword123!"
  },
  "headers": {
    "Content-Type": "application/json"
  }
}
```

**Output Responses**:
```json
{
  "statusCode": 200,
  "headers": {
    "Content-Type": "application/json",
    "Access-Control-Allow-Origin": "*"
  },
  "body": {
    "message": "User registered successfully",
    "userSub": "12345678-1234-1234-1234-123456789012"
  }
}
```

### 2. Upload Functions

#### Upload Handler Lambda
**Purpose**: Generates pre-signed S3 URLs for secure direct uploads

**Configuration**:
```hcl
resource "aws_lambda_function" "upload_handler" {
  filename         = data.archive_file.upload_handler.output_path
  function_name    = "${var.project_name}-upload-handler"
  role            = aws_iam_role.upload_handler_role.arn
  handler         = "upload_handler.lambda_handler"
  runtime         = "python3.9"
  timeout         = 30
  memory_size     = 256
  
  environment {
    variables = {
      S3_INPUT_BUCKET = aws_s3_bucket.input_bucket.bucket
      DYNAMODB_TABLE  = aws_dynamodb_table.image_metadata.name
      COGNITO_USER_POOL_ID = aws_cognito_user_pool.main.id
    }
  }
  
  vpc_config {
    subnet_ids         = aws_subnet.private[*].id
    security_group_ids = [aws_security_group.lambda_sg.id]
  }
}
```

**Key Features**:
- JWT token validation
- File type validation
- Pre-signed URL generation
- User metadata encoding
- Upload tracking

**Input Events**:
```json
{
  "httpMethod": "POST",
  "path": "/upload",
  "body": {
    "fileName": "vacation-photo.jpg",
    "fileType": "image/jpeg"
  },
  "headers": {
    "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
  }
}
```

**Output Responses**:
```json
{
  "statusCode": 200,
  "body": {
    "uploadUrl": "https://s3.amazonaws.com/bucket/uploads/user-id/image-id.jpg?X-Amz-Algorithm=...",
    "fileKey": "uploads/user-id/image-id.jpg",
    "expiresIn": 3600
  }
}
```

#### S3 Event Handler Lambda
**Purpose**: Processes S3 upload events and enqueues processing requests

**Configuration**:
```hcl
resource "aws_lambda_function" "s3_event_handler" {
  filename         = data.archive_file.s3_event_handler.output_path
  function_name    = "${var.project_name}-s3-event-handler"
  role            = aws_iam_role.s3_event_handler_role.arn
  handler         = "s3_event_handler.lambda_handler"
  runtime         = "python3.9"
  timeout         = 60
  memory_size     = 512
  
  environment {
    variables = {
      SQS_QUEUE_URL = aws_sqs_queue.upload_queue.url
      DYNAMODB_TABLE = aws_dynamodb_table.image_metadata.name
    }
  }
  
  vpc_config {
    subnet_ids         = aws_subnet.private[*].id
    security_group_ids = [aws_security_group.lambda_sg.id]
  }
}
```

**Key Features**:
- S3 event processing
- User metadata extraction
- SQS message enqueuing
- Initial metadata creation
- Error handling and retries

**Input Events**:
```json
{
  "Records": [
    {
      "eventVersion": "2.1",
      "eventSource": "aws:s3",
      "awsRegion": "us-east-1",
      "eventTime": "2024-01-01T12:00:00.000Z",
      "eventName": "ObjectCreated:Put",
      "s3": {
        "bucket": {
          "name": "image-processing-input-bucket"
        },
        "object": {
          "key": "uploads/user-id/image-id.jpg",
          "size": 2048576,
          "eTag": "abc123"
        }
      }
    }
  ]
}
```

### 3. Processing Functions

#### Orchestrator Lambda
**Purpose**: Manages the image processing workflow and Step Functions execution

**Configuration**:
```hcl
resource "aws_lambda_function" "orchestrator" {
  filename         = data.archive_file.orchestrator.output_path
  function_name    = "${var.project_name}-orchestrator"
  role            = aws_iam_role.orchestrator_role.arn
  handler         = "orchestrator.lambda_handler"
  runtime         = "python3.9"
  timeout         = 300
  memory_size     = 512
  
  environment {
    variables = {
      STEP_FUNCTIONS_ARN = aws_sfn_state_machine.image_processing.arn
      DYNAMODB_TABLE     = aws_dynamodb_table.image_metadata.name
      SNS_TOPIC_ARN      = aws_sns_topic.notifications.arn
    }
  }
  
  vpc_config {
    subnet_ids         = aws_subnet.private[*].id
    security_group_ids = [aws_security_group.lambda_sg.id]
  }
}
```

**Key Features**:
- SQS message processing
- Step Functions execution
- Workflow orchestration
- Error handling and retries
- Status tracking

**Input Events**:
```json
{
  "Records": [
    {
      "messageId": "msg-123",
      "receiptHandle": "receipt-handle",
      "body": {
        "imageId": "img_1234567890abcdef",
        "userId": "user_12345678-1234-1234-1234-123456789012",
        "s3Key": "uploads/user-id/image-id.jpg",
        "fileName": "vacation-photo.jpg",
        "fileSize": 2048576,
        "fileType": "image/jpeg"
      }
    }
  ]
}
```

#### Validation Lambda
**Purpose**: Validates uploaded images for format, size, and integrity

**Configuration**:
```hcl
resource "aws_lambda_function" "validation" {
  filename         = data.archive_file.validation.output_path
  function_name    = "${var.project_name}-validation"
  role            = aws_iam_role.validation_role.arn
  handler         = "validation.lambda_handler"
  runtime         = "python3.9"
  timeout         = 300
  memory_size     = 1024
  
  environment {
    variables = {
      S3_INPUT_BUCKET  = aws_s3_bucket.input_bucket.bucket
      S3_OUTPUT_BUCKET = aws_s3_bucket.output_bucket.bucket
      DYNAMODB_TABLE   = aws_dynamodb_table.image_metadata.name
      MAX_FILE_SIZE    = "10485760"  # 10MB
      ALLOWED_TYPES    = "image/jpeg,image/png,image/gif"
    }
  }
  
  vpc_config {
    subnet_ids         = aws_subnet.private[*].id
    security_group_ids = [aws_security_group.lambda_sg.id]
  }
}
```

**Key Features**:
- File format validation
- File size validation
- Image integrity checks
- Metadata extraction
- Virus scanning (optional)

**Input Events**:
```json
{
  "imageId": "img_1234567890abcdef",
  "userId": "user_12345678-1234-1234-1234-123456789012",
  "s3Key": "uploads/user-id/image-id.jpg",
  "fileName": "vacation-photo.jpg",
  "fileSize": 2048576,
  "fileType": "image/jpeg"
}
```

**Output Events**:
```json
{
  "imageId": "img_1234567890abcdef",
  "userId": "user_12345678-1234-1234-1234-123456789012",
  "s3Key": "uploads/user-id/image-id.jpg",
  "validationResult": "valid",
  "imageMetadata": {
    "width": 1920,
    "height": 1080,
    "format": "JPEG",
    "colorSpace": "sRGB"
  }
}
```

#### Resize Lambda
**Purpose**: Resizes images to predefined dimensions while maintaining quality

**Configuration**:
```hcl
resource "aws_lambda_function" "resize" {
  filename         = data.archive_file.resize.output_path
  function_name    = "${var.project_name}-resize"
  role            = aws_iam_role.resize_role.arn
  handler         = "resize.lambda_handler"
  runtime         = "python3.9"
  timeout         = 300
  memory_size     = 2048
  
  environment {
    variables = {
      S3_INPUT_BUCKET  = aws_s3_bucket.input_bucket.bucket
      S3_OUTPUT_BUCKET = aws_s3_bucket.output_bucket.bucket
      DYNAMODB_TABLE   = aws_dynamodb_table.image_metadata.name
      RESIZE_DIMENSIONS = "800x600,1200x900,1920x1080"
      QUALITY_SETTING  = "85"
    }
  }
  
  vpc_config {
    subnet_ids         = aws_subnet.private[*].id
    security_group_ids = [aws_security_group.lambda_sg.id]
  }
}
```

**Key Features**:
- Multiple size generation
- Aspect ratio preservation
- Quality optimization
- Format conversion
- Progressive JPEG support

**Input Events**:
```json
{
  "imageId": "img_1234567890abcdef",
  "userId": "user_12345678-1234-1234-1234-123456789012",
  "s3Key": "uploads/user-id/image-id.jpg",
  "validationResult": "valid",
  "imageMetadata": {
    "width": 1920,
    "height": 1080,
    "format": "JPEG"
  }
}
```

**Output Events**:
```json
{
  "imageId": "img_1234567890abcdef",
  "userId": "user_12345678-1234-1234-1234-123456789012",
  "resizedImages": [
    {
      "size": "small",
      "dimensions": "800x600",
      "s3Key": "processed/user-id/image-id-small.jpg",
      "fileSize": 512000
    },
    {
      "size": "medium",
      "dimensions": "1200x900",
      "s3Key": "processed/user-id/image-id-medium.jpg",
      "fileSize": 1024000
    }
  ]
}
```

#### Watermark Lambda
**Purpose**: Applies watermarks to processed images

**Configuration**:
```hcl
resource "aws_lambda_function" "watermark" {
  filename         = data.archive_file.watermark.output_path
  function_name    = "${var.project_name}-watermark"
  role            = aws_iam_role.watermark_role.arn
  handler         = "watermark.lambda_handler"
  runtime         = "python3.9"
  timeout         = 300
  memory_size     = 1024
  
  environment {
    variables = {
      S3_INPUT_BUCKET  = aws_s3_bucket.input_bucket.bucket
      S3_OUTPUT_BUCKET = aws_s3_bucket.output_bucket.bucket
      DYNAMODB_TABLE   = aws_dynamodb_table.image_metadata.name
      WATERMARK_TEXT   = "Processed by Image Platform"
      WATERMARK_FONT   = "Arial"
      WATERMARK_COLOR  = "#FFFFFF"
    }
  }
  
  vpc_config {
    subnet_ids         = aws_subnet.private[*].id
    security_group_ids = [aws_security_group.lambda_sg.id]
  }
}
```

**Key Features**:
- Text watermarking
- Image watermarking
- Position customization
- Opacity control
- Brand protection

## Performance Optimization

### Memory Configuration
```python
# Memory allocation based on function requirements
MEMORY_CONFIG = {
    'auth_handler': 256,      # Light processing
    'upload_handler': 256,    # Light processing
    's3_event_handler': 512,  # Moderate processing
    'orchestrator': 512,      # Moderate processing
    'validation': 1024,       # Image processing
    'resize': 2048,          # Heavy image processing
    'watermark': 1024        # Image processing
}
```

### Timeout Configuration
```python
# Timeout settings based on function complexity
TIMEOUT_CONFIG = {
    'auth_handler': 30,       # Quick operations
    'upload_handler': 30,     # Quick operations
    's3_event_handler': 60,   # S3 operations
    'orchestrator': 300,      # Step Functions execution
    'validation': 300,        # Image validation
    'resize': 300,           # Image processing
    'watermark': 300         # Image processing
}
```

### Concurrency Configuration
```hcl
resource "aws_lambda_function_event_invoke_config" "resize" {
  function_name                = aws_lambda_function.resize.function_name
  maximum_event_age_in_seconds = 60
  maximum_retry_attempts       = 2
}

resource "aws_lambda_provisioned_concurrency_config" "resize" {
  function_name                     = aws_lambda_function.resize.function_name
  provisioned_concurrent_executions = 10
  qualifier                         = aws_lambda_function.resize.version
}
```

## Error Handling

### Retry Logic
```python
import boto3
from botocore.exceptions import ClientError
import time

def retry_with_backoff(func, max_retries=3, base_delay=1):
    """Retry function with exponential backoff"""
    for attempt in range(max_retries):
        try:
            return func()
        except ClientError as e:
            if e.response['Error']['Code'] in ['ThrottlingException', 'ServiceUnavailable']:
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)
                    time.sleep(delay)
                    continue
            raise
    return None
```

### Dead Letter Queues
```hcl
resource "aws_sqs_queue" "lambda_dlq" {
  name = "${var.project_name}-lambda-dlq"
  
  tags = {
    Environment = var.environment
    Service     = "lambda"
  }
}

resource "aws_lambda_function_event_invoke_config" "with_dlq" {
  function_name                = aws_lambda_function.orchestrator.function_name
  maximum_event_age_in_seconds = 60
  maximum_retry_attempts       = 2
  
  destination_config {
    on_failure {
      destination = aws_sqs_queue.lambda_dlq.arn
    }
  }
}
```

## Monitoring & Observability

### CloudWatch Logs
```python
import logging
import json
import traceback

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    try:
        logger.info(f"Processing event: {json.dumps(event)}")
        
        # Function logic here
        
        logger.info("Function completed successfully")
        return {
            'statusCode': 200,
            'body': json.dumps({'message': 'Success'})
        }
    except Exception as e:
        logger.error(f"Function failed: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise
```

### X-Ray Tracing
```python
import boto3
from aws_xray_sdk.core import xray_recorder
from aws_xray_sdk.core import patch_all

patch_all()

@xray_recorder.capture('process_image')
def process_image(image_data):
    # Image processing logic
    pass

def lambda_handler(event, context):
    # Enable X-Ray tracing
    xray_recorder.begin_segment('lambda_handler')
    
    try:
        result = process_image(event)
        xray_recorder.end_segment()
        return result
    except Exception as e:
        xray_recorder.end_segment()
        raise
```

### Custom Metrics
```python
import boto3

cloudwatch = boto3.client('cloudwatch')

def put_custom_metric(metric_name, value, unit='Count'):
    """Put custom metric to CloudWatch"""
    cloudwatch.put_metric_data(
        Namespace='ImageProcessing',
        MetricData=[
            {
                'MetricName': metric_name,
                'Value': value,
                'Unit': unit,
                'Timestamp': datetime.utcnow()
            }
        ]
    )

def lambda_handler(event, context):
    start_time = time.time()
    
    try:
        # Function logic
        processing_time = time.time() - start_time
        put_custom_metric('ProcessingTime', processing_time, 'Seconds')
        put_custom_metric('ImagesProcessed', 1)
        
    except Exception as e:
        put_custom_metric('ProcessingErrors', 1)
        raise
```

## Security

### IAM Roles and Policies
```hcl
resource "aws_iam_role" "lambda_execution_role" {
  name = "${var.project_name}-lambda-execution-role"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_basic" {
  role       = aws_iam_role.lambda_execution_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy_attachment" "lambda_vpc" {
  role       = aws_iam_role.lambda_execution_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole"
}
```

### Environment Variables Encryption
```hcl
resource "aws_kms_key" "lambda_env" {
  description             = "KMS key for Lambda environment variables"
  deletion_window_in_days = 7
  
  tags = {
    Environment = var.environment
    Service     = "lambda"
  }
}

resource "aws_lambda_function" "with_encrypted_env" {
  # ... other configuration ...
  
  environment {
    variables = {
      ENCRYPTED_SECRET = aws_kms_key.lambda_env.arn
    }
  }
  
  kms_key_arn = aws_kms_key.lambda_env.arn
}
```

## Best Practices

### 1. Function Design
- Keep functions focused and single-purpose
- Use environment variables for configuration
- Implement proper error handling
- Use async/await for I/O operations

### 2. Performance
- Optimize memory allocation
- Use connection pooling for databases
- Implement caching where appropriate
- Use provisioned concurrency for critical functions

### 3. Security
- Use least-privilege IAM policies
- Encrypt sensitive environment variables
- Validate all inputs
- Implement proper authentication

### 4. Monitoring
- Use structured logging
- Implement custom metrics
- Set up comprehensive alarms
- Use X-Ray for distributed tracing

### 5. Cost Optimization
- Optimize memory and timeout settings
- Use provisioned concurrency strategically
- Implement efficient error handling
- Monitor and optimize cold starts

## Troubleshooting

### Common Issues

#### 1. Cold Starts
**Symptoms**: High latency on first invocation
**Solutions**:
- Use provisioned concurrency
- Optimize function size
- Use Lambda layers for dependencies

#### 2. Memory Issues
**Symptoms**: Function timeouts or errors
**Solutions**:
- Increase memory allocation
- Optimize code efficiency
- Use streaming for large files

#### 3. VPC Connectivity
**Symptoms**: Timeout connecting to RDS or other VPC resources
**Solutions**:
- Configure NAT Gateway
- Use VPC endpoints
- Optimize security group rules

#### 4. Permission Errors
**Symptoms**: Access denied errors
**Solutions**:
- Review IAM policies
- Check resource ARNs
- Verify cross-account permissions

This Lambda implementation provides a robust, scalable, and secure compute layer for the Serverless Image Processing Platform, with comprehensive monitoring, error handling, and performance optimization features. 