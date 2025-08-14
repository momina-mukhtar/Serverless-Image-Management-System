import json
import boto3
import os
from datetime import datetime
from botocore.exceptions import ClientError

# Initialize AWS clients
dynamodb_client = boto3.client('dynamodb')
s3_client = boto3.client('s3', config=boto3.session.Config(signature_version='s3v4'))
cognito_client = boto3.client('cognito-idp')

# Get environment variables
OUTPUT_BUCKET = os.environ.get('OUTPUT_BUCKET')
DYNAMODB_TABLE = os.environ.get('DYNAMODB_TABLE')
USER_POOL_ID = os.environ.get('USER_POOL_ID')
CLIENT_ID = os.environ.get('CLIENT_ID')

def validate_token(token):
    """Validate JWT token and return user information."""
    print(f"Validating token with Cognito...")
    try:
        response = cognito_client.get_user(
            AccessToken=token
        )
        
        print(f"Cognito response received:")
        print(f"  - Username: {response['Username']}")
        print(f"  - User Attributes Count: {len(response['UserAttributes'])}")
        
        # Extract user attributes
        user_attributes = {attr['Name']: attr['Value'] for attr in response['UserAttributes']}
        
        user_info = {
            'sub': response['Username'],
            'email': user_attributes.get('email', ''),
            'email_verified': user_attributes.get('email_verified', 'false') == 'true'
        }
        
        print(f"User info extracted:")
        print(f"  - Sub: {user_info['sub']}")
        print(f"  - Email: {user_info['email']}")
        print(f"  - Email Verified: {user_info['email_verified']}")
        
        return user_info
        
    except ClientError as e:
        print(f"ERROR: Cognito token validation failed")
        print(f"Error code: {e.response['Error']['Code']}")
        print(f"Error message: {e.response['Error']['Message']}")
        return None
    except Exception as e:
        print(f"ERROR: Unexpected error during token validation")
        print(f"Error details: {str(e)}")
        print(f"Error type: {type(e).__name__}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return None

def main(event, context):
    """Lambda handler for retrieving processed images."""
    print(f"=== IMAGE RETRIEVAL STARTED ===")
    print(f"Event: {json.dumps(event)}")
    
    try:
        # Parse the event
        http_method = event.get('httpMethod', '')
        print(f"HTTP Method: {http_method}")
        
        if http_method == 'GET':
            return handle_image_retrieval(event)
        elif http_method == 'OPTIONS':
            return handle_cors_preflight()
        else:
            print(f"ERROR: Unsupported HTTP method: {http_method}")
            return create_response(405, {'error': 'Method not allowed'})
            
    except Exception as e:
        print(f"=== IMAGE RETRIEVAL FAILED ===")
        print(f"Error in image retrieval handler: {str(e)}")
        print(f"Error type: {type(e).__name__}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return create_response(500, {'error': 'Internal server error'})

def handle_image_retrieval(event):
    """Handle image retrieval request."""
    print(f"--- Handling Image Retrieval Request ---")
    try:
        # Validate authorization header
        auth_header = event.get('headers', {}).get('Authorization', '')
        print(f"Authorization header: {auth_header[:20]}..." if len(auth_header) > 20 else f"Authorization header: {auth_header}")
        
        if not auth_header.startswith('Bearer '):
            print(f"ERROR: Invalid authorization header format")
            return create_response(401, {'error': 'Authorization header required'})
        
        token = auth_header.split(' ')[1]
        print(f"Token extracted (first 20 chars): {token[:20]}...")
        
        # Validate token and get user info
        print(f"Validating token with Cognito...")
        user_info = validate_token(token)
        if not user_info:
            print(f"ERROR: Token validation failed")
            return create_response(401, {'error': 'Invalid token'})
        
        print(f"Token validation successful:")
        print(f"  - User ID: {user_info['sub']}")
        print(f"  - Email: {user_info['email']}")
        
        # Extract image_id (filename) from the request
        image_id = event.get('queryStringParameters', {}).get('image_id')
        
        if not image_id:
            print(f"ERROR: Missing image_id parameter")
            return create_response(400, {'error': 'image_id parameter is required'})
        
        print(f"Requested image ID (filename): {image_id}")
        
        # Use the authenticated user's ID directly
        user_id = user_info['sub']
        print(f"Authenticated user ID: {user_id}")
        
        # Construct the watermarked image key based on the predictable path structure
        # Format: watermarked/{user_id}/{image_id}_watermarked.{extension}
        
        # Default to jpg extension (can be overridden by query parameter)
        file_extension = event.get('queryStringParameters', {}).get('extension', 'jpg')
        
        # Construct the watermarked image key
        image_key = f"watermarked/{user_id}/{image_id}_watermarked.{file_extension}"
        
        print(f"Constructed watermarked image key: {image_key}")
        
        # Check if the file exists in S3 before generating pre-signed URL
        print(f"Checking if file exists in S3 bucket...")
        try:
            s3_client.head_object(Bucket=OUTPUT_BUCKET, Key=image_key)
            print(f"✓ File exists in S3 bucket")
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == '404' or error_code == 'NoSuchKey':
                print(f"✗ File not found in S3 bucket: {image_key}")
                return create_response(404, {
                    'error': 'Image not found',
                    'message': f'The requested image "{image_id}" was not found in your processed images.',
                    'image_id': image_id,
                    'user_id': user_id,
                    'searched_path': image_key
                })
            else:
                print(f"✗ Error checking file existence: {error_code}")
                return create_response(500, {
                    'error': 'Error checking image availability',
                    'message': 'Unable to verify if the image exists. Please try again later.'
                })
        
        # Generate pre-signed URL for the processed image
        print(f"Generating pre-signed URL...")
        
        # Since the bucket has default KMS encryption, we don't need to specify KMS parameters
        # The pre-signed URL will work with the bucket's default encryption
        presigned_url = s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': OUTPUT_BUCKET, 'Key': image_key},
            ExpiresIn=3600  # 1 hour expiration
        )
        
        # Prepare response with image details
        result = {
            'image_id': image_id,
            'user_id': user_id,
            'processed_image': {
                'key': image_key,
                'download_url': presigned_url,
                'expires_in': '1 hour',
                'extension': file_extension
            }
        }
        
        print(f"=== IMAGE RETRIEVAL COMPLETED SUCCESSFULLY ===")
        print(f"Result: {json.dumps(result)}")
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type,Authorization',
                'Access-Control-Allow-Methods': 'GET,OPTIONS'
            },
            'body': json.dumps(result)
        }
        
    except Exception as e:
        error_msg = f"Error in image retrieval function: {str(e)}"
        print(f"=== IMAGE RETRIEVAL FAILED ===")
        print(error_msg)
        
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type,Authorization',
                'Access-Control-Allow-Methods': 'GET,OPTIONS'
            },
            'body': json.dumps({
                'error': 'Internal server error',
                'message': error_msg
            })
        }

def handle_cors_preflight():
    """Handle CORS preflight request."""
    return create_response(200, {})

def create_response(status_code, body):
    """Create a standardized API Gateway response."""
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type,Authorization',
            'Access-Control-Allow-Methods': 'GET,OPTIONS'
        },
        'body': json.dumps(body)
    } 