import json
import boto3
import os
from PIL import Image, ImageDraw, ImageFont
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

# Watermark configurations
WATERMARK_TEXT = os.environ.get('WATERMARK_TEXT', 'PROCESSED')
WATERMARK_FONT_SIZE = int(os.environ.get('WATERMARK_FONT_SIZE', '100'))
WATERMARK_OPACITY = int(os.environ.get('WATERMARK_OPACITY', '128'))  # 0-255
WATERMARK_POSITION = os.environ.get('WATERMARK_POSITION', 'bottom-right')



def main(event, context):
    """Lambda handler for actual image watermarking."""
    print(f"=== WATERMARK STARTED (Real Image Processing) ===")
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
        
        # Convert to RGBA if necessary for watermarking
        if image.mode != 'RGBA':
            image = image.convert('RGBA')
        
        # Create watermark text
        watermark_text = f"{WATERMARK_TEXT} - {datetime.utcnow().strftime('%Y-%m-%d')}"
        print(f"Watermark text: {watermark_text}")
        
        # Create a new image for the watermark
        watermark_layer = Image.new('RGBA', image.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(watermark_layer)
        
        # Try to use a default font, fallback to basic if not available
        try:
            # Try to use a system font
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", WATERMARK_FONT_SIZE)
        except:
            try:
                # Try another common font path
                font = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", WATERMARK_FONT_SIZE)
            except:
                # Fallback to default font
                font = ImageFont.load_default()
                print("Using default font for watermark")
        
        # Get text size
        bbox = draw.textbbox((0, 0), watermark_text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        # Calculate position based on WATERMARK_POSITION
        if WATERMARK_POSITION == 'top-left':
            position = (10, 10)
        elif WATERMARK_POSITION == 'top-right':
            position = (image.width - text_width - 10, 10)
        elif WATERMARK_POSITION == 'bottom-left':
            position = (10, image.height - text_height - 10)
        elif WATERMARK_POSITION == 'center':
            position = ((image.width - text_width) // 2, (image.height - text_height) // 2)
        else:  # bottom-right (default)
            position = (image.width - text_width - 10, image.height - text_height - 10)
        
        print(f"Watermark position: {position}")
        
        # Draw watermark text with semi-transparency
        draw.text(position, watermark_text, font=font, fill=(255, 255, 255, WATERMARK_OPACITY))
        
        # Composite the watermark onto the original image
        watermarked_image = Image.alpha_composite(image, watermark_layer)
        
        # Convert back to RGB if original was not RGBA
        if original_format.upper() in ['JPEG', 'JPG']:
            # Create white background for JPEG
            background = Image.new('RGB', watermarked_image.size, (255, 255, 255))
            background.paste(watermarked_image, mask=watermarked_image.split()[-1] if watermarked_image.mode == 'RGBA' else None)
            watermarked_image = background
        
        # Save to bytes
        output_buffer = BytesIO()
        
        if original_format.upper() in ['JPEG', 'JPG']:
            watermarked_image.save(output_buffer, format='JPEG', quality=85, optimize=True)
            file_extension = 'jpg'
            content_type = 'image/jpeg'
        elif original_format.upper() == 'PNG':
            watermarked_image.save(output_buffer, format='PNG', optimize=True)
            file_extension = 'png'
            content_type = 'image/png'
        else:
            # Default to JPEG
            watermarked_image.save(output_buffer, format='JPEG', quality=85, optimize=True)
            file_extension = 'jpg'
            content_type = 'image/jpeg'
        
        output_buffer.seek(0)
        watermarked_data = output_buffer.getvalue()
        
        # Create output key
        base_name = os.path.splitext(original_filename)[0] if original_filename != 'image' else actual_image_id
        output_key = f"watermarked/{actual_image_id}/{base_name}_watermarked.{file_extension}"
        
        # Upload watermarked image to S3
        print(f"Uploading watermarked image: {output_key}")
        s3_client.put_object(
            Bucket=OUTPUT_BUCKET,
            Key=output_key,
            Body=watermarked_data,
            ContentType=content_type,
            ServerSideEncryption='aws:kms',
            SSEKMSKeyId=KMS_KEY_ID,
            Metadata={
                'original-key': image_key,
                'original-size': f"{original_size[0]}x{original_size[1]}",
                'watermark-text': watermark_text,
                'watermark-position': WATERMARK_POSITION,
                'watermark-opacity': str(WATERMARK_OPACITY),
                'user-id': user_id,
                'processed-by': 'lambda-watermark',
                'processing-date': datetime.utcnow().isoformat()
            }
        )
        
        # Update DynamoDB with processing results
        print(f"Updating DynamoDB...")
        dynamodb_client.update_item(
            TableName=DYNAMODB_TABLE,
            Key={'image_id': {'S': actual_image_id}},
            UpdateExpression='SET processing_status = :status, watermark_result = :result, updated_at = :updated',
            ExpressionAttributeValues={
                ':status': {'S': 'watermarked'},
                ':result': {'M': {
                    'key': {'S': output_key},
                    'watermark_text': {'S': watermark_text},
                    'position': {'S': WATERMARK_POSITION},
                    'format': {'S': file_extension}
                }},
                ':updated': {'S': datetime.utcnow().isoformat()}
            }
        )
        

        
        result = {
            'status': 'success',
            'message': 'Successfully watermarked image',
            'watermarked_image': {
                'key': output_key,
                'watermark_text': watermark_text,
                'position': WATERMARK_POSITION,
                'format': file_extension,
                'content_type': content_type
            },
            'original_size': f"{original_size[0]}x{original_size[1]}",
            'original_format': original_format,
            'image_id': actual_image_id,
            'user_id': user_id
        }
        
        print(f"=== WATERMARK COMPLETED SUCCESSFULLY ===")
        print(f"Result: {json.dumps(result)}")
        
        return result
        
    except Exception as e:
        error_msg = f"Error in watermark function: {str(e)}"
        print(f"=== WATERMARK FAILED ===")
        print(error_msg)
        
        # Update DynamoDB with error status
        try:
            if 'actual_image_id' in locals():
                dynamodb_client.update_item(
                    TableName=DYNAMODB_TABLE,
                    Key={'image_id': {'S': actual_image_id}},
                    UpdateExpression='SET processing_status = :status, error_message = :error, updated_at = :updated',
                    ExpressionAttributeValues={
                        ':status': {'S': 'watermark_failed'},
                        ':error': {'S': error_msg},
                        ':updated': {'S': datetime.utcnow().isoformat()}
                    }
                )
        except Exception as db_error:
            print(f"Failed to update DynamoDB: {str(db_error)}")
        
        raise Exception(error_msg) 