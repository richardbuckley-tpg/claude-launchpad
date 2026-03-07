# S3 Object Storage Reference

## Overview
Amazon S3 (and S3-compatible alternatives like Cloudflare R2, MinIO, DigitalOcean Spaces)
for file uploads, media storage, data exports, backups, and static asset hosting.

## Directory Additions

```
src/
├── lib/
│   └── storage/
│       ├── client.ts         # S3 client configuration
│       ├── upload.ts         # Upload utilities (presigned URLs, multipart)
│       ├── download.ts       # Download/stream utilities
│       └── types.ts          # Storage-related types
├── middleware/
│   └── upload.ts             # Multer/Busboy middleware for file uploads
```

## CLAUDE.md Additions

```markdown
## Object Storage
- Provider: AWS S3 (or Cloudflare R2 / MinIO / Supabase Storage)
- Client: @aws-sdk/client-s3 + @aws-sdk/s3-request-presigner
- Upload strategy: Presigned URLs (client-direct) for large files, server proxy for small files
- Buckets: {project}-uploads-{env}, {project}-assets-{env}

## Storage Commands
- List buckets: aws s3 ls
- Sync local: aws s3 sync ./uploads s3://bucket-name/
- Create bucket: aws s3 mb s3://bucket-name

## Storage Conventions
- ALWAYS use presigned URLs for client-side uploads (never proxy large files through your server)
- Use structured key prefixes: users/{userId}/avatars/, documents/{docId}/
- Set appropriate Content-Type on upload
- Configure CORS on S3 bucket for direct browser uploads
- Use lifecycle policies to auto-delete temporary files
- Set bucket policies to block public access by default
- Use CloudFront/CDN for serving public assets

## Mistakes to Avoid
- NEVER store AWS credentials in client-side code
- NEVER make buckets publicly writable
- NEVER use sequential keys (use UUIDs or prefixed paths for performance)
- ALWAYS validate file type and size before generating presigned URLs
- ALWAYS set appropriate Content-Disposition for downloads
- NEVER store sensitive files without server-side encryption (SSE-S3 or SSE-KMS)
```

## Presigned URL Pattern (Upload)

```typescript
// Server: Generate presigned upload URL
import { S3Client, PutObjectCommand } from '@aws-sdk/client-s3'
import { getSignedUrl } from '@aws-sdk/s3-request-presigner'

async function getUploadUrl(key: string, contentType: string) {
  const command = new PutObjectCommand({
    Bucket: process.env.S3_BUCKET,
    Key: key,
    ContentType: contentType,
  })
  return getSignedUrl(s3Client, command, { expiresIn: 3600 })
}

// Client: Upload directly to S3
const response = await fetch(presignedUrl, {
  method: 'PUT',
  body: file,
  headers: { 'Content-Type': file.type },
})
```

## Presigned URL Pattern (Download)

```typescript
import { GetObjectCommand } from '@aws-sdk/client-s3'

async function getDownloadUrl(key: string, filename: string) {
  const command = new GetObjectCommand({
    Bucket: process.env.S3_BUCKET,
    Key: key,
    ResponseContentDisposition: `attachment; filename="${filename}"`,
  })
  return getSignedUrl(s3Client, command, { expiresIn: 3600 })
}
```

## S3-Compatible Alternatives

### Cloudflare R2
- No egress fees (major cost advantage over S3)
- S3-compatible API — swap endpoint URL and credentials
- Built-in CDN integration with Cloudflare
- `S3_ENDPOINT=https://<account-id>.r2.cloudflarestorage.com`

### MinIO (Self-hosted)
- Full S3 API compatibility
- Good for local development and on-prem deployments
- Docker: `docker run -p 9000:9000 -p 9001:9001 minio/minio server /data --console-address ":9001"`

### Supabase Storage
- Built on S3, managed by Supabase
- Integrates with Supabase Auth for RLS-like file access policies
- Simple API: `supabase.storage.from('bucket').upload(path, file)`

## Bucket Configuration

```json
{
  "CORSConfiguration": {
    "CORSRules": [{
      "AllowedOrigins": ["https://yourdomain.com"],
      "AllowedMethods": ["GET", "PUT", "POST"],
      "AllowedHeaders": ["*"],
      "MaxAgeSeconds": 3600
    }]
  }
}
```

## Environment Variables
```
S3_BUCKET=your-bucket-name
S3_REGION=us-east-1
S3_ACCESS_KEY_ID=...
S3_SECRET_ACCESS_KEY=...
S3_ENDPOINT=  # Only for R2/MinIO/custom endpoints
CDN_URL=https://cdn.yourdomain.com  # If using CloudFront/CDN
```
