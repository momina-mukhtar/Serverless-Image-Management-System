resource "aws_cognito_user_pool" "main" {
  name = "image-processing-user-pool-${random_id.suffix.hex}"

  # Password policy
  password_policy {
    minimum_length    = 8
    require_lowercase = true
    require_numbers   = true
    require_symbols   = true
    require_uppercase = true
    temporary_password_validity_days = 7
  }

  # Account recovery settings
  account_recovery_setting {
    recovery_mechanism {
      name     = "verified_email"
      priority = 1
    }
  }

  # Auto verified attributes
  auto_verified_attributes = ["email"]

  # Username attributes
  username_attributes = ["email"]

  # Email configuration
  email_configuration {
    email_sending_account = "COGNITO_DEFAULT"
  }

  # User pool add-ons
  user_pool_add_ons {
    advanced_security_mode = "OFF"
  }

  # Verification message template
  verification_message_template {
    default_email_option = "CONFIRM_WITH_CODE"
    email_subject       = "Your verification code"
    email_message       = "Your verification code is {####}"
  }

  # Admin create user config
  admin_create_user_config {
    allow_admin_create_user_only = false
  }

  # Schema attributes
  schema {
    attribute_data_type = "String"
    name               = "email"
    required           = true
    mutable            = true

    string_attribute_constraints {
      min_length = 1
      max_length = 256
    }
  }

  # Tags
  tags = {
    Name = "image-processing-user-pool"
    Environment = "production"
  }
}

resource "aws_cognito_user_pool_client" "main" {
  name         = "image-processing-client-${random_id.suffix.hex}"
  user_pool_id = aws_cognito_user_pool.main.id

  # Generate client secret
  generate_secret = false

  # Explicit auth flows
  explicit_auth_flows = [
    "ALLOW_USER_PASSWORD_AUTH",
    "ALLOW_REFRESH_TOKEN_AUTH",
    "ALLOW_USER_SRP_AUTH"
  ]

  # Prevent user existence errors
  prevent_user_existence_errors = "ENABLED"

  # Token validity
  access_token_validity  = 1
  id_token_validity      = 1
  refresh_token_validity = 30

  # Callback URLs
  callback_urls = ["http://localhost:3000/callback"]
  logout_urls   = ["http://localhost:3000/logout"]

  # Allowed OAuth flows
  allowed_oauth_flows = ["code"]

  # Allowed OAuth scopes
  allowed_oauth_scopes = ["email", "openid", "profile"]

  # Supported identity providers
  supported_identity_providers = ["COGNITO"]
}

resource "aws_cognito_user_pool_domain" "main" {
  domain       = "image-processing-${random_id.suffix.hex}"
  user_pool_id = aws_cognito_user_pool.main.id
} 