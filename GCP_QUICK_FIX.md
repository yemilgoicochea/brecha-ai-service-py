# Fix Rápido - Errores de Despliegue

## Problema: Secret Manager API no habilitada

```bash
# Ejecuta esto en tu terminal
gcloud services enable secretmanager.googleapis.com --project=p-brecha-251-219-11-cd
gcloud services enable run.googleapis.com --project=p-brecha-251-219-11-cd
gcloud services enable artifactregistry.googleapis.com --project=p-brecha-251-219-11-cd
```

## Problema: Service Account sin permisos

```bash
PROJECT_ID="p-brecha-251-219-11-cd"
SERVICE_ACCOUNT="github-ci-service@${PROJECT_ID}.iam.gserviceaccount.com"

# Dar permisos para acceder a GEMINI_API_KEY
gcloud secrets add-iam-policy-binding GEMINI_API_KEY \
  --member=serviceAccount:$SERVICE_ACCOUNT \
  --role=roles/secretmanager.secretAccessor \
  --project=$PROJECT_ID

# Dar permisos para acceder a GEMINI_MODEL_NAME
gcloud secrets add-iam-policy-binding GEMINI_MODEL_NAME \
  --member=serviceAccount:$SERVICE_ACCOUNT \
  --role=roles/secretmanager.secretAccessor \
  --project=$PROJECT_ID
```

## Problema: Secretos no existen

```bash
PROJECT_ID="p-brecha-251-219-11-cd"

# Crear GEMINI_API_KEY
echo -n "YOUR_GEMINI_API_KEY_HERE" | gcloud secrets create GEMINI_API_KEY \
  --data-file=- \
  --project=$PROJECT_ID \
  --replication-policy="automatic"

# Crear GEMINI_MODEL_NAME
echo -n "gemini-2.0-flash-exp" | gcloud secrets create GEMINI_MODEL_NAME \
  --data-file=- \
  --project=$PROJECT_ID \
  --replication-policy="automatic"
```

## Verificar que todo está configurado

```bash
# Listar secretos
gcloud secrets list --project=p-brecha-251-219-11-cd

# Verificar permisos
gcloud secrets get-iam-policy GEMINI_API_KEY --project=p-brecha-251-219-11-cd
gcloud secrets get-iam-policy GEMINI_MODEL_NAME --project=p-brecha-251-219-11-cd

# Verificar APIs habilitadas
gcloud services list --enabled --project=p-brecha-251-219-11-cd | grep -E "secretmanager|run|artifactregistry"
```

## Paso a Paso Recomendado

1. Ejecuta los comandos de habilitación de APIs
2. Espera 1-2 minutos
3. Crea los secretos
4. Da los permisos a la Service Account
5. Haz un nuevo push a GitHub para disparar el workflow

¡Eso debería resolver todos los problemas! 🚀
