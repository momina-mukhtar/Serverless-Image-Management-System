import json
import boto3
import os
from datetime import datetime
from botocore.exceptions import ClientError

# Initialize AWS clients
stepfunctions_client = boto3.client('stepfunctions')
dynamodb_client = boto3.client('dynamodb')

# Get environment variables
STATE_MACHINE_ARN = os.environ.get('STATE_MACHINE_ARN')
DYNAMODB_TABLE = os.environ.get('DYNAMODB_TABLE')

def main(event, context):
    """Lambda handler for orchestrating the Step Functions workflow."""
    print(f"=== ORCHESTRATOR STARTED ===")
    print(f"Event received: {json.dumps(event, indent=2)}")
    print(f"Context: RequestId={context.aws_request_id}, FunctionName={context.function_name}")
    print(f"Environment variables:")
    print(f"  - STATE_MACHINE_ARN: {STATE_MACHINE_ARN}")
    print(f"  - DYNAMODB_TABLE: {DYNAMODB_TABLE}")
    
    try:
        # Process each SQS message
        for i, record in enumerate(event['Records']):
            print(f"Processing SQS record {i+1}/{len(event['Records'])}")
            process_sqs_message(record)
        
        print(f"=== ORCHESTRATOR COMPLETED SUCCESSFULLY ===")
        return {
            'statusCode': 200,
            'body': json.dumps({'message': 'SQS messages processed successfully'})
        }
        
    except Exception as e:
        print(f"=== ORCHESTRATOR FAILED ===")
        print(f"Error in orchestrator: {str(e)}")
        print(f"Error type: {type(e).__name__}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': 'Internal server error'})
        }

