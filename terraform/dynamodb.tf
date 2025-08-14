# DynamoDB Table for Image Metadata
resource "aws_dynamodb_table" "image_metadata" {
  name           = "image-metadata-${random_id.suffix.hex}"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "image_id"
  
  # Point-in-time recovery for backup
  point_in_time_recovery {
    enabled = true
  }

  # Attribute definitions
  attribute {
    name = "image_id"
    type = "S"
  }
  
  attribute {
    name = "user_id"
    type = "S"
  }
  
  attribute {
    name = "status"
    type = "S"
  }
  
  attribute {
    name = "upload_timestamp"
    type = "S"
  }

  # Global Secondary Index for user queries
  global_secondary_index {
    name            = "user-id-index"
    hash_key        = "user_id"
    range_key       = "upload_timestamp"
    projection_type = "ALL"
  }

  # Global Secondary Index for status queries
  global_secondary_index {
    name            = "status-index"
    hash_key        = "status"
    range_key       = "upload_timestamp"
    projection_type = "ALL"
  }

  # Server-side encryption
  server_side_encryption {
    enabled     = true
    kms_key_arn = aws_kms_key.dynamodb.arn
  }

  tags = {
    Name = "image-metadata-table"
    Environment = "production"
  }
}

# Note: Auto scaling is not available for PAY_PER_REQUEST billing mode
# The table will automatically scale based on demand
