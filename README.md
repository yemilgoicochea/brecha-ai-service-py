# Brecha AI Service

A professional FastAPI-based REST API for classifying public infrastructure project titles using Google's Gemini AI. This service is designed for the SNPMGI (Sistema Nacional de Programación Multianual y Gestión de Inversiones) of Peru.

## 🚀 Features

- **FastAPI Framework**: Modern, fast, and async-ready REST API
- **Gemini AI Integration**: Leverages Google's Gemini models for intelligent classification
- **Multi-label Classification**: Assigns one or more service categories to project titles
- **Production Ready**: 
  - Docker containerization
  - Cloud Run compatible
  - Health checks and logging
  - Environment-based configuration
- **CI/CD Pipeline**: Automated testing and deployment with GitHub Actions
- **Clean Architecture**: Scalable project structure with separation of concerns

## 📋 Prerequisites

- Python 3.11+
- Docker (for containerization)
- Google Cloud account (for deployment)
- Gemini API key

## 🛠️ Installation

### Local Development

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd brecha-ai-service-py
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   
   # Windows
   .\venv\Scripts\activate
   
   # Linux/Mac
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**
   ```bash
   cp .env.example .env
   ```
   
   Edit `.env` and add your Gemini credentials:
   ```env
   GEMINI_API_KEY=your-actual-api-key-here
   GEMINI_MODEL_NAME=gemini-2.0-flash-exp
   ```

5. **Run the application**
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8080
   ```

6. **Access the API**
   - API: http://localhost:8080
   - Swagger docs: http://localhost:8080/docs
   - ReDoc: http://localhost:8080/redoc

## 🐳 Docker

### Build and Run Locally

```bash
# Build the image
docker build -t brecha-ai-service-py:latest .

# Run the container
docker run -d --rm -p 8080:8080 \
  --env-file .env \
  --name brecha-ai-service-test \
  brecha-ai-service-py:latest

# Check health
curl http://localhost:8080/health

# View logs
docker logs brecha-ai-service-test

# Stop the container
docker stop brecha-ai-service-test
```

### Docker Compose (Optional)

Create a `docker-compose.yml`:

```yaml
version: '3.8'
services:
  api:
    build: .
    ports:
      - "8080:8080"
    env_file: .env
    environment:
      - ENVIRONMENT=production
    restart: unless-stopped
```

Run with:
```bash
docker-compose up -d
```

## 📡 API Endpoints

### Classification

**POST** `/api/v1/classify`

Classify a project title into service categories.

**Request:**
```json
{
  "title": "Mejoramiento del servicio de agua potable en el distrito de San Juan"
}
```

**Response:**
```json
{
  "labels": [
    {
      "label": "servicio de agua potable mediante red publica o pileta publica",
      "confianza": 0.95,
      "justificacion": "El título menciona explícitamente 'servicio de agua potable', que corresponde directamente a esta categoría."
    }
  ]
}
```

### Categories

**GET** `/api/v1/categories`

List all available classification categories.

**Response:**
```json
{
  "categories": {
    "SERVICIO DE EDUCACIÓN SECUNDARIA": "...",
    "servicio de agua potable mediante red publica o pileta publica": "..."
  },
  "total": 8
}
```

### Health Check

**GET** `/health`

Health check endpoint for monitoring.

**Response:**
```json
{
  "status": "healthy",
  "service": "Brecha AI Service"
}
```

## 🏗️ Project Structure

```
brecha-ai-service-py/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI application
│   ├── api/
│   │   ├── __init__.py
│   │   └── routers/
│   │       ├── __init__.py
│   │       └── classifier.py   # Classification endpoints
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py           # Configuration settings
│   │   └── logging_config.py   # Logging setup
│   ├── models/
│   │   ├── __init__.py
│   │   ├── categories.py       # Category definitions
│   │   └── schemas.py          # Pydantic models
│   └── services/
│       ├── __init__.py
│       └── classifier_service.py # Gemini integration
├── tests/
│   ├── conftest.py
│   └── test_api.py
├── .github/
│   └── workflows/
│       ├── tests.yml           # CI tests
│       └── build-and-deploy.yml # CD to Cloud Run
├── .dockerignore
├── .env.example
├── .gitignore
├── Dockerfile
├── README.md
└── requirements.txt
```

## ☁️ Cloud Run Deployment

### Prerequisites

1. **Create a Google Cloud project**
2. **Enable required APIs:**
   ```bash
   gcloud services enable run.googleapis.com
   gcloud services enable artifactregistry.googleapis.com
   ```

3. **Create Artifact Registry repository:**
   ```bash
   gcloud artifacts repositories create brecha-ai-repo \
     --repository-format=docker \
     --location=us-central1 \
     --description="Brecha AI Service Docker repository"
   ```

4. **Store Gemini credentials in Secret Manager:**
   ```bash
   echo -n "your-gemini-api-key" | gcloud secrets create GEMINI_API_KEY --data-file=-
   echo -n "gemini-2.0-flash-exp" | gcloud secrets create GEMINI_MODEL_NAME --data-file=-
   ```

### Manual Deployment

```bash
# Set variables
export PROJECT_ID=your-gcp-project-id
export REGION=us-central1
export SERVICE_NAME=brecha-ai-service-py-prod