def process_sqs_message(record):
    """Process a single SQS message and start Step Functions workflow."""
    print(f"--- Processing SQS Message ---")
    try:
        # Parse SQS message
        message_body = json.loads(record['body'])
        message_id = record['messageId']
        
        print(f"SQS Message Details:")
        print(f"  - Message ID: {message_id}")
        print(f"  - Receipt Handle: {record['receiptHandle'][:50]}...")
        print(f"  - Message Body: {json.dumps(message_body, indent=2)}")
        
        # Extract image and user information
        image_id = message_body['image_id']
        bucket_name = message_body['bucket_name']
        user_id = message_body['user_id']
        user_email = message_body.get('user_email', 'unknown')
        upload_timestamp = message_body['upload_timestamp']
        original_filename = message_body.get('original_filename', 'unknown')
        file_size = message_body['file_size']
        
        print(f"Extracted Information:")
        print(f"  - Image ID: {image_id}")
        print(f"  - Bucket Name: {bucket_name}")
        print(f"  - User ID: {user_id}")
        print(f"  - User Email: {user_email}")
        print(f"  - Upload Timestamp: {upload_timestamp}")
        print(f"  - Original Filename: {original_filename}")
        print(f"  - File Size: {file_size}")
        
        # Create workflow input
        workflow_input = {
            'image_id': image_id,
            'bucket_name': bucket_name,
            'user_id': user_id,
            'user_email': user_email,
            'upload_timestamp': upload_timestamp,
            'original_filename': original_filename,
            'file_size': file_size,
            'processing_start_time': datetime.utcnow().isoformat(),
            'status': 'processing'
        }
        
        print(f"Workflow Input prepared:")
        print(f"  - Processing Start Time: {workflow_input['processing_start_time']}")
        print(f"  - Initial Status: {workflow_input['status']}")
        
        # Start Step Functions workflow
        print(f"Starting Step Functions workflow...")
        execution_arn = start_workflow(workflow_input)
        
        print(f"Step Functions workflow started successfully:")
        print(f"  - Execution ARN: {execution_arn}")
        
        # Update DynamoDB with initial status
        print(f"Updating DynamoDB with initial status...")
        update_dynamodb_status(image_id, user_id, 'processing', execution_arn)
        
        print(f"SUCCESS: Workflow orchestration completed for image: {image_id}")
        print(f"  - Execution ARN: {execution_arn}")
        
    except json.JSONDecodeError as e:
        print(f"ERROR: Failed to parse SQS message JSON")
        print(f"Error details: {str(e)}")
        print(f"Message body: {record.get('body', 'No body')}")
        raise
    except Exception as e:
        print(f"ERROR: Failed to process SQS message")
        print(f"Error details: {str(e)}")
        print(f"Error type: {type(e).__name__}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        raise

def start_workflow(workflow_input):
    """Start Step Functions workflow execution."""
    print(f"Starting Step Functions workflow...")
    try:
        # Generate unique execution name (must be <= 80 characters)
        timestamp = int(datetime.utcnow().timestamp())
        image_id = workflow_input['image_id']
        user_id = workflow_input['user_id']
        
        # Create a shorter, unique name using hash of image_id and timestamp
        import hashlib
        image_hash = hashlib.md5(image_id.encode()).hexdigest()[:8]
        execution_name = f"img-{user_id[:8]}-{image_hash}-{timestamp}"
        
        print(f"Generated execution name: {execution_name}")
        print(f"Execution name length: {len(execution_name)} characters")
        print(f"State Machine ARN: {STATE_MACHINE_ARN}")
        
        workflow_input_json = json.dumps(workflow_input)
        print(f"Workflow input JSON: {workflow_input_json}")
        
        response = stepfunctions_client.start_execution(
            stateMachineArn=STATE_MACHINE_ARN,
            name=execution_name,
            input=workflow_input_json
        )
        
        execution_arn = response['executionArn']
        print(f"Step Functions response:")
        print(f"  - Execution ARN: {execution_arn}")
        print(f"  - Start Date: {response.get('startDate', 'Unknown')}")
        
        return execution_arn
        
    except ClientError as e:
        print(f"ERROR: Failed to start Step Functions workflow")
        print(f"Error code: {e.response['Error']['Code']}")
        print(f"Error message: {e.response['Error']['Message']}")
        raise
    except Exception as e:
        print(f"ERROR: Unexpected error starting Step Functions workflow")
        print(f"Error details: {str(e)}")
        print(f"Error type: {type(e).__name__}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        raise

def update_dynamodb_status(image_id, user_id, status, execution_arn=None):
    """Update DynamoDB with processing status."""
    print(f"Updating DynamoDB status...")
    try:
        update_expression = "SET #status = :status, #updated_at = :updated_at"
        expression_attribute_names = {
            '#status': 'status',
            '#updated_at': 'updated_at'
        }
        expression_attribute_values = {
            ':status': {'S': status},
            ':updated_at': {'S': datetime.utcnow().isoformat()}
        }
        
        if execution_arn:
            update_expression += ", #execution_arn = :execution_arn"
            expression_attribute_names['#execution_arn'] = 'execution_arn'
            expression_attribute_values[':execution_arn'] = {'S': execution_arn}
        
        print(f"DynamoDB update parameters:")
        print(f"  - Table: {DYNAMODB_TABLE}")
        print(f"  - Image ID: {image_id}")
        print(f"  - Status: {status}")
        print(f"  - Execution ARN: {execution_arn}")
        print(f"  - Update Expression: {update_expression}")
        
        dynamodb_client.update_item(
            TableName=DYNAMODB_TABLE,
            Key={
                'image_id': {'S': image_id}
            },
            UpdateExpression=update_expression,
            ExpressionAttributeNames=expression_attribute_names,
            ExpressionAttributeValues=expression_attribute_values
        )
        
        print(f"SUCCESS: DynamoDB status updated for image: {image_id}")
        
    except ClientError as e:
        print(f"ERROR: Failed to update DynamoDB status")
        print(f"Error code: {e.response['Error']['Code']}")
        print(f"Error message: {e.response['Error']['Message']}")
        # Don't raise here as this is not critical for workflow execution
    except Exception as e:
        print(f"ERROR: Unexpected error updating DynamoDB status")
        print(f"Error details: {str(e)}")
        print(f"Error type: {type(e).__name__}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        # Don't raise here as this is not critical for workflow execution 