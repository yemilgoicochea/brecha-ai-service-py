#!/bin/bash

# Script para configurar Google Cloud para Brecha AI Service

# Variables
PROJECT_ID="p-brecha-251-219-11-cd"
REGION="us-central1"
SERVICE_ACCOUNT="github-ci-service@${PROJECT_ID}.iam.gserviceaccount.com"

echo "🚀 Configurando Google Cloud para Brecha AI Service"
echo "=================================================="
echo "Proyecto: $PROJECT_ID"
echo "Región: $REGION"
echo ""

# 1. Habilitar Secret Manager API
echo "1️⃣  Habilitando Secret Manager API..."
gcloud services enable secretmanager.googleapis.com --project=$PROJECT_ID
if [ $? -eq 0 ]; then
  echo "✅ Secret Manager API habilitada"
else
  echo "❌ Error al habilitar Secret Manager API"
  exit 1
fi

echo ""

# 2. Crear secretos en Secret Manager
echo "2️⃣  Creando secretos en Secret Manager..."

# GEMINI_API_KEY
echo "   Creando GEMINI_API_KEY..."
gcloud secrets create GEMINI_API_KEY \
  --replication-policy="automatic" \
  --project=$PROJECT_ID 2>/dev/null || echo "   ℹ️  GEMINI_API_KEY ya existe"

# GEMINI_MODEL_NAME
echo "   Creando GEMINI_MODEL_NAME..."
gcloud secrets create GEMINI_MODEL_NAME \
  --replication-policy="automatic" \
  --project=$PROJECT_ID 2>/dev/null || echo "   ℹ️  GEMINI_MODEL_NAME ya existe"

echo "✅ Secretos creados (o ya existen)"

echo ""

# 3. Dar permisos a la Service Account
echo "3️⃣  Configurando permisos de IAM..."

# Secret Accessor para GEMINI_API_KEY
echo "   Configurando permisos para GEMINI_API_KEY..."
gcloud secrets add-iam-policy-binding GEMINI_API_KEY \
  --member=serviceAccount:$SERVICE_ACCOUNT \
  --role=roles/secretmanager.secretAccessor \
  --project=$PROJECT_ID \
  --condition=None 2>/dev/null

# Secret Accessor para GEMINI_MODEL_NAME
echo "   Configurando permisos para GEMINI_MODEL_NAME..."
gcloud secrets add-iam-policy-binding GEMINI_MODEL_NAME \
  --member=serviceAccount:$SERVICE_ACCOUNT \
  --role=roles/secretmanager.secretAccessor \
  --project=$PROJECT_ID \
  --condition=None 2>/dev/null

echo "✅ Permisos de IAM configurados"

echo ""

# 4. Actualizar valores de secretos
echo "4️⃣  Actualizando valores de secretos..."

read -p "Ingresa tu GEMINI_API_KEY: " GEMINI_API_KEY
echo -n "$GEMINI_API_KEY" | gcloud secrets versions add GEMINI_API_KEY \
  --data-file=- \
  --project=$PROJECT_ID

read -p "Ingresa el GEMINI_MODEL_NAME (default: gemini-2.0-flash-exp): " GEMINI_MODEL_NAME
GEMINI_MODEL_NAME=${GEMINI_MODEL_NAME:-gemini-2.0-flash-exp}
echo -n "$GEMINI_MODEL_NAME" | gcloud secrets versions add GEMINI_MODEL_NAME \
  --data-file=- \
  --project=$PROJECT_ID

echo "✅ Valores de secretos actualizados"

echo ""

# 5. Habilitar Cloud Run API
echo "5️⃣  Habilitando Cloud Run API..."
gcloud services enable run.googleapis.com --project=$PROJECT_ID
echo "✅ Cloud Run API habilitada"

echo ""

# 6. Habilitar Artifact Registry API
echo "6️⃣  Habilitando Artifact Registry API..."
gcloud services enable artifactregistry.googleapis.com --project=$PROJECT_ID
echo "✅ Artifact Registry API habilitada"

echo ""

# 7. Resumen
echo "🎉 Configuración completada!"
echo "=================================================="
echo ""
echo "Próximos pasos:"
echo "1. Asegúrate de que los secretos GEMINI_API_KEY y GEMINI_MODEL_NAME"
echo "   están configurados en GitHub Secrets con GCP_SA_KEY"
echo "2. Intenta hacer push nuevamente al repositorio"
echo "3. El workflow de GitHub Actions debería ejecutarse automáticamente"
echo ""
echo "Para verificar que todo está configurado:"
echo "  gcloud secrets list --project=$PROJECT_ID"
echo ""
