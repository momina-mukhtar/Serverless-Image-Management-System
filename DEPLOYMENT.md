# Deployment Guide

This guide provides step-by-step instructions for deploying the Serverless Image Processing Platform on AWS.

## 📋 Prerequisites

### Required Tools

- **AWS CLI** (v2.x or later)
- **Terraform** (v1.0 or later)
- **Python** (3.11 or later)
- **Git**

### AWS Account Setup

1. **Create an AWS Account** (if you don't have one)
2. **Configure AWS CLI**
3. **Verify AWS Access**

### Required Permissions

Your AWS user/role needs the following permissions:
- `AdministratorAccess` (recommended for initial setup)
- Or specific permissions for: EC2, Lambda, S3, DynamoDB, API Gateway, Cognito, Step Functions, SQS, KMS, CloudWatch, IAM

## 🚀 Deployment Steps

### Step 1: Clone and Prepare

1. Clone the repository
2. Verify the structure

### Step 2: Configure Variables (Optional)

Edit `terraform/variables.tf` if you want to customize the deployment region, project name, or other settings.

### Step 3: Deploy Infrastructure

1. Navigate to terraform directory
2. Initialize Terraform
3. Review the deployment plan
4. Apply the configuration

**Expected Output:**
```
Plan: 126 to add, 0 to change, 0 to destroy.

Do you want to perform these actions?
  Terraform will perform the actions described above.
  Only 'yes' will be accepted to approve.

  Enter a value: yes
```

### Step 4: Deploy Lambda Functions

After infrastructure deployment, deploy the Lambda functions using the provided deployment script or manual deployment process.

### Step 5: Verify Deployment

1. Check all resources are created
2. Test API Gateway endpoints

## 🧪 Testing the Platform

### Test Authentication

Test user registration and authentication flows.

### Test Image Upload

Test complete upload flow including pre-signed URL generation and S3 upload.

### Test Image Retrieval

Test image retrieval functionality with different size variants.

## 📊 Monitoring Deployment

### Check CloudWatch Logs

Monitor Lambda function logs and API Gateway access logs.

### Check Step Functions

Monitor workflow executions and processing status.

## 🔧 Configuration

### Environment Variables

Key environment variables are automatically set by Terraform:

| Variable | Description | Set By |
|----------|-------------|---------|
| `USER_POOL_ID` | Cognito User Pool ID | Terraform |
| `CLIENT_ID` | Cognito Client ID | Terraform |
| `INPUT_BUCKET` | S3 Input Bucket Name | Terraform |
| `OUTPUT_BUCKET` | S3 Output Bucket Name | Terraform |
| `DYNAMODB_TABLE` | DynamoDB Table Name | Terraform |
| `STATE_MACHINE_ARN` | Step Functions ARN | Terraform |

### Customization Options

#### Change Region
Modify the AWS region in `terraform/variables.tf`

#### Modify VPC CIDR
Adjust the VPC CIDR block in `terraform/variables.tf`

#### Adjust Lambda Settings
Modify timeout and memory settings in `terraform/lambda.tf`

## 🚨 Troubleshooting

### Common Issues

#### 1. Terraform Plan Fails

**Error:** `Error: No valid credential sources found`

**Solution:** Configure AWS CLI credentials

#### 2. Lambda Deployment Fails

**Error:** `Error: timeout while waiting for state to become 'success'`

**Solution:** Increase timeout settings in Lambda configuration

#### 3. S3 Upload Fails

**Error:** `SignatureDoesNotMatch`

**Solution:** Check CORS configuration and pre-signed URL generation

#### 4. Step Functions Execution Fails

**Error:** `Execution name too long`

**Solution:** Check orchestrator Lambda for execution name generation

### Debugging Steps

1. **Check CloudWatch Logs**
2. **Verify IAM Permissions**
3. **Test API Endpoints**
4. **Check S3 Bucket Policy**

## 🔄 Updates and Maintenance

### Updating Lambda Functions

1. Modify function code in `src/lambda/`
2. Redeploy using the deployment script

### Updating Infrastructure

1. Modify Terraform files
2. Apply changes with `terraform plan` and `terraform apply`

### Scaling Considerations

- **Lambda Concurrency**: Adjust in `terraform/lambda.tf`
- **SQS Visibility Timeout**: Modify in `terraform/sqs.tf`
- **DynamoDB Capacity**: Change in `terraform/dynamodb.tf`

## 🗑️ Cleanup

### Destroy Infrastructure

Remove all resources using `terraform destroy`

**⚠️ Warning:** This will permanently delete all resources and data.

### Manual Cleanup

If terraform destroy fails, manually delete resources in the following order:
1. Lambda functions
2. S3 buckets (must be empty)
3. DynamoDB table
4. Cognito resources

## 📞 Support

If you encounter issues:

1. **Check the logs** in CloudWatch
2. **Review this guide** for common solutions
3. **Check the documentation** in the `docs/` directory
4. **Create an issue** in the repository

## 📚 Additional Resources

- [AWS Lambda Documentation](https://docs.aws.amazon.com/lambda/)
- [Terraform AWS Provider](https://registry.terraform.io/providers/hashicorp/aws/latest/docs)
- [AWS Step Functions Guide](https://docs.aws.amazon.com/step-functions/)
- [Amazon S3 Developer Guide](https://docs.aws.amazon.com/s3/)

---

**Happy Deploying! 🚀** 