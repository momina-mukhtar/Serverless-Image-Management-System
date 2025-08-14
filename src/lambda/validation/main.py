import json
import boto3
import os
import imghdr
# Remove PIL import to avoid _imaging issues
# from PIL import Image
from io import BytesIO
from botocore.exceptions import ClientError
from datetime import datetime

# Initialize AWS clients
s3_client = boto3.client('s3')
dynamodb_client = boto3.client('dynamodb')

# Get environment variables
INPUT_BUCKET = os.environ.get('INPUT_BUCKET')
OUTPUT_BUCKET = os.environ.get('OUTPUT_BUCKET')
DYNAMODB_TABLE = os.environ.get('DYNAMODB_TABLE')

# Validation constants
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
ALLOWED_FORMATS = ['jpeg', 'jpg', 'png', 'gif']
MIN_DIMENSIONS = (100, 100)  # Minimum width and height

def main(event, context):
    """Lambda handler for image validation."""
    print(f"=== VALIDATION STARTED ===")
    print(f"Event received: {json.dumps(event, indent=2)}")
    print(f"Context: RequestId={context.aws_request_id}, FunctionName={context.function_name}")
    print(f"Environment variables:")
    print(f"  - INPUT_BUCKET: {INPUT_BUCKET}")
    print(f"  - OUTPUT_BUCKET: {OUTPUT_BUCKET}")
    print(f"  - DYNAMODB_TABLE: {DYNAMODB_TABLE}")
    print(f"Validation constants:")
    print(f"  - MAX_FILE_SIZE: {MAX_FILE_SIZE} bytes ({MAX_FILE_SIZE/1024/1024:.1f} MB)")
    print(f"  - ALLOWED_FORMATS: {ALLOWED_FORMATS}")
    print(f"  - MIN_DIMENSIONS: {MIN_DIMENSIONS}")
    
    try:
        # Parse input from Step Functions
        input_data = event
        
        image_id = input_data['image_id']
        bucket_name = input_data['bucket_name']
        user_id = input_data['user_id']
        user_email = input_data['user_email']
        
        print(f"Validation parameters:")
        print(f"  - Image ID: {image_id}")
        print(f"  - Bucket Name: {bucket_name}")
        print(f"  - User ID: {user_id}")
        print(f"  - User Email: {user_email}")
        
        print(f"Starting validation for image: {image_id}")
        
        # Download image from S3
        print(f"Downloading image from S3...")
        image_data = download_image(bucket_name, image_id)
        if not image_data:
            raise Exception(f"Failed to download image: {image_id}")
        
        print(f"Image downloaded successfully:")
        print(f"  - Size: {len(image_data)} bytes")
        
        # Validate image
        print(f"Starting image validation...")
        validation_result = validate_image(image_data, image_id)
        
        print(f"Validation completed:")
        print(f"  - Is Valid: {validation_result['is_valid']}")
        if 'error' in validation_result:
            print(f"  - Error: {validation_result['error']}")
        if 'image_info' in validation_result:
            print(f"  - Image Info: {validation_result['image_info']}")
        
        if validation_result['is_valid']:
            # Update DynamoDB status
            print(f"Updating DynamoDB with validation success...")
            update_validation_status(image_id, 'validated', validation_result)
            
            print(f"=== VALIDATION COMPLETED SUCCESSFULLY ===")
            # Return success for Step Functions
            return {
                'statusCode': 200,
                'image_id': image_id,
                'validation_result': validation_result,
                'status': 'validated'
            }
        else:
            # Update DynamoDB status
            print(f"Updating DynamoDB with validation failure...")
            update_validation_status(image_id, 'validation_failed', validation_result)
            
            print(f"=== VALIDATION FAILED ===")
            # Return error for Step Functions
            raise Exception(f"Image validation failed: {validation_result['error']}")
            
    except Exception as e:
        print(f"=== VALIDATION FAILED ===")
        print(f"Error in validation: {str(e)}")
        print(f"Error type: {type(e).__name__}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        # Update DynamoDB with error status
        if 'image_id' in locals():
            update_validation_status(image_id, 'validation_error', {'error': str(e)})
        raise

def download_image(bucket_name, image_id):
    """Download image from S3."""
    print(f"Downloading image from S3...")
    print(f"  - Bucket: {bucket_name}")
    print(f"  - Key: {image_id}")
    
    try:
        response = s3_client.get_object(
            Bucket=bucket_name,
            Key=image_id
        )
        
        image_data = response['Body'].read()
        
        print(f"Image download successful:")
        print(f"  - Content Length: {response.get('ContentLength', 'Unknown')}")
        print(f"  - Content Type: {response.get('ContentType', 'Unknown')}")
        print(f"  - ETag: {response.get('ETag', 'Unknown')}")
        print(f"  - Actual data size: {len(image_data)} bytes")
        
        return image_data
        
    except ClientError as e:
        print(f"ERROR: Failed to download image from S3")
        print(f"Error code: {e.response['Error']['Code']}")
        print(f"Error message: {e.response['Error']['Message']}")
        return None
    except Exception as e:
        print(f"ERROR: Unexpected error downloading image")
        print(f"Error details: {str(e)}")
        print(f"Error type: {type(e).__name__}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return None

def validate_image(image_data, image_id):
    """Validate image file type, size, and integrity without PIL."""
    print(f"--- Image Validation Process (No PIL) ---")
    try:
        # Check file size
        file_size = len(image_data)
        print(f"File size validation:")
        print(f"  - Actual size: {file_size} bytes ({file_size/1024/1024:.2f} MB)")
        print(f"  - Max allowed: {MAX_FILE_SIZE} bytes ({MAX_FILE_SIZE/1024/1024:.2f} MB)")
        
        if file_size > MAX_FILE_SIZE:
            error_msg = f'File size {file_size} exceeds maximum allowed size {MAX_FILE_SIZE}'
            print(f"VALIDATION FAILED: {error_msg}")
            return {
                'is_valid': False,
                'error': error_msg
            }
        
        print(f"✓ File size validation passed")
        
        # Check file format using imghdr
        print(f"File format validation using imghdr...")
        image_format = imghdr.what(None, h=image_data)
        print(f"  - Detected format: {image_format}")
        print(f"  - Allowed formats: {ALLOWED_FORMATS}")
        
        if not image_format or image_format.lower() not in ALLOWED_FORMATS:
            error_msg = f'Invalid file format: {image_format}. Allowed formats: {ALLOWED_FORMATS}'
            print(f"VALIDATION FAILED: {error_msg}")
            return {
                'is_valid': False,
                'error': error_msg
            }
        
        print(f"✓ File format validation passed")
        
        # Basic file header validation for common image formats
        print(f"File header validation...")
        if not validate_image_headers(image_data, image_format):
            error_msg = f'Invalid image file header for format: {image_format}'
            print(f"VALIDATION FAILED: {error_msg}")
            return {
                'is_valid': False,
                'error': error_msg
            }
        
        print(f"✓ File header validation passed")
        
        # For now, skip dimension validation without PIL
        # We'll do dimension validation in the resize function instead
        print(f"⚠️  Skipping dimension validation (will be done in resize function)")
        
        # Return success with basic image info
        image_info = {
            'format': image_format,
            'size_bytes': file_size,
            'dimensions_validated': False  # Will be validated in resize function
        }
        
        print(f"✓ Basic image validation completed successfully")
        return {
            'is_valid': True,
            'image_info': image_info
        }
        
    except Exception as e:
        print(f"ERROR: Validation failed with exception")
        print(f"Error details: {str(e)}")
        print(f"Error type: {type(e).__name__}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return {
            'is_valid': False,
            'error': f'Validation error: {str(e)}'
        }

def validate_image_headers(image_data, format_type):
    """Validate image file headers for common formats."""
    if not image_data or len(image_data) < 8:
        return False
    
    # JPEG validation
    if format_type in ['jpeg', 'jpg']:
        return image_data[:2] == b'\xff\xd8' and image_data[-2:] == b'\xff\xd9'
    
    # PNG validation
    elif format_type == 'png':
        return image_data[:8] == b'\x89PNG\r\n\x1a\n'
    
    # GIF validation
    elif format_type == 'gif':
        return image_data[:6] in [b'GIF87a', b'GIF89a']
    
    # For other formats, assume valid if imghdr detected them
    return True

def update_validation_status(image_id, status, validation_result):
    """Update DynamoDB with validation status."""
    print(f"Updating DynamoDB validation status...")
    try:
        update_expression = "SET #status = :status, #validation_result = :validation_result, #updated_at = :updated_at"
        expression_attribute_names = {
            '#status': 'status',
            '#validation_result': 'validation_result',
            '#updated_at': 'updated_at'
        }
        expression_attribute_values = {
            ':status': {'S': status},
            ':validation_result': {'S': json.dumps(validation_result)},
            ':updated_at': {'S': datetime.utcnow().isoformat()}
        }
        
        print(f"DynamoDB update parameters:")
        print(f"  - Table: {DYNAMODB_TABLE}")
        print(f"  - Image ID: {image_id}")
        print(f"  - Status: {status}")
        print(f"  - Validation Result: {json.dumps(validation_result, indent=2)}")
        
        dynamodb_client.update_item(
            TableName=DYNAMODB_TABLE,
            Key={
                'image_id': {'S': image_id}
            },
            UpdateExpression=update_expression,
            ExpressionAttributeNames=expression_attribute_names,
            ExpressionAttributeValues=expression_attribute_values
        )
        
        print(f"SUCCESS: DynamoDB validation status updated for image: {image_id}")
        
    except ClientError as e:
        print(f"ERROR: Failed to update DynamoDB validation status")
        print(f"Error code: {e.response['Error']['Code']}")
        print(f"Error message: {e.response['Error']['Message']}")
        # Don't raise here as this is not critical for validation
    except Exception as e:
        print(f"ERROR: Unexpected error updating DynamoDB validation status")
        print(f"Error details: {str(e)}")
        print(f"Error type: {type(e).__name__}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        # Don't raise here as this is not critical for validation 