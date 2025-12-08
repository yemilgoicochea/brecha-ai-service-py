# Deployment Guide - Brecha AI Service

## Table of Contents
1. [GitHub Secrets Configuration](#github-secrets-configuration)
2. [Google Cloud Setup](#google-cloud-setup)
3. [Deployment Flow](#deployment-flow)
4. [Local Testing](#local-testing)
5. [Troubleshooting](#troubleshooting)

---

## GitHub Secrets Configuration

To make the CI/CD workflow function correctly, configure the following secret in your GitHub repository:

### Steps to add secret:

1. Go to your GitHub repository
2. Click **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret**
4. Add `GCP_SA_KEY` with the full JSON contents of your Service Account key

---

## Google Cloud Setup

### 1. Enable Required APIs

```bash
export PROJECT_ID="p-brecha-251-219-11-cd"

# Enable Secret Manager API (IMPORTANT - required for secrets)
gcloud services enable secretmanager.googleapis.com --project=$PROJECT_ID

# Enable Cloud Run API
gcloud services enable run.googleapis.com --project=$PROJECT_ID

# Enable Artifact Registry API
gcloud services enable artifactregistry.googleapis.com --project=$PROJECT_ID
```

### 2. Create Secrets in Secret Manager

```bash
PROJECT_ID="p-brecha-251-219-11-cd"

# Create GEMINI_API_KEY secret
echo -n "your-gemini-api-key-here" | gcloud secrets create GEMINI_API_KEY \
  --data-file=- \
  --project=$PROJECT_ID \
  --replication-policy="automatic"

# Create GEMINI_MODEL_NAME secret
echo -n "gemini-2.0-flash-exp" | gcloud secrets create GEMINI_MODEL_NAME \
  --data-file=- \
  --project=$PROJECT_ID \
  --replication-policy="automatic"
```

### 3. Grant Permissions to Service Account

```bash
PROJECT_ID="p-brecha-251-219-11-cd"
SERVICE_ACCOUNT="github-ci-service@${PROJECT_ID}.iam.gserviceaccount.com"

# Grant Secret Manager Secret Accessor role for GEMINI_API_KEY
gcloud secrets add-iam-policy-binding GEMINI_API_KEY \
  --member=serviceAccount:$SERVICE_ACCOUNT \
  --role=roles/secretmanager.secretAccessor \
  --project=$PROJECT_ID

# Grant Secret Manager Secret Accessor role for GEMINI_MODEL_NAME
gcloud secrets add-iam-policy-binding GEMINI_MODEL_NAME \
  --member=serviceAccount:$SERVICE_ACCOUNT \
  --role=roles/secretmanager.secretAccessor \
  --project=$PROJECT_ID
```

### 4. Verify Configuration

```bash
# List all secrets
gcloud secrets list --project=$PROJECT_ID

# Verify permissions
gcloud secrets get-iam-policy GEMINI_API_KEY --project=$PROJECT_ID
gcloud secrets get-iam-policy GEMINI_MODEL_NAME --project=$PROJECT_ID
```

---

## Deployment Flow

### Branch-based Strategy

| Branch | Environment | Project | Service Name |
|--------|-------------|---------|--------------|
| `main` | production | `p-brecha-251-219-11-cd` | `brecha-ai-service-py-prod` |
| `dev` | development | `d-brecha-251-219-11-CD` | `brecha-ai-service-py-dev` |

### Automatic Deployment Steps

When you push to `main` or `dev`, GitHub Actions:

1. **Builds** Docker image and tags with commit SHA
2. **Pushes** to Artifact Registry
3. **Deploys** to Cloud Run with:
   - Environment variables (ENVIRONMENT, LOG_LEVEL, etc.)
   - Secrets from Secret Manager (GEMINI_API_KEY, GEMINI_MODEL_NAME)
4. **Verifies** deployment with health check

### Environment Variables in Cloud Run

**Public Variables (set-env-vars):**
- ENVIRONMENT: production or development
- LOG_LEVEL: INFO or DEBUG
- ALLOWED_ORIGINS: *
- GEMINI_MAX_RETRIES: 5 (prod) or 3 (dev)
- GEMINI_RETRY_DELAY: 3 (prod) or 2 (dev)

**Secret Variables (set-secrets):**
- GEMINI_API_KEY: From Secret Manager
- GEMINI_MODEL_NAME: From Secret Manager

**Note**: PORT is automatically set to 8080 by Cloud Run

### Configure Public Access (Manual - Security Best Practice)

After first deployment, configure public access manually via Google Cloud Console or gcloud:

**Option 1: Google Cloud Console**
1. Go to [Cloud Run Console](https://console.cloud.google.com/run)
2. Select your service (e.g., `brecha-ai-service-py-prod`)
3. Click **Security** tab
4. Under **Authentication**, select **Allow unauthenticated invocations**
5. Click **Save**

**Option 2: gcloud Command**
```bash
# For Production
gcloud run services add-iam-policy-binding brecha-ai-service-py-prod \
  --region=us-central1 \
  --member="allUsers" \
  --role="roles/run.invoker" \
  --project=p-brecha-251-219-11-cd

# For Development
gcloud run services add-iam-policy-binding brecha-ai-service-py-dev \
  --region=us-central1 \
  --member="allUsers" \
  --role="roles/run.invoker" \
  --project=d-brecha-251-219-11-CD
```

**Note**: This is done manually for security reasons, requiring explicit authorization for public access.

---

## Local Testing

### Build and Run Docker Image

```bash
# Build the image
docker build -t brecha-ai-service-py:latest .

# Run the container
docker run -d --rm -p 8080:8080 \
  --env-file .env \
  --name brecha-ai-test \
  brecha-ai-service-py:latest

# Test the health check
curl http://localhost:8080/health

# View logs
docker logs brecha-ai-test

# Stop the container
docker stop brecha-ai-test
```

---

## Troubleshooting

### Error: "Secret Manager API has not been used in project"
- **Cause**: Secret Manager API is not enabled
- **Solution**: Run the "Enable Required APIs" commands above
- **Note**: Wait 1-2 minutes for propagation after enabling

### Error: "Permission denied on secret"
- **Cause**: Service account doesn't have access to the secret
- **Solution**: Run the "Grant Permissions" commands above
- **Note**: Wait 1-2 minutes for permissions to propagate

### Error: "Context access might be invalid: GCP_SA_KEY"
- **Cause**: The GitHub secret is not configured
- **Solution**: Add `GCP_SA_KEY` to GitHub Settings → Secrets and variables → Actions

### Check Service Status

```bash
# Describe the service
gcloud run services describe brecha-ai-service-py-prod \
  --region us-central1 \
  --project p-brecha-251-219-11-cd

# View recent logs
gcloud run services logs read brecha-ai-service-py-prod \
  --region us-central1 \
  --project p-brecha-251-219-11-cd \
  --limit 50

# Test the service URL
SERVICE_URL=$(gcloud run services describe brecha-ai-service-py-prod \
  --region us-central1 \
  --project p-brecha-251-219-11-cd \
  --format 'value(status.url)')

curl -f $SERVICE_URL/health
```

---

## Resources

- [Google Cloud Run Documentation](https://cloud.google.com/run/docs)
- [GitHub Actions - Google Cloud Auth](https://github.com/google-github-actions/auth)
- [Google Cloud Secret Manager](https://cloud.google.com/secret-manager/docs)
- [Brecha AI Service README](./README.md)
