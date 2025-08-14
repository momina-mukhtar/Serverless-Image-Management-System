import json
import boto3
import os
from botocore.exceptions import ClientError

# Initialize Cognito client
cognito_client = boto3.client('cognito-idp')

# Get environment variables
USER_POOL_ID = os.environ.get('USER_POOL_ID')
CLIENT_ID = os.environ.get('CLIENT_ID')

def main(event, context):
    """Lambda handler for authentication endpoints (sign up, sign in, verify, forgot password, etc.)."""
    print(f"=== AUTH HANDLER STARTED ===")
    print(f"Event received: {json.dumps(event, indent=2)}")
    print(f"Context: RequestId={context.aws_request_id}, FunctionName={context.function_name}")
    print(f"Environment variables:")
    print(f"  - USER_POOL_ID: {USER_POOL_ID}")
    print(f"  - CLIENT_ID: {CLIENT_ID}")
    
    try:
        # Parse the event
        http_method = event.get('httpMethod', '')
        path = event.get('path', '')
        
        print(f"Request details:")
        print(f"  - HTTP Method: {http_method}")
        print(f"  - Path: {path}")
        
        # Route to appropriate handler based on path
        if path.endswith('/signup'):
            print(f"Routing to signup handler")
            return handle_signup(event)
        elif path.endswith('/signin'):
            print(f"Routing to signin handler")
            return handle_signin(event)
        elif path.endswith('/verify'):
            print(f"Routing to verify handler")
            return handle_verify(event)
        elif path.endswith('/forgot-password'):
            print(f"Routing to forgot-password handler")
            return handle_forgot_password(event)
        elif path.endswith('/confirm-forgot-password'):
            print(f"Routing to confirm-forgot-password handler")
            return handle_confirm_forgot_password(event)
        else:
            print(f"ERROR: Unknown endpoint: {path}")
            return create_response(404, {'error': 'Endpoint not found'})
            
    except Exception as e:
        print(f"=== AUTH HANDLER FAILED ===")
        print(f"Error in auth handler: {str(e)}")
        print(f"Error type: {type(e).__name__}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return create_response(500, {'error': 'Internal server error'})

def handle_signup(event):
    """Handle user sign up."""
    print(f"--- Handling Signup Request ---")
    try:
        body = json.loads(event.get('body', '{}'))
        email = body.get('email')
        password = body.get('password')
        
        print(f"Signup parameters:")
        print(f"  - Email: {email}")
        print(f"  - Password: {'*' * len(password) if password else 'None'}")
        
        if not email or not password:
            print(f"ERROR: Missing required parameters")
            return create_response(400, {'error': 'Email and password are required'})
        
        print(f"Calling Cognito sign_up...")
        # Sign up user with Cognito
        response = cognito_client.sign_up(
            ClientId=CLIENT_ID,
            Username=email,
            Password=password,
            UserAttributes=[
                {
                    'Name': 'email',
                    'Value': email
                }
            ]
        )
        
        print(f"Cognito sign_up response:")
        print(f"  - User Sub: {response['UserSub']}")
        print(f"  - User Confirmed: {response.get('UserConfirmed', False)}")
        print(f"  - Code Delivery Details: {response.get('CodeDeliveryDetails', {})}")
        
        return create_response(200, {
            'message': 'User registered successfully. Please check your email for verification code.',
            'userSub': response['UserSub']
        })
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        print(f"ERROR: Cognito sign_up failed")
        print(f"  - Error Code: {error_code}")
        print(f"  - Error Message: {error_message}")
        
        if error_code == 'UsernameExistsException':
            return create_response(409, {'error': 'User already exists'})
        elif error_code == 'InvalidPasswordException':
            return create_response(400, {'error': 'Password does not meet requirements'})
        else:
            return create_response(400, {'error': str(e)})
    except json.JSONDecodeError as e:
        print(f"ERROR: Failed to parse JSON in request body")
        print(f"Error details: {str(e)}")
        return create_response(400, {'error': 'Invalid JSON in request body'})
    except Exception as e:
        print(f"ERROR: Unexpected error in signup")
        print(f"Error details: {str(e)}")
        print(f"Error type: {type(e).__name__}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return create_response(500, {'error': 'Internal server error'})

def handle_signin(event):
    """Handle user sign in."""
    print(f"--- Handling Signin Request ---")
    try:
        body = json.loads(event.get('body', '{}'))
        email = body.get('email')
        password = body.get('password')
        
        print(f"Signin parameters:")
        print(f"  - Email: {email}")
        print(f"  - Password: {'*' * len(password) if password else 'None'}")
        
        if not email or not password:
            print(f"ERROR: Missing required parameters")
            return create_response(400, {'error': 'Email and password are required'})
        
        print(f"Calling Cognito initiate_auth...")
        # Sign in user with Cognito
        response = cognito_client.initiate_auth(
            ClientId=CLIENT_ID,
            AuthFlow='USER_PASSWORD_AUTH',
            AuthParameters={
                'USERNAME': email,
                'PASSWORD': password
            }
        )
        
        print(f"Cognito initiate_auth response:")
        print(f"  - Challenge Name: {response.get('ChallengeName', 'None')}")
        print(f"  - Session: {response.get('Session', 'None')}")
        print(f"  - Has Authentication Result: {bool(response.get('AuthenticationResult'))}")
        
        if 'AuthenticationResult' in response:
            auth_result = response['AuthenticationResult']
            print(f"  - Access Token Length: {len(auth_result.get('AccessToken', ''))}")
            print(f"  - ID Token Length: {len(auth_result.get('IdToken', ''))}")
            print(f"  - Refresh Token Length: {len(auth_result.get('RefreshToken', ''))}")
            print(f"  - Expires In: {auth_result.get('ExpiresIn', 'Unknown')}")
        
        return create_response(200, {
            'message': 'Sign in successful',
            'tokens': {
                'accessToken': response['AuthenticationResult']['AccessToken'],
                'refreshToken': response['AuthenticationResult']['RefreshToken'],
                'idToken': response['AuthenticationResult']['IdToken']
            }
        })
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        print(f"ERROR: Cognito initiate_auth failed")
        print(f"  - Error Code: {error_code}")
        print(f"  - Error Message: {error_message}")
        
        if error_code == 'UserNotConfirmedException':
            return create_response(400, {'error': 'User not confirmed. Please verify your email.'})
        elif error_code == 'NotAuthorizedException':
            return create_response(401, {'error': 'Invalid credentials'})
        else:
            return create_response(400, {'error': str(e)})
    except json.JSONDecodeError as e:
        print(f"ERROR: Failed to parse JSON in request body")
        print(f"Error details: {str(e)}")
        return create_response(400, {'error': 'Invalid JSON in request body'})
    except Exception as e:
        print(f"ERROR: Unexpected error in signin")
        print(f"Error details: {str(e)}")
        print(f"Error type: {type(e).__name__}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return create_response(500, {'error': 'Internal server error'})

def handle_verify(event):
    """Handle email verification."""
    print(f"--- Handling Verify Request ---")
    try:
        body = json.loads(event.get('body', '{}'))
        email = body.get('email')
        code = body.get('code')
        
        print(f"Verify parameters:")
        print(f"  - Email: {email}")
        print(f"  - Code: {code}")
        
        if not email or not code:
            print(f"ERROR: Missing required parameters")
            return create_response(400, {'error': 'Email and verification code are required'})
        
        print(f"Calling Cognito confirm_sign_up...")
        # Confirm sign up with verification code
        response = cognito_client.confirm_sign_up(
            ClientId=CLIENT_ID,
            Username=email,
            ConfirmationCode=code
        )
        
        print(f"Cognito confirm_sign_up response received")
        
        return create_response(200, {'message': 'Email verified successfully'})
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        print(f"ERROR: Cognito confirm_sign_up failed")
        print(f"  - Error Code: {error_code}")
        print(f"  - Error Message: {error_message}")
        
        if error_code == 'CodeMismatchException':
            return create_response(400, {'error': 'Invalid verification code'})
        else:
            return create_response(400, {'error': str(e)})
    except json.JSONDecodeError as e:
        print(f"ERROR: Failed to parse JSON in request body")
        print(f"Error details: {str(e)}")
        return create_response(400, {'error': 'Invalid JSON in request body'})
    except Exception as e:
        print(f"ERROR: Unexpected error in verify")
        print(f"Error details: {str(e)}")
        print(f"Error type: {type(e).__name__}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return create_response(500, {'error': 'Internal server error'})

def handle_forgot_password(event):
    """Handle forgot password request."""
    print(f"--- Handling Forgot Password Request ---")
    try:
        body = json.loads(event.get('body', '{}'))
        email = body.get('email')
        
        print(f"Forgot password parameters:")
        print(f"  - Email: {email}")
        
        if not email:
            print(f"ERROR: Missing required parameters")
            return create_response(400, {'error': 'Email is required'})
        
        print(f"Calling Cognito forgot_password...")
        # Initiate forgot password flow
        response = cognito_client.forgot_password(
            ClientId=CLIENT_ID,
            Username=email
        )
        
        print(f"Cognito forgot_password response:")
        print(f"  - Code Delivery Details: {response.get('CodeDeliveryDetails', {})}")
        
        return create_response(200, {'message': 'Password reset code sent to your email'})
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        print(f"ERROR: Cognito forgot_password failed")
        print(f"  - Error Code: {error_code}")
        print(f"  - Error Message: {error_message}")
        
        if error_code == 'UserNotFoundException':
            return create_response(404, {'error': 'User not found'})
        else:
            return create_response(400, {'error': str(e)})
    except json.JSONDecodeError as e:
        print(f"ERROR: Failed to parse JSON in request body")
        print(f"Error details: {str(e)}")
        return create_response(400, {'error': 'Invalid JSON in request body'})
    except Exception as e:
        print(f"ERROR: Unexpected error in forgot password")
        print(f"Error details: {str(e)}")
        print(f"Error type: {type(e).__name__}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return create_response(500, {'error': 'Internal server error'})

def handle_confirm_forgot_password(event):
    """Handle confirm forgot password."""
    print(f"--- Handling Confirm Forgot Password Request ---")
    try:
        body = json.loads(event.get('body', '{}'))
        email = body.get('email')
        code = body.get('code')
        new_password = body.get('newPassword')
        
        print(f"Confirm forgot password parameters:")
        print(f"  - Email: {email}")
        print(f"  - Code: {code}")
        print(f"  - New Password: {'*' * len(new_password) if new_password else 'None'}")
        
        if not email or not code or not new_password:
            print(f"ERROR: Missing required parameters")
            return create_response(400, {'error': 'Email, code, and new password are required'})
        
        print(f"Calling Cognito confirm_forgot_password...")
        # Confirm forgot password
        response = cognito_client.confirm_forgot_password(
            ClientId=CLIENT_ID,
            Username=email,
            ConfirmationCode=code,
            Password=new_password
        )
        
        print(f"Cognito confirm_forgot_password response received")
        
        return create_response(200, {'message': 'Password reset successfully'})
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        print(f"ERROR: Cognito confirm_forgot_password failed")
        print(f"  - Error Code: {error_code}")
        print(f"  - Error Message: {error_message}")
        
        if error_code == 'CodeMismatchException':
            return create_response(400, {'error': 'Invalid reset code'})
        elif error_code == 'InvalidPasswordException':
            return create_response(400, {'error': 'New password does not meet requirements'})
        else:
            return create_response(400, {'error': str(e)})
    except json.JSONDecodeError as e:
        print(f"ERROR: Failed to parse JSON in request body")
        print(f"Error details: {str(e)}")
        return create_response(400, {'error': 'Invalid JSON in request body'})
    except Exception as e:
        print(f"ERROR: Unexpected error in confirm forgot password")
        print(f"Error details: {str(e)}")
        print(f"Error type: {type(e).__name__}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return create_response(500, {'error': 'Internal server error'})

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