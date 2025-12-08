# Guía de Despliegue - Brecha AI Service

## Configuración de GitHub Secrets

Para que el workflow de CI/CD funcione correctamente, necesitas configurar los siguientes secretos en tu repositorio de GitHub:

### Pasos para agregar secretos:

1. Ve a tu repositorio en GitHub
2. Haz clic en **Settings** → **Secrets and variables** → **Actions**
3. Haz clic en **New repository secret** y agrega cada uno:

### Secretos Requeridos:

#### 1. `GCP_SA_KEY` (Obligatorio)
- **Descripción**: Clave JSON de la cuenta de servicio de Google Cloud
- **Valor**: Contenido completo del archivo JSON de tu Service Account
- **Cómo obtenerlo**:
  ```bash
  gcloud iam service-accounts keys create key.json \
    --iam-account=github-ci-service@YOUR-PROJECT-ID.iam.gserviceaccount.com
  
  # Luego copia el contenido de key.json
  cat key.json
  ```

#### 2. `GEMINI_API_KEY` (Obligatorio)
- **Descripción**: Clave API de Google Gemini
- **Valor**: Tu clave API de Gemini
- **Nota**: También se debe crear como secreto en Google Cloud Secret Manager

#### 3. `GEMINI_MODEL_NAME` (Obligatorio)
- **Descripción**: Nombre del modelo Gemini a usar
- **Valor Típico**: `gemini-2.0-flash-exp`
- **Nota**: También se debe crear como secreto en Google Cloud Secret Manager

## Configuración en Google Cloud

### 1. Habilitar APIs Necesarias

```bash
export PROJECT_ID="p-brecha-251-219-11-cd"

# Habilitar Secret Manager API (IMPORTANTE)
gcloud services enable secretmanager.googleapis.com --project=$PROJECT_ID

# Habilitar Cloud Run API
gcloud services enable run.googleapis.com --project=$PROJECT_ID

# Habilitar Artifact Registry API
gcloud services enable artifactregistry.googleapis.com --project=$PROJECT_ID
```

### 2. Crear Secretos en Secret Manager

```bash
# Configurar variables de entorno
export PROJECT_ID="p-brecha-251-219-11-cd"
export REGION="us-central1"

# Crear secreto para GEMINI_API_KEY
echo -n "your-gemini-api-key-here" | gcloud secrets create GEMINI_API_KEY \
  --data-file=- \
  --project=$PROJECT_ID

# Crear secreto para GEMINI_MODEL_NAME
echo -n "gemini-2.0-flash-exp" | gcloud secrets create GEMINI_MODEL_NAME \
  --data-file=- \
  --project=$PROJECT_ID
```

### 2. Verificar que los secretos están creados

```bash
gcloud secrets list --project=$PROJECT_ID
```

### 3. Dar permisos a la Service Account

```bash
# Para GEMINI_API_KEY
gcloud secrets add-iam-policy-binding GEMINI_API_KEY \
  --member=serviceAccount:github-ci-service@p-brecha-251-219-11-cd.iam.gserviceaccount.com \
  --role=roles/secretmanager.secretAccessor \
  --project=$PROJECT_ID

# Para GEMINI_MODEL_NAME
gcloud secrets add-iam-policy-binding GEMINI_MODEL_NAME \
  --member=serviceAccount:github-ci-service@p-brecha-251-219-11-cd.iam.gserviceaccount.com \
  --role=roles/secretmanager.secretAccessor \
  --project=$PROJECT_ID
```

## Flujo de Despliegue

### Rama `main` → Production
- **Proyecto**: `p-brecha-251-219-11-cd`
- **Servicio**: `brecha-ai-service-py-prod`
- **Región**: `us-central1`
- **Ambiente**: `production`

### Rama `dev` → Development
- **Proyecto**: `d-brecha-251-219-11-CD`
- **Servicio**: `brecha-ai-service-py-dev`
- **Región**: `us-central1`
- **Ambiente**: `development`

## Verificación Local Antes de Desplegar

```bash
# 1. Construir la imagen Docker
docker build -t brecha-ai-service-py:latest .

# 2. Crear archivo .env para pruebas
cat > .env.test << EOF
ENVIRONMENT=development
PORT=8080
LOG_LEVEL=DEBUG
ALLOWED_ORIGINS=*
GEMINI_API_KEY=your-test-key
GEMINI_MODEL_NAME=gemini-2.0-flash-exp
GEMINI_MAX_RETRIES=3
GEMINI_RETRY_DELAY=2
EOF

# 3. Ejecutar el contenedor
docker run -d --rm -p 8080:8080 \
  --env-file .env.test \
  --name brecha-ai-test \
  brecha-ai-service-py:latest

# 4. Verificar health check
curl http://localhost:8080/health

# 5. Detener el contenedor
docker stop brecha-ai-test
```

## Solución de Problemas

### Error: "Secret Manager API has not been used in project"
- **Causa**: La API de Secret Manager no está habilitada
- **Solución**: Ejecuta:
  ```bash
  gcloud services enable secretmanager.googleapis.com --project=p-brecha-251-219-11-cd
  ```

### Error: "Setting IAM policy failed"
- **Causa**: La Service Account no tiene permisos para acceder a los secretos
- **Solución**: Ejecuta los comandos de permiso en la sección "Dar permisos a la Service Account"

### Error: "Context access might be invalid: GCP_SA_KEY"
- **Causa**: El secreto no está configurado en GitHub
- **Solución**: Agrega el secreto en GitHub → Settings → Secrets

## Variables de Entorno en Cloud Run

### Variables de Entorno (set-env-vars)
- `ENVIRONMENT`: production o development
- `LOG_LEVEL`: INFO o DEBUG
- `ALLOWED_ORIGINS`: *
- `GEMINI_MAX_RETRIES`: 3 o 5
- `GEMINI_RETRY_DELAY`: 2 o 3

### Secretos (set-secrets)
- `GEMINI_API_KEY`: De Secret Manager
- `GEMINI_MODEL_NAME`: De Secret Manager

**Nota**: `PORT` NO se incluye porque Cloud Run lo establece automáticamente en 8080.

## Monitoreo

### Ver logs del servicio
```bash
gcloud run services logs read brecha-ai-service-py-prod \
  --region us-central1 \
  --project p-brecha-251-219-11-cd
```

### Ver métrica de requests
```bash
gcloud monitoring read \
  --filter='metric.type="run.googleapis.com/request_count"' \
  --project p-brecha-251-219-11-cd
```

## Recursos Útiles

- [Google Cloud Run Documentation](https://cloud.google.com/run/docs)
- [GitHub Actions - Google Cloud Auth](https://github.com/google-github-actions/auth)
- [Google Cloud Secret Manager](https://cloud.google.com/secret-manager/docs)
- [Brecha AI Service README](./README.md)
