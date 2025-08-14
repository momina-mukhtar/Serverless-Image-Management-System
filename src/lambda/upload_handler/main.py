import json
import boto3
import os
import uuid
from datetime import datetime, timedelta
from botocore.exceptions import ClientError

# Initialize AWS clients
s3_client = boto3.client('s3', config=boto3.session.Config(signature_version='s3v4'))
cognito_client = boto3.client('cognito-idp')

# Get environment variables
INPUT_BUCKET = os.environ.get('INPUT_BUCKET')
USER_POOL_ID = os.environ.get('USER_POOL_ID')
CLIENT_ID = os.environ.get('CLIENT_ID')

def main(event, context):
    """Lambda handler for generating S3 pre-signed URLs for image upload."""
    print(f"=== UPLOAD HANDLER STARTED ===")
    print(f"Event received: {json.dumps(event, indent=2)}")
    print(f"Context: RequestId={context.aws_request_id}, FunctionName={context.function_name}")
    print(f"Environment variables:")
    print(f"  - INPUT_BUCKET: {INPUT_BUCKET}")
    print(f"  - USER_POOL_ID: {USER_POOL_ID}")
    print(f"  - CLIENT_ID: {CLIENT_ID}")
    
    try:
        # Parse the event
        http_method = event.get('httpMethod', '')
        print(f"HTTP Method: {http_method}")
        
        if http_method == 'POST':
            return handle_upload_request(event)
        elif http_method == 'OPTIONS':
            return handle_cors_preflight()
        else:
            print(f"ERROR: Unsupported HTTP method: {http_method}")
            return create_response(405, {'error': 'Method not allowed'})
            
    except Exception as e:
        print(f"=== UPLOAD HANDLER FAILED ===")
        print(f"Error in upload handler: {str(e)}")
        print(f"Error type: {type(e).__name__}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return create_response(500, {'error': 'Internal server error'})

def handle_upload_request(event):
    """Handle upload request and generate pre-signed URL."""
    print(f"--- Handling Upload Request ---")
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
        print(f"  - Email Verified: {user_info['email_verified']}")
        
        # Parse request body
        body = json.loads(event.get('body', '{}'))
        file_name = body.get('fileName')
        file_type = body.get('fileType')
        
        print(f"Request body parameters:")
        print(f"  - File Name: {file_name}")
        print(f"  - File Type: {file_type}")
        
        if not file_name or not file_type:
            print(f"ERROR: Missing required parameters")
            return create_response(400, {'error': 'fileName and fileType are required'})
        
        # Validate file type
        allowed_types = ['image/jpeg', 'image/png', 'image/gif']
        print(f"Validating file type: {file_type}")
        print(f"Allowed types: {allowed_types}")
        
        if file_type not in allowed_types:
            print(f"ERROR: Invalid file type: {file_type}")
            return create_response(400, {'error': 'Invalid file type. Only JPEG, PNG, and GIF are allowed.'})
        
        print(f"✓ File type validation passed")
        
        # Validate Content-Type format
        if not file_type or '/' not in file_type or len(file_type.split('/')) != 2:
            print(f"ERROR: Invalid Content-Type format: {file_type}")
            return create_response(400, {'error': 'Invalid Content-Type format. Must be in format: type/subtype'})
        
        print(f"✓ Content-Type format validation passed")
        
        # Generate unique file key
        file_extension = get_file_extension(file_type)
        file_key = f"uploads/{user_info['sub']}/{uuid.uuid4()}{file_extension}"
        
        print(f"Generated file key:")
        print(f"  - Extension: {file_extension}")
        print(f"  - Full key: {file_key}")
        
        # Generate pre-signed URL
        print(f"Generating pre-signed URL...")
        presigned_url = generate_presigned_url(file_key, file_type, user_info)
        
        print(f"Pre-signed URL generated successfully")
        print(f"  - URL length: {len(presigned_url)} characters")
        print(f"  - URL preview: {presigned_url[:100]}...")
        
        response_data = {
            'uploadUrl': presigned_url,
            'fileKey': file_key,
            'expiresIn': 3600  # 1 hour
        }
        
        print(f"Response data prepared:")
        print(f"  - File Key: {response_data['fileKey']}")
        print(f"  - Expires In: {response_data['expiresIn']} seconds")
        
        return create_response(200, response_data)
        
    except json.JSONDecodeError as e:
        print(f"ERROR: Failed to parse JSON in request body")
        print(f"Error details: {str(e)}")
        return create_response(400, {'error': 'Invalid JSON in request body'})
    except Exception as e:
        print(f"ERROR: Failed to handle upload request")
        print(f"Error details: {str(e)}")
        print(f"Error type: {type(e).__name__}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return create_response(500, {'error': 'Internal server error'})

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

def generate_presigned_url(file_key, file_type, user_info):
    """Generate pre-signed URL for S3 upload with SSE-KMS."""
    print(f"Generating pre-signed URL for S3 upload...")
    print(f"  - File Key: {file_key}")
    print(f"  - File Type: {file_type}")
    print(f"  - User ID: {user_info['sub']}")
    
    try:
        # Get KMS key ID from environment
        kms_key_id = os.environ.get('S3_KMS_KEY_ID', 'alias/aws/s3')
        print(f"  - KMS Key ID: {kms_key_id}")
        
        # Generate pre-signed URL with explicit SSE-KMS parameters
        # This is required due to the bucket policy that enforces SSE-KMS
        presigned_params = {
            'Bucket': INPUT_BUCKET,
            'Key': file_key,
            'ContentType': file_type,
            'ServerSideEncryption': 'aws:kms',
            'SSEKMSKeyId': kms_key_id
        }
        
        print(f"Pre-signed URL parameters:")
        for key, value in presigned_params.items():
            print(f"    - {key}: {value}")
        
        presigned_url = s3_client.generate_presigned_url(
            'put_object',
            Params=presigned_params,
            ExpiresIn=7200  # 2 hours - increased for debugging
        )
        
        print(f"Pre-signed URL generated successfully:")
        print(f"  - URL length: {len(presigned_url)} characters")
        print(f"  - Expires in: 7200 seconds (2 hours)")
        print(f"  - SSE-KMS enabled with key: {kms_key_id}")
        
        return presigned_url
        
    except Exception as e:
        print(f"ERROR: Failed to generate pre-signed URL")
        print(f"Error details: {str(e)}")
        print(f"Error type: {type(e).__name__}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        raise

def get_file_extension(file_type):
    """Get file extension based on MIME type."""
    extensions = {
        'image/jpeg': '.jpg',
        'image/png': '.png',
        'image/gif': '.gif'
    }
    
    extension = extensions.get(file_type, '')
    print(f"File extension mapping:")
    print(f"  - MIME Type: {file_type}")
    print(f"  - Extension: {extension}")
    
    return extension

def handle_cors_preflight():
    """Handle CORS preflight requests."""
    print(f"Handling CORS preflight request")
    return create_response(200, {})

def create_response(status_code, body):
    """Create a standardized API Gateway response."""
    print(f"Creating API Gateway response:")
    print(f"  - Status Code: {status_code}")
    print(f"  - Body: {json.dumps(body, indent=2) if isinstance(body, dict) else str(body)}")
    
    response = {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
            'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS'
        },
        'body': json.dumps(body)
    }
    
    print(f"Response created successfully")
    return response 