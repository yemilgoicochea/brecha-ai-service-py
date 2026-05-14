"""Google Cloud Pub/Sub service for publishing messages."""

import json
import logging
from typing import Any, Dict

from google.cloud import pubsub_v1

from app.core.config import settings

logger = logging.getLogger(__name__)


class PubSubPublisher:
    """Service for publishing messages to Google Cloud Pub/Sub."""

    def __init__(self):
        """Initialize the Pub/Sub publisher."""
        try:
            self.project_id = settings.GCP_PROJECT_ID
            self.topic_id = settings.PUBSUB_TOPIC_ID
            self.publisher = pubsub_v1.PublisherClient()
            self.topic_path = self.publisher.topic_path(self.project_id, self.topic_id)

            logger.info(
                f"Pub/Sub publisher initialized. "
                f"Project: {self.project_id}, Topic: {self.topic_id}"
            )
        except Exception as e:
            logger.warning(f"Pub/Sub not fully configured: {str(e)}")
            self.publisher = None
            self.topic_path = None

    def publish_classification_request(self, message: Dict[str, Any]) -> str:
        """
        Publish a classification request to Pub/Sub.

        Args:
            message: Message data containing query details

        Returns:
            Message ID
        """
        if not self.publisher or not self.topic_path:
            logger.warning("Pub/Sub publisher not initialized")
            raise RuntimeError("Pub/Sub publisher not configured")

        try:
            message_json = json.dumps(message)
            future = self.publisher.publish(
                self.topic_path,
                message_json.encode("utf-8"),
            )
            message_id = future.result()

            logger.info(f"Published classification request: {message_id}")
            return message_id

        except Exception as e:
            logger.error(f"Failed to publish message: {str(e)}")
            raise