# Build and push image
gcloud builds submit --tag $REGION-docker.pkg.dev/$PROJECT_ID/cloud-run-repo/brecha-ai-service-py

# Deploy to Cloud Run
gcloud run deploy $SERVICE_NAME \
  --image $REGION-docker.pkg.dev/$PROJECT_ID/cloud-run-repo/brecha-ai-service-py \
  --platform managed \
  --region $REGION \
  --allow-unauthenticated \
  --set-env-vars "ENVIRONMENT=production,PORT=8080,LOG_LEVEL=INFO,ALLOWED_ORIGINS=*" \
  --set-secrets "GEMINI_API_KEY=GEMINI_API_KEY:latest,GEMINI_MODEL_NAME=GEMINI_MODEL_NAME:latest" \
  --memory 512Mi \
  --cpu 1 \
  --port 8080
```

### Automated Deployment with GitHub Actions

1. **Set up GitHub Secrets:**
   - `GCP_PROJECT_ID`: Your Google Cloud project ID
   - `GCP_SA_KEY`: Service account JSON key with permissions:
     - Cloud Run Admin
     - Artifact Registry Writer
     - Service Account User
     - Secret Manager Secret Accessor

2. **Create service account:**
   ```bash
   gcloud iam service-accounts create github-actions \
     --display-name="GitHub Actions"

   gcloud projects add-iam-policy-binding $PROJECT_ID \
     --member="serviceAccount:github-actions@$PROJECT_ID.iam.gserviceaccount.com" \
     --role="roles/run.admin"

   gcloud projects add-iam-policy-binding $PROJECT_ID \
     --member="serviceAccount:github-actions@$PROJECT_ID.iam.gserviceaccount.com" \
     --role="roles/artifactregistry.writer"

   gcloud iam service-accounts keys create key.json \
     --iam-account=github-actions@$PROJECT_ID.iam.gserviceaccount.com
   ```

3. **Add key.json content to GitHub Secrets as GCP_SA_KEY**

4. **Push to main branch** to trigger automatic deployment

## 🧪 Testing

Run tests locally:

```bash
# Install test dependencies
pip install pytest pytest-asyncio pytest-cov httpx

# Run tests
pytest tests/ -v

# Run with coverage
pytest tests/ -v --cov=app --cov-report=term-missing
```

## 📝 Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `ENVIRONMENT` | Environment (development/production) | `development` | No |
| `PORT` | Server port | `8080` | No |
| `LOG_LEVEL` | Logging level | `INFO` | No |
| `ALLOWED_ORIGINS` | CORS allowed origins | `*` | No |
| `GEMINI_API_KEY` | Google Gemini API key | - | **Yes** |
| `GEMINI_MODEL_NAME` | Gemini model to use | - | **Yes** |
| `GEMINI_MAX_RETRIES` | Max retry attempts | `3` | No |
| `GEMINI_RETRY_DELAY` | Retry delay (seconds) | `2` | No |

## 🔧 Development

### Code Formatting

```bash
# Format with black
black app/

# Sort imports
isort app/

# Lint with flake8
flake8 app/

# Type check with mypy
mypy app/
```

### Adding New Categories

1. Edit `app/models/categories.py`
2. Add new category to `DEFINICIONES_DE_CATEGORIAS` dictionary
3. Restart the service

## 📊 Monitoring

### Cloud Run Metrics

Access metrics in Google Cloud Console:
- Request count
- Request latency
- Error rate
- Container instances

### Logs

View logs:
```bash
gcloud run services logs read brecha-ai-service --region us-central1
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is proprietary software for SNPMGI Peru.

## 👥 Support

For issues and questions:
- Create an issue in the repository
- Contact the development team

## 🔄 Version History

- **1.0.0** (2024-12-07)
  - Initial release
  - Gemini 2.0 Flash integration
  - 8 classification categories
  - Cloud Run deployment support
  - CI/CD pipeline with GitHub Actions
