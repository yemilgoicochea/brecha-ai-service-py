"""Classifier service using Gemini API."""

import json
import logging
import time
from typing import Any, Dict

import google.generativeai as genai

from app.core.config import settings
from app.models.categories import DEFINICIONES_DE_CATEGORIAS

logger = logging.getLogger(__name__)


class ClassifierService:
    """Service for classifying project titles using Gemini AI."""

    def __init__(self):
        """Initialize the classifier service."""
        try:
            genai.configure(api_key=settings.GEMINI_API_KEY)
            self.model = genai.GenerativeModel(settings.GEMINI_MODEL_NAME)
            logger.info(f"Gemini API configured with model: {settings.GEMINI_MODEL_NAME}")
        except Exception as e:
            logger.error(f"Failed to configure Gemini API: {str(e)}")
            raise

    def get_categories(self) -> Dict[str, str]:
        """
        Get all available classification categories.

        Returns:
            Dictionary of category names and definitions
        """
        return DEFINICIONES_DE_CATEGORIAS.copy()

    def _build_prompt(self, project_title: str) -> str:
        """
        Build the classification prompt for Gemini.

        Args:
            project_title: The project title to classify

        Returns:
            Formatted prompt string
        """
        project_title = str(project_title).strip()

        category_text_parts = []
        for name, category_info in DEFINICIONES_DE_CATEGORIAS.items():
            category_id = category_info["id"]
            definition = category_info["definicion"]
            category_text_parts.append(
                f"- ID: {category_id}\n"
                f"  NOMBRE: {name}\n"
                f"  DEFINICION: {definition.strip()}\n"
            )
        categories_text = "\n".join(category_text_parts)

        prompt = f"""
Eres un modelo de lenguaje experto en clasificación de títulos de proyectos públicos
según brechas de infraestructura y servicios definidas por el SNPMGI del Perú.

Tu única tarea es leer el título del proyecto y asignarle UNA O VARIAS categorías
de servicios publicos de la lista definida abajo.

CATEGORÍAS DISPONIBLES:
{categories_text}

REGLAS ESTRICTAS:
- Analiza el significado del título del proyecto, no solo palabras sueltas.
- Asigna múltiples categorías solo si el título realmente cubre más de una brecha.
- No inventes información adicional que no esté presente o inferida razonablemente del título del proyecto.

FORMATO DE RESPUESTA (OBLIGATORIO):
Responde ÚNICAMENTE con JSON válido, sin texto adicional, sin explicaciones, sin backticks.
Ejemplo de formato:

{{
  "labels": [
    {{
      "label": "NOMBRE_DE_CATEGORIA_1",
      "id": 1,
      "confianza": 0.95,
      "justificacion": "Texto de la justificación"
    }},
    {{
      "label": "NOMBRE_DE_CATEGORIA_2",
      "id": 3,
      "confianza": 0.98,
      "justificacion": "Texto de la justificación"
    }}
  ]
}}

donde:
- "labels" es una lista de objetos.
- "label" es el nombre de la categoría seleccionada.
-"id": es el identificador numérico único asignado a cada categoría. Debes devolver exactamente el id asociado a la categoría, según la lista de categorías proporcionada en el prompt.
- "confianza": representa el nivel de certeza del modelo sobre la asignación de una categoría. Debe ser un valor numérico entre 0 y 1, donde:
1.0 indica certeza máxima basada en una alta coincidencia semántica con la definición de la categoría,
0.7 a 0.9 indica coincidencia fuerte pero no absoluta,
0.4 a 0.6 indica coincidencia débil o parcialmente relacionada,
< 0.4 indica baja certeza; la categoría probablemente no aplica.
- "justificacion": explica por qué el proyecto fue clasificado en esa categoria usando unicamente la DEFINICIÓN de la categoria. máximo 200 palabras.

Si el título del proyecto es ambiguo o no coincide con ninguna definición, debes devolver:

{{
  "labels": [
    {{
      "label": "NO_CLASIFICADO",
      "id": 0,
      "confianza": 0.0,
      "justificacion": "El texto no es suficiente o no coincide con ninguna categoría."
    }}
  ]
}}

TEXTO A CLASIFICAR:
\"\"\"{project_title}\"\"\"
"""
        return prompt

    def _extract_json_from_response(self, text: str) -> str:
        """
        Extract and clean JSON from model response.

        Args:
            text: Raw response text from the model

        Returns:
            Clean JSON string

        Raises:
            json.JSONDecodeError: If response is not valid JSON
        """
        if text is None:
            raise json.JSONDecodeError("Empty response from model", "", 0)

        s = text.strip()

        # Remove markdown code blocks if present
        if s.startswith("```"):
            first_newline = s.find("\n")
            if first_newline != -1:
                s = s[first_newline + 1 :]
            if s.endswith("```"):
                s = s[:-3]
            s = s.strip()

        # Extract content between first '{' and last '}'
        start = s.find("{")
        end = s.rfind("}")
        if start != -1 and end != -1 and end > start:
            s = s[start : end + 1]

        # Parse and validate JSON
        obj = json.loads(s)
        return json.dumps(obj, ensure_ascii=False)

    async def classify(self, project_title: str) -> Dict[str, Any]:
        """
        Classify a project title.

        Args:
            project_title: The project title to classify

        Returns:
            Classification result as dictionary

        Raises:
            ValueError: If project title is empty
            Exception: If classification fails after retries
        """
        if not project_title or not project_title.strip():
            raise ValueError("Project title cannot be empty")

        prompt = self._build_prompt(project_title)

        for attempt in range(1, settings.GEMINI_MAX_RETRIES + 1):
            try:
                logger.info(f"Classification attempt {attempt}/{settings.GEMINI_MAX_RETRIES}")

                response = self.model.generate_content(prompt)
                text = (response.text or "").strip()

                try:
                    json_clean = self._extract_json_from_response(text)
                    result = json.loads(json_clean)

                    logger.info(f"Classification successful on attempt {attempt}")
                    return result

                except json.JSONDecodeError as e:
                    logger.warning(f"Invalid JSON response on attempt {attempt}: {str(e)}")
                    return {
                        "labels": [],
                        "error": "La respuesta del modelo no es JSON válido",
                        "detalle_error": str(e),
                        "raw_response": text,
                    }

            except Exception as e:
                logger.error(f"Attempt {attempt} failed: {str(e)}")
                if attempt < settings.GEMINI_MAX_RETRIES:
                    time.sleep(settings.GEMINI_RETRY_DELAY)
                else:
                    return {
                        "labels": [],
                        "error": "No se pudo obtener respuesta del modelo luego de varios intentos.",
                        "detalle_error": str(e),
                    }

        return {
            "labels": [],
            "error": "Classification failed after all retries",
        }
