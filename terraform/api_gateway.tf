# API Gateway REST API
resource "aws_api_gateway_rest_api" "main" {
  name        = "image-processing-api-${random_id.suffix.hex}"
  description = "REST API for image processing platform"
}

# IAM Role for API Gateway CloudWatch Logging
resource "aws_iam_role" "api_gateway_cloudwatch" {
  name = "${var.project_name}-api-gateway-cloudwatch-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "apigateway.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy" "api_gateway_cloudwatch" {
  name = "${var.project_name}-api-gateway-cloudwatch-policy"
  role = aws_iam_role.api_gateway_cloudwatch.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:DescribeLogGroups",
          "logs:DescribeLogStreams",
          "logs:PutLogEvents",
          "logs:GetLogEvents",
          "logs:FilterLogEvents"
        ]
        Resource = "*"
      }
    ]
  })
}

# API Gateway Account Settings
resource "aws_api_gateway_account" "main" {
  cloudwatch_role_arn = aws_iam_role.api_gateway_cloudwatch.arn
}

# CloudWatch Log Group for API Gateway
resource "aws_cloudwatch_log_group" "api_gateway" {
  name              = "/aws/apigateway/${var.project_name}-api"
  retention_in_days = 30
  
  tags = {
    Environment = var.environment
    Service     = "api-gateway"
  }
}

# API Gateway Stage
resource "aws_api_gateway_stage" "main" {
  depends_on = [aws_api_gateway_account.main]
  deployment_id = aws_api_gateway_deployment.main.id
  rest_api_id   = aws_api_gateway_rest_api.main.id
  stage_name    = "prod"

  # Enable CloudWatch logging
  access_log_settings {
    destination_arn = aws_cloudwatch_log_group.api_gateway.arn
    format = jsonencode({
      requestId      = "$context.requestId"
      ip             = "$context.identity.sourceIp"
      caller         = "$context.identity.caller"
      user           = "$context.identity.user"
      requestTime    = "$context.requestTime"
      httpMethod     = "$context.httpMethod"
      resourcePath   = "$context.resourcePath"
      status         = "$context.status"
      protocol       = "$context.protocol"
      responseLength = "$context.responseLength"
      integrationLatency = "$context.integrationLatency"
      responseLatency    = "$context.responseLatency"
    })
  }

  # Enable X-Ray tracing
  xray_tracing_enabled = true

  tags = {
    Name = "prod-stage"
  }
}

# API Gateway Deployment
resource "aws_api_gateway_deployment" "main" {
  depends_on = [
    aws_api_gateway_integration.signup_post,
    aws_api_gateway_integration.signin_post,
    aws_api_gateway_integration.verify_post,
    aws_api_gateway_integration.forgot_password_post,
    aws_api_gateway_integration.confirm_forgot_password_post,
    aws_api_gateway_integration.upload_post,
    aws_api_gateway_integration.upload_options,
    aws_api_gateway_integration.image_get,
    aws_api_gateway_integration.image_options
  ]

  rest_api_id = aws_api_gateway_rest_api.main.id

  # Force new deployment when usage plan changes
  triggers = {
    redeployment = sha1(jsonencode([
      aws_api_gateway_integration.signup_post,
      aws_api_gateway_integration.signin_post,
      aws_api_gateway_integration.verify_post,
      aws_api_gateway_integration.forgot_password_post,
      aws_api_gateway_integration.confirm_forgot_password_post,
      aws_api_gateway_integration.upload_post,
      aws_api_gateway_integration.upload_options,
      aws_api_gateway_integration.image_get,
      aws_api_gateway_integration.image_options
    ]))
  }

  lifecycle {
    create_before_destroy = true
  }
}

# Note: Removed usage plan and API key requirements since authentication is handled in Lambda functions
# This prevents SigV4 signing issues and simplifies the API access

# Auth Resource
resource "aws_api_gateway_resource" "auth" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_rest_api.main.root_resource_id
  path_part   = "auth"
}

# Signup Resource
resource "aws_api_gateway_resource" "signup" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_resource.auth.id
  path_part   = "signup"
}

# Signup POST Method
resource "aws_api_gateway_method" "signup_post" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.signup.id
  http_method   = "POST"
  authorization = "NONE"
}

# Signup Integration
resource "aws_api_gateway_integration" "signup_post" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.signup.id
  http_method = aws_api_gateway_method.signup_post.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.auth_handler.invoke_arn
}

# Signin Resource
resource "aws_api_gateway_resource" "signin" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_resource.auth.id
  path_part   = "signin"
}

# Signin POST Method
resource "aws_api_gateway_method" "signin_post" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.signin.id
  http_method   = "POST"
  authorization = "NONE"
}

# Signin Integration
resource "aws_api_gateway_integration" "signin_post" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.signin.id
  http_method = aws_api_gateway_method.signin_post.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.auth_handler.invoke_arn
}

# Verify Resource
resource "aws_api_gateway_resource" "verify" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_resource.auth.id
  path_part   = "verify"
}

# Verify POST Method
resource "aws_api_gateway_method" "verify_post" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.verify.id
  http_method   = "POST"
  authorization = "NONE"
}

