# Setting Up AWS S3 & CloudFront for Image Storage

This guide will walk you through **creating an S3 bucket, setting up CloudFront, and obtaining the necessary credentials** for configuration.

---

## **✅ 1️⃣ Creating an S3 Bucket**
1. **Go to AWS Console → [S3](https://s3.console.aws.amazon.com/s3/home)**
2. Click **"Create bucket"**.
3. **Set the bucket name** (e.g., `my-image-bucket`).
4. **Region:** Choose the region closest to your users (e.g., `us-east-1`).
5. **Uncheck "Block all public access"** (⚠️ Only if using `public-read` mode).
6. **Enable "Bucket Versioning"** (optional, for tracking file versions).
7. Click **"Create bucket"**.

📌 **To make images public:**  
- Go to **Bucket → Permissions → Bucket Policy** and add:
  ```json
  {
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Principal": "*",
        "Action": "s3:GetObject",
        "Resource": "arn:aws:s3:::my-image-bucket/*"
      }
    ]
  }
  ```
  - Replace `"my-image-bucket"` with your actual bucket name.

---

## **✅ 2️⃣ Creating an IAM User & Getting API Keys**
To interact with S3, you need **AWS Access Keys**.

1. **Go to AWS Console → [IAM](https://console.aws.amazon.com/iam/home)**.
2. Click **"Users" → "Create User"**.
3. **Username:** `s3-image-uploader`
4. **Permissions:** Select **"Attach policies directly"** and add:
   - ✅ `AmazonS3FullAccess` (or `AmazonS3ReadOnlyAccess` for read-only access).
5. Click **"Create user"**.
6. **Go to "Security Credentials" → "Access Keys" → "Create Access Key"**.
7. Copy:
   - **AWS Access Key ID**
   - **AWS Secret Access Key**

---

## **✅ 3️⃣ Setting Up CloudFront for Faster Image Delivery**
CloudFront caches and accelerates content delivery.

1. **Go to AWS Console → [CloudFront](https://console.aws.amazon.com/cloudfront/home)**
2. Click **"Create Distribution"**.
3. **Origin Settings**:
   - **Origin Domain**: Select your **S3 bucket**.
   - **Origin Access**: Choose **"Origin Access Control Settings (OAC)"**.
   - **Click "Create Control Setting" → "Allow CloudFront to access S3"**.
4. **Default Cache Behavior**:
   - **Viewer Protocol Policy**: `Redirect HTTP to HTTPS`
   - **Allowed HTTP Methods**: `GET, HEAD`
   - **Cache Policy**: `CachingOptimized`
5. Click **"Create Distribution"**.
6. **Copy the CloudFront Domain Name** (e.g., `https://d123abc.cloudfront.net/`).

---

## **✅ 4️⃣ Configuring `.env` for Tortoise ImageField**
After setting up S3 & CloudFront, update your `.env` file:

```ini
DATABASE_URL=sqlite://db.sqlite3
IMAGES_UPLOAD_DIR=uploads
IMAGES_UPLOAD_URL=uploads

# S3 Configuration
S3_BUCKET=my-image-bucket
S3_REGION=us-east-1
S3_ACCESS_KEY=your-access-key
S3_SECRET_KEY=your-secret-key
S3_CDN_DOMAIN=https://d123abc.cloudfront.net/
```

---

## **✅ 5️⃣ Verifying Setup**
Run the following Python script to check your configuration:

```python
import boto3
import os

s3 = boto3.client(
    "s3",
    aws_access_key_id=os.getenv("S3_ACCESS_KEY"),
    aws_secret_access_key=os.getenv("S3_SECRET_KEY"),
    region_name=os.getenv("S3_REGION")
)

# List Buckets
response = s3.list_buckets()
print("✅ S3 Buckets:", [bucket["Name"] for bucket in response["Buckets"]])

# Generate Presigned URL (if private access)
url = s3.generate_presigned_url(
    "get_object",
    Params={"Bucket": os.getenv("S3_BUCKET"), "Key": "test-image.jpg"},
    ExpiresIn=3600
)
print("🔗 Temporary Image URL:", url)
```

---

## **📌 Summary**
| Step | Description |
|------|------------|
| **S3 Bucket** | Created `my-image-bucket`, allowed public read. |
| **IAM Keys** | Created user `s3-image-uploader`, assigned `AmazonS3FullAccess`. |
| **CloudFront** | Created CDN for fast image delivery. |
| **Environment Variables** | Configured `.env` with S3 & CloudFront. |
