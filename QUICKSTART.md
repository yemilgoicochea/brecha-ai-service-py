# Brecha AI Service - Quick Start Guide

## Development Setup

### 1. Environment Setup
```bash
# Create virtual environment
python -m venv venv
.\venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env and add your GEMINI_API_KEY
```

### 2. Run Locally
```bash
# Development mode with auto-reload
uvicorn app.main:app --reload --port 8080

# Access the API
# http://localhost:8080/docs
```

### 3. Test the API
```bash
# Using curl (PowerShell)
$headers = @{"Content-Type"="application/json"}
$body = @{title="Mejoramiento del servicio de agua potable"} | ConvertTo-Json
Invoke-RestMethod -Uri "http://localhost:8080/api/v1/classify" -Method Post -Headers $headers -Body $body

# Or using Python
python -c "import requests; print(requests.post('http://localhost:8080/api/v1/classify', json={'title': 'Mejoramiento del servicio de agua potable'}).json())"
```

## Docker

### Build and Run
```bash
docker build -t brecha-ai-service .
docker run -p 8080:8080 -e GEMINI_API_KEY=your-key brecha-ai-service
```

## Testing

```bash
# Run all tests
pytest tests/ -v

# With coverage
pytest tests/ -v --cov=app
```

## Cloud Run Deployment

### Quick Deploy
```bash
# Set your project
gcloud config set project YOUR_PROJECT_ID

# Deploy
gcloud run deploy brecha-ai-service \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --set-secrets GEMINI_API_KEY=GEMINI_API_KEY:latest
```

### GitHub Actions (Automated)
1. Set GitHub secrets: `GCP_PROJECT_ID`, `GCP_SA_KEY`, `GEMINI_API_KEY`
2. Push to `main` branch
3. Automatic deployment to Cloud Run

## API Examples

### Classify a Project
```bash
POST /api/v1/classify
{
  "title": "Construcción de pistas y veredas en el distrito de Lima"
}
```

### Get Categories
```bash
GET /api/v1/categories
```

### Health Check
```bash
GET /health
```

## Troubleshooting

### API Key Issues
- Verify `GEMINI_API_KEY` is set in `.env`
- Check the key is valid in Google AI Studio

### Port Already in Use
```bash
# Change port
uvicorn app.main:app --port 8000
```

### Docker Build Fails
```bash
# Clear cache and rebuild
docker build --no-cache -t brecha-ai-service .
```

## Next Steps

1. Review the full [README.md](README.md) for detailed documentation
2. Explore the API at http://localhost:8080/docs
3. Customize categories in `app/models/categories.py`
4. Set up CI/CD with GitHub Actions