# Verify Integration
resource "aws_api_gateway_integration" "verify_post" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.verify.id
  http_method = aws_api_gateway_method.verify_post.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.auth_handler.invoke_arn
}

# Forgot Password Resource
resource "aws_api_gateway_resource" "forgot_password" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_resource.auth.id
  path_part   = "forgot-password"
}

# Forgot Password POST Method
resource "aws_api_gateway_method" "forgot_password_post" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.forgot_password.id
  http_method   = "POST"
  authorization = "NONE"
}

# Forgot Password Integration
resource "aws_api_gateway_integration" "forgot_password_post" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.forgot_password.id
  http_method = aws_api_gateway_method.forgot_password_post.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.auth_handler.invoke_arn
}

# Confirm Forgot Password Resource
resource "aws_api_gateway_resource" "confirm_forgot_password" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_resource.auth.id
  path_part   = "confirm-forgot-password"
}

# Confirm Forgot Password POST Method
resource "aws_api_gateway_method" "confirm_forgot_password_post" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.confirm_forgot_password.id
  http_method   = "POST"
  authorization = "NONE"
}

# Confirm Forgot Password Integration
resource "aws_api_gateway_integration" "confirm_forgot_password_post" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.confirm_forgot_password.id
  http_method = aws_api_gateway_method.confirm_forgot_password_post.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.auth_handler.invoke_arn
}

# Upload Resource
resource "aws_api_gateway_resource" "upload" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_rest_api.main.root_resource_id
  path_part   = "upload"
}

resource "aws_api_gateway_resource" "image" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_rest_api.main.root_resource_id
  path_part   = "image"
}

# Upload POST Method
resource "aws_api_gateway_method" "upload_post" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.upload.id
  http_method   = "POST"
  authorization = "NONE"
}

# Upload Integration
resource "aws_api_gateway_integration" "upload_post" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.upload.id
  http_method = aws_api_gateway_method.upload_post.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.upload_handler.invoke_arn
}

# Upload OPTIONS Method (CORS)
resource "aws_api_gateway_method" "upload_options" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.upload.id
  http_method   = "OPTIONS"
  authorization = "NONE"
}

# Upload OPTIONS Integration
resource "aws_api_gateway_integration" "upload_options" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.upload.id
  http_method = aws_api_gateway_method.upload_options.http_method
  type        = "MOCK"
  
  request_templates = {
    "application/json" = "{\"statusCode\": 200}"
  }
}

# Upload OPTIONS Method Response
resource "aws_api_gateway_method_response" "upload_options" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.upload.id
  http_method = aws_api_gateway_method.upload_options.http_method
  status_code = "200"
  
  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = true
    "method.response.header.Access-Control-Allow-Methods" = true
    "method.response.header.Access-Control-Allow-Origin"  = true
  }
}

# Upload OPTIONS Integration Response
resource "aws_api_gateway_integration_response" "upload_options" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.upload.id
  http_method = aws_api_gateway_method.upload_options.http_method
  status_code = aws_api_gateway_method_response.upload_options.status_code
  
  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'"
    "method.response.header.Access-Control-Allow-Methods" = "'GET,POST,PUT,DELETE,OPTIONS'"
    "method.response.header.Access-Control-Allow-Origin"  = "'*'"
  }
}

# Lambda permissions for API Gateway
resource "aws_lambda_permission" "auth_handler" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.auth_handler.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.main.execution_arn}/*/*"
}

resource "aws_lambda_permission" "upload_handler" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.upload_handler.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.main.execution_arn}/*/*"
}

resource "aws_api_gateway_method" "image_get" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.image.id
  http_method   = "GET"
  authorization = "NONE"
}

# Image OPTIONS Method (CORS)
resource "aws_api_gateway_method" "image_options" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.image.id
  http_method   = "OPTIONS"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "image_get" {
  rest_api_id             = aws_api_gateway_rest_api.main.id
  resource_id             = aws_api_gateway_resource.image.id
  http_method             = aws_api_gateway_method.image_get.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.image_retrieval.invoke_arn
}

# Image OPTIONS Integration
resource "aws_api_gateway_integration" "image_options" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.image.id
  http_method = aws_api_gateway_method.image_options.http_method
  type        = "MOCK"
  
  request_templates = {
    "application/json" = "{\"statusCode\": 200}"
  }
}

# Image OPTIONS Method Response
resource "aws_api_gateway_method_response" "image_options" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.image.id
  http_method = aws_api_gateway_method.image_options.http_method
  status_code = "200"
  
  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = true
    "method.response.header.Access-Control-Allow-Methods" = true
    "method.response.header.Access-Control-Allow-Origin"  = true
  }
}

# Image OPTIONS Integration Response
resource "aws_api_gateway_integration_response" "image_options" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.image.id
  http_method = aws_api_gateway_method.image_options.http_method
  status_code = aws_api_gateway_method_response.image_options.status_code
  
  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'"
    "method.response.header.Access-Control-Allow-Methods" = "'GET,POST,PUT,DELETE,OPTIONS'"
    "method.response.header.Access-Control-Allow-Origin"  = "'*'"
  }
}

resource "aws_lambda_permission" "image_retrieval" {
  statement_id  = "AllowAPIGatewayInvokeImageRetrieval"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.image_retrieval.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.main.execution_arn}/*/*"
}
