import json
import boto3
import os
from datetime import datetime
from botocore.exceptions import ClientError

# Initialize AWS clients
sqs_client = boto3.client('sqs')
s3_client = boto3.client('s3')

# Get environment variables
SQS_QUEUE_URL = os.environ.get('SQS_QUEUE_URL')

def main(event, context):
    """Lambda handler for processing S3 upload events and enqueuing messages to SQS."""
    print(f"=== S3 EVENT HANDLER STARTED ===")
    print(f"Event received: {json.dumps(event, indent=2)}")
    print(f"Context: RequestId={context.aws_request_id}, FunctionName={context.function_name}")
    
    try:
        # Process each S3 event
        for i, record in enumerate(event['Records']):
            print(f"Processing record {i+1}/{len(event['Records'])}")
            process_s3_event(record)
        
        print(f"=== S3 EVENT HANDLER COMPLETED SUCCESSFULLY ===")
        return {
            'statusCode': 200,
            'body': json.dumps({'message': 'S3 events processed successfully'})
        }
        
    except Exception as e:
        print(f"=== S3 EVENT HANDLER FAILED ===")
        print(f"Error in S3 event handler: {str(e)}")
        print(f"Error type: {type(e).__name__}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': 'Internal server error'})
        }

def process_s3_event(record):
    """Process a single S3 event record."""
    print(f"--- Processing S3 Event Record ---")
    try:
        # Extract S3 event information
        s3_event = record['s3']
        bucket_name = s3_event['bucket']['name']
        object_key = s3_event['object']['key']
        event_name = record['eventName']
        
        print(f"S3 Event Details:")
        print(f"  - Event Name: {event_name}")
        print(f"  - Bucket: {bucket_name}")
        print(f"  - Object Key: {object_key}")
        print(f"  - Object Size: {s3_event['object'].get('size', 'Unknown')}")
        print(f"  - Event Time: {record.get('eventTime', 'Unknown')}")
        
        # Only process ObjectCreated events
        if not event_name.startswith('ObjectCreated'):
            print(f"SKIPPING: Non-creation event detected: {event_name}")
            return
        
        print(f"PROCESSING: ObjectCreated event confirmed")
        
        # Extract user information from object key
        # Format: uploads/{user_id}/{uuid}.{extension}
        print(f"Extracting user info from object key: {object_key}")
        user_info = extract_user_info_from_key(object_key)
        if not user_info:
            print(f"ERROR: Could not extract user info from object key: {object_key}")
            print(f"Expected format: uploads/{{user_id}}/{{uuid}}.{{extension}}")
            return
        
        print(f"User info extracted successfully:")
        print(f"  - User ID: {user_info['user_id']}")
        print(f"  - Filename: {user_info['filename']}")
        
        # Prepare SQS message
        message_body = {
            'image_id': object_key,
            'bucket_name': bucket_name,
            'user_id': user_info['user_id'],
            'user_email': user_info.get('user_email', 'unknown'),  # Will be populated later
            'file_size': s3_event['object']['size'],
            'event_timestamp': record['eventTime'],
            'event_name': event_name,
            'upload_timestamp': datetime.utcnow().isoformat(),
            'original_filename': user_info['filename']
        }
        
        print(f"SQS Message prepared:")
        print(f"  - Image ID: {message_body['image_id']}")
        print(f"  - User ID: {message_body['user_id']}")
        print(f"  - File Size: {message_body['file_size']}")
        print(f"  - Upload Timestamp: {message_body['upload_timestamp']}")
        
        # Send message to SQS
        send_sqs_message(message_body)
        
        print(f"SUCCESS: Message enqueued for image: {object_key}")
        
    except Exception as e:
        print(f"ERROR: Failed to process S3 event")
        print(f"Error details: {str(e)}")
        print(f"Error type: {type(e).__name__}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        raise

def extract_user_info_from_key(object_key):
    """Extract user information from S3 object key."""
    print(f"Extracting user info from key: {object_key}")
    try:
        # Expected format: uploads/{user_id}/{uuid}.{extension}
        parts = object_key.split('/')
        print(f"Key parts: {parts}")
        
        if len(parts) != 3:
            print(f"ERROR: Invalid key format. Expected 3 parts, got {len(parts)}")
            return None
        
        if parts[0] != 'uploads':
            print(f"ERROR: Key does not start with 'uploads'. Got: {parts[0]}")
            return None
        
        user_id = parts[1]
        filename = parts[2]
        
        print(f"Parsed components:")
        print(f"  - User ID: {user_id}")
        print(f"  - Filename: {filename}")
        
        # Validate user_id is not empty
        if not user_id:
            print(f"ERROR: User ID is empty")
            return None
        
        result = {
            'user_id': user_id,
            'filename': filename
        }
        
        print(f"User info extraction successful: {result}")
        return result
        
    except Exception as e:
        print(f"ERROR: Failed to extract user info from object key")
        print(f"Error details: {str(e)}")
        print(f"Error type: {type(e).__name__}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return None

def send_sqs_message(message_body):
    """Send message to SQS queue."""
    print(f"Sending message to SQS queue: {SQS_QUEUE_URL}")
    try:
        message_attributes = {
            'MessageType': {
                'StringValue': 'ImageUploadEvent',
                'DataType': 'String'
            },
            'UserId': {
                'StringValue': message_body['user_id'],
                'DataType': 'String'
            },
            'ImageId': {
                'StringValue': message_body['image_id'],
                'DataType': 'String'
            }
        }
        
        print(f"Message attributes:")
        for key, value in message_attributes.items():
            print(f"  - {key}: {value['StringValue']}")
        
        response = sqs_client.send_message(
            QueueUrl=SQS_QUEUE_URL,
            MessageBody=json.dumps(message_body),
            MessageAttributes=message_attributes
        )
        
        print(f"SUCCESS: Message sent to SQS")
        print(f"  - Message ID: {response['MessageId']}")
        print(f"  - MD5: {response['MD5OfMessageBody']}")
        
    except ClientError as e:
        print(f"ERROR: Failed to send message to SQS")
        print(f"Error code: {e.response['Error']['Code']}")
        print(f"Error message: {e.response['Error']['Message']}")
        raise
    except Exception as e:
        print(f"ERROR: Unexpected error sending message to SQS")
        print(f"Error details: {str(e)}")
        print(f"Error type: {type(e).__name__}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        raise 