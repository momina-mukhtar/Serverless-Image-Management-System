# S3 Input Bucket
resource "aws_s3_bucket" "input" {
  bucket = "image-processing-input-${random_id.suffix.hex}"
  force_destroy = true
  
  tags = {
    Name = "input-bucket"
    Environment = "production"
  }
}

# S3 Input Bucket Versioning
resource "aws_s3_bucket_versioning" "input" {
  bucket = aws_s3_bucket.input.id
  versioning_configuration {
    status = "Enabled"
  }
}

# S3 Input Bucket Server-Side Encryption
resource "aws_s3_bucket_server_side_encryption_configuration" "input" {
  bucket = aws_s3_bucket.input.id

  rule {
    apply_server_side_encryption_by_default {
      kms_master_key_id = aws_kms_key.s3.arn
      sse_algorithm     = "aws:kms"
    }
    bucket_key_enabled = true
  }
}

# S3 Input Bucket Lifecycle Configuration
resource "aws_s3_bucket_lifecycle_configuration" "input" {
  bucket = aws_s3_bucket.input.id

  rule {
    id     = "input_lifecycle"
    status = "Enabled"

    filter {
      prefix = ""
    }

    transition {
      days          = 30
      storage_class = "STANDARD_IA"
    }

    transition {
      days          = 90
      storage_class = "GLACIER"
    }

    expiration {
      days = 365
    }
  }
}

# S3 Input Bucket CORS Configuration
resource "aws_s3_bucket_cors_configuration" "input" {
  bucket = aws_s3_bucket.input.id

  cors_rule {
    allowed_headers = ["*"]
    allowed_methods = ["GET", "PUT", "POST", "DELETE", "HEAD"]
    allowed_origins = ["*"]
    expose_headers  = ["ETag", "x-amz-version-id"]
    max_age_seconds = 3000
  }
}

# S3 Input Bucket Access Logging
resource "aws_s3_bucket_logging" "input" {
  bucket = aws_s3_bucket.input.id

  target_bucket = aws_s3_bucket.logs.id
  target_prefix = "input-bucket-logs/"
}

# S3 Output Bucket
resource "aws_s3_bucket" "output" {
  bucket = "image-processing-output-${random_id.suffix.hex}"
  force_destroy = true
  
  tags = {
    Name = "output-bucket"
    Environment = "production"
  }
}

# S3 Output Bucket Versioning
resource "aws_s3_bucket_versioning" "output" {
  bucket = aws_s3_bucket.output.id
  versioning_configuration {
    status = "Enabled"
  }
}

# S3 Output Bucket Server-Side Encryption
resource "aws_s3_bucket_server_side_encryption_configuration" "output" {
  bucket = aws_s3_bucket.output.id

  rule {
    apply_server_side_encryption_by_default {
      kms_master_key_id = aws_kms_key.s3.arn
      sse_algorithm     = "aws:kms"
    }
    bucket_key_enabled = true
  }
}

# S3 Output Bucket Lifecycle Configuration
resource "aws_s3_bucket_lifecycle_configuration" "output" {
  bucket = aws_s3_bucket.output.id

  rule {
    id     = "output_lifecycle"
    status = "Enabled"

    filter {
      prefix = ""
    }

    transition {
      days          = 30
      storage_class = "STANDARD_IA"
    }

    transition {
      days          = 90
      storage_class = "GLACIER"
    }

    expiration {
      days = 2555
    }
  }
}

# S3 Output Bucket Access Logging
resource "aws_s3_bucket_logging" "output" {
  bucket = aws_s3_bucket.output.id

  target_bucket = aws_s3_bucket.logs.id
  target_prefix = "output-bucket-logs/"
}

# S3 Logs Bucket
resource "aws_s3_bucket" "logs" {
  bucket = "image-processing-logs-${random_id.suffix.hex}"
  force_destroy = true
  
  tags = {
    Name = "logs-bucket"
    Environment = "production"
  }
}

# S3 Logs Bucket Versioning
resource "aws_s3_bucket_versioning" "logs" {
  bucket = aws_s3_bucket.logs.id
  
  versioning_configuration {
    status = "Enabled"
  }
}

# S3 Logs Bucket Server-Side Encryption
resource "aws_s3_bucket_server_side_encryption_configuration" "logs" {
  bucket = aws_s3_bucket.logs.id
  
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# S3 Logs Bucket Lifecycle Configuration
resource "aws_s3_bucket_lifecycle_configuration" "logs" {
  bucket = aws_s3_bucket.logs.id

  rule {
    id     = "logs_lifecycle"
    status = "Enabled"

    filter {
      prefix = ""
    }

    transition {
      days          = 30
      storage_class = "STANDARD_IA"
    }

    transition {
      days          = 90
      storage_class = "GLACIER"
    }

    expiration {
      days = 2555
    }
  }
}

# S3 Bucket Policies
resource "aws_s3_bucket_policy" "input" {
  bucket = aws_s3_bucket.input.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "DenyUnencryptedObjectUploads"
        Effect = "Deny"
        Principal = {
          AWS = "*"
        }
        Action = [
          "s3:PutObject"
        ]
        Resource = "${aws_s3_bucket.input.arn}/*"
        Condition = {
          StringNotEquals = {
            "s3:x-amz-server-side-encryption" = "aws:kms"
          }
        }
      },
      {
        Sid    = "DenyIncorrectEncryptionHeader"
        Effect = "Deny"
        Principal = {
          AWS = "*"
        }
        Action = [
          "s3:PutObject"
        ]
        Resource = "${aws_s3_bucket.input.arn}/*"
        Condition = {
          StringNotEquals = {
            "s3:x-amz-server-side-encryption-aws-kms-key-id" = aws_kms_key.s3.arn
          }
        }
      }
    ]
  })
}

resource "aws_s3_bucket_policy" "output" {
  bucket = aws_s3_bucket.output.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "DenyUnencryptedObjectUploads"
        Effect = "Deny"
        Principal = {
          AWS = "*"
        }
        Action = [
          "s3:PutObject"
        ]
        Resource = "${aws_s3_bucket.output.arn}/*"
        Condition = {
          StringNotEquals = {
            "s3:x-amz-server-side-encryption" = "aws:kms"
          }
        }
      },
      {
        Sid    = "DenyIncorrectEncryptionHeader"
        Effect = "Deny"
        Principal = {
          AWS = "*"
        }
        Action = [
          "s3:PutObject"
        ]
        Resource = "${aws_s3_bucket.output.arn}/*"
        Condition = {
          StringNotEquals = {
            "s3:x-amz-server-side-encryption-aws-kms-key-id" = aws_kms_key.s3.arn
          }
        }
      }
    ]
  })
}


