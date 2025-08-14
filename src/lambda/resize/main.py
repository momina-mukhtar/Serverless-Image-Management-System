import json
import boto3
import os
from PIL import Image
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
KMS_KEY_ID = os.environ.get('KMS_KEY_ID', 'alias/aws/s3')

# Resize configurations
RESIZE_DIMENSIONS = [
    (800, 600),   # Medium
    (1200, 900),  # Large
    (400, 300)    # Thumbnail
]

def main(event, context):
    """Lambda handler for actual image resizing."""
    print(f"=== RESIZE STARTED (Real Image Processing) ===")
    print(f"Event: {json.dumps(event)}")
    
    try:
        # Extract input from Step Functions event
        if 'input' in event:
            input_data = event['input']
        else:
            input_data = event
            
        # Extract required fields
        image_key = input_data.get('image_id')  # This contains the full S3 key path
        bucket_name = input_data.get('bucket_name')
        user_id = input_data.get('user_id', 'unknown')
        original_filename = input_data.get('original_filename', 'image')
        
        # Extract the actual image_id from the S3 key path
        # image_key format: "uploads/{user_id}/{filename}"
        if image_key and '/' in image_key:
            path_parts = image_key.split('/')
            if len(path_parts) >= 3:
                actual_image_id = path_parts[1]  # The user_id part
            else:
                actual_image_id = user_id  # Fallback to user_id
        else:
            actual_image_id = user_id  # Fallback to user_id
        
        print(f"Processing image: {image_key}")
        print(f"Actual Image ID: {actual_image_id}")
        print(f"User ID: {user_id}")
        print(f"Bucket: {bucket_name}")
        print(f"Original filename: {original_filename}")
        
        # Validate required fields
        if not image_key:
            raise Exception("image_key is required but not provided")
        if not bucket_name:
            raise Exception("bucket_name is required but not provided")
        
        # Download original image from S3
        print(f"Downloading image from S3...")
        response = s3_client.get_object(Bucket=INPUT_BUCKET, Key=image_key)
        image_data = response['Body'].read()
        
        # Open image with Pillow
        image = Image.open(BytesIO(image_data))
        original_format = image.format or 'JPEG'
        original_size = image.size
        
        print(f"Original image size: {original_size}")
        print(f"Original format: {original_format}")
        
        # Process each resize dimension
        processed_images = []
        
        for width, height in RESIZE_DIMENSIONS:
            print(f"Resizing to {width}x{height}...")
            
            # Calculate new dimensions maintaining aspect ratio
            img_ratio = image.width / image.height
            target_ratio = width / height
            
            if img_ratio > target_ratio:
                # Image is wider than target ratio
                new_width = width
                new_height = int(width / img_ratio)
            else:
                # Image is taller than target ratio
                new_height = height
                new_width = int(height * img_ratio)
            
            # Resize image
            resized_image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            # Convert to RGB if necessary (for JPEG compatibility)
            if resized_image.mode in ('RGBA', 'LA', 'P'):
                # Create white background
                background = Image.new('RGB', resized_image.size, (255, 255, 255))
                if resized_image.mode == 'P':
                    resized_image = resized_image.convert('RGBA')
                background.paste(resized_image, mask=resized_image.split()[-1] if resized_image.mode == 'RGBA' else None)
                resized_image = background
            
            # Save to bytes
            output_buffer = BytesIO()
            
            if original_format.upper() in ['JPEG', 'JPG']:
                resized_image.save(output_buffer, format='JPEG', quality=85, optimize=True)
                file_extension = 'jpg'
                content_type = 'image/jpeg'
            elif original_format.upper() == 'PNG':
                resized_image.save(output_buffer, format='PNG', optimize=True)
                file_extension = 'png'
                content_type = 'image/png'
            else:
                # Default to JPEG
                resized_image.save(output_buffer, format='JPEG', quality=85, optimize=True)
                file_extension = 'jpg'
                content_type = 'image/jpeg'
            
            output_buffer.seek(0)
            resized_data = output_buffer.getvalue()
            
            # Create output key
            base_name = os.path.splitext(original_filename)[0] if original_filename != 'image' else actual_image_id
            output_key = f"resized/{actual_image_id}/{base_name}_{new_width}x{new_height}.{file_extension}"
            
            # Upload resized image to S3
            print(f"Uploading resized image: {output_key}")
            s3_client.put_object(
                Bucket=OUTPUT_BUCKET,
                Key=output_key,
                Body=resized_data,
                ContentType=content_type,
                ServerSideEncryption='aws:kms',
                SSEKMSKeyId=KMS_KEY_ID,
                Metadata={
                    'original-key': image_key,
                    'original-size': f"{original_size[0]}x{original_size[1]}",
                    'resized-size': f"{new_width}x{new_height}",
                    'user-id': user_id,
                    'processed-by': 'lambda-resize',
                    'processing-date': datetime.utcnow().isoformat()
                }
            )
            
            processed_images.append({
                'key': output_key,
                'size': f"{new_width}x{new_height}",
                'format': file_extension,
                'content_type': content_type
            })
            
            print(f"Successfully processed: {output_key}")
        
        # Update DynamoDB with processing results
        print(f"Updating DynamoDB...")
        dynamodb_client.update_item(
            TableName=DYNAMODB_TABLE,
            Key={'image_id': {'S': actual_image_id}},
            UpdateExpression='SET processing_status = :status, resize_results = :results, updated_at = :updated',
            ExpressionAttributeValues={
                ':status': {'S': 'resized'},
                ':results': {'L': [{'M': {
                    'key': {'S': img['key']},
                    'size': {'S': img['size']},
                    'format': {'S': img['format']}
                }} for img in processed_images]},
                ':updated': {'S': datetime.utcnow().isoformat()}
            }
        )
        
        result = {
            'status': 'success',
            'message': f'Successfully resized image to {len(processed_images)} variants',
            'processed_images': processed_images,
            'original_size': f"{original_size[0]}x{original_size[1]}",
            'original_format': original_format,
            'image_id': actual_image_id,
            'user_id': user_id
        }
        
        print(f"=== RESIZE COMPLETED SUCCESSFULLY ===")
        print(f"Result: {json.dumps(result)}")
        
        return result
        
    except Exception as e:
        error_msg = f"Error in resize function: {str(e)}"
        print(f"=== RESIZE FAILED ===")
        print(error_msg)
        
        # Update DynamoDB with error status
        try:
            if 'actual_image_id' in locals():
                dynamodb_client.update_item(
                    TableName=DYNAMODB_TABLE,
                    Key={'image_id': {'S': actual_image_id}},
                    UpdateExpression='SET processing_status = :status, error_message = :error, updated_at = :updated',
                    ExpressionAttributeValues={
                        ':status': {'S': 'resize_failed'},
                        ':error': {'S': error_msg},
                        ':updated': {'S': datetime.utcnow().isoformat()}
                    }
                )
        except Exception as db_error:
            print(f"Failed to update DynamoDB: {str(db_error)}")
        
        raise Exception(error_msg) 