# Upload Examples with KMS Encryption

## Overview
This guide shows how to use pre-signed URLs with KMS encryption for secure image uploads.

## Complete Upload Flow

### 1. Authentication
```bash
# Sign in to get JWT token
curl -X POST https://your-api-gateway-url/prod/auth/signin \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "YourPassword123!"
  }'
```

### 2. Request Pre-signed URL
```bash
curl -X POST https://your-api-gateway-url/prod/upload \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{
    "fileName": "my-image.jpg",
    "fileType": "image/jpeg"
  }'
```

**Response:**
```json
{
  "uploadUrl": "https://bucket.s3.amazonaws.com/key?X-Amz-Algorithm=...",
  "fileKey": "uploads/user-id/uuid.jpg",
  "expiresIn": 3600
}
```

### 3. Upload to S3

#### JavaScript/Node.js
```javascript
const axios = require('axios');
const fs = require('fs');

async function uploadImage(presignedUrl, filePath, contentType) {
  try {
    const fileBuffer = fs.readFileSync(filePath);
    
    await axios.put(presignedUrl, fileBuffer, {
      headers: {
        'Content-Type': contentType
      }
    });
    
    console.log('Upload successful!');
  } catch (error) {
    console.error('Upload failed:', error.response?.data || error.message);
  }
}
```

#### Python
```python
import requests

def upload_image(presigned_url, file_path, content_type):
    try:
        with open(file_path, 'rb') as file:
            response = requests.put(
                presigned_url,
                data=file,
                headers={
                    'Content-Type': content_type
                }
            )
            response.raise_for_status()
            print('Upload successful!')
    except requests.exceptions.RequestException as e:
        print(f'Upload failed: {e}')
```

#### cURL
```bash
curl -X PUT "PRESIGNED_URL" \
  -H "Content-Type: image/jpeg" \
  --upload-file /path/to/image.jpg
```

## Key Points

### Required Headers
- `Content-Type`: Must match the file type (e.g., `image/jpeg`)

### CORS Configuration
The S3 bucket must have CORS configured to allow these headers:
```json
{
  "allowed_headers": ["*"],
  "allowed_methods": ["GET", "PUT", "POST", "DELETE", "HEAD"],
  "allowed_origins": ["*"],
  "expose_headers": ["ETag", "x-amz-version-id"]
}
```

### Encryption
- Files are automatically encrypted using the bucket's default KMS encryption
- No additional headers required for encryption

## Error Handling

### Common Errors and Solutions

1. **SignatureDoesNotMatch**
   - Ensure CORS allows all headers (`allowed_headers: ["*"]`)
   - Check that Signature Version 4 is enabled
   - Verify Content-Type header matches file type

2. **InvalidArgument - Server Side Encryption with AWS KMS managed keys require AWS Signature Version 4**
   - Lambda function must use `signature_version='s3v4'`

3. **Access Denied**
   - Verify IAM permissions for S3 bucket
   - Check bucket policy allows uploads

## Testing

Test the complete flow:
1. Authenticate and get JWT token
2. Request pre-signed URL
3. Upload with KMS headers
4. Verify file appears in S3 with encryption

The uploaded files will be automatically processed by the image processing pipeline. 