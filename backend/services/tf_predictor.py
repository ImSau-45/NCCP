import logging

import numpy as np

logger = logging.getLogger(__name__)


class TFPredictor:
    def __init__(self):
        self.model = None
        self.tf = None
        self.init_error = None
        try:
            import tensorflow as tf

            self.tf = tf
            self.model = self.build_model()
        except Exception as exc:
            self.init_error = exc
            logger.warning("TensorFlow is unavailable; using fallback predictor: %s", exc)

    def build_model(self):
        if self.tf is None:
            raise RuntimeError("TensorFlow is not available")

        model = self.tf.keras.Sequential(
            [
                self.tf.keras.layers.InputLayer(input_shape=(3,)),
                self.tf.keras.layers.Dense(16, activation="relu"),
                self.tf.keras.layers.Dense(8, activation="relu"),
                self.tf.keras.layers.Dense(1, activation="sigmoid"),
            ]
        )
        model.compile(optimizer="adam", loss="binary_crossentropy", metrics=["accuracy"])
        return model

    def predict_failure_risk(self, features: dict):
        if self.model is None:
            recent_failures = max(features.get("recent_failures", 0), 0)
            success_rate = max(min(features.get("success_rate", 0.0), 1.0), 0.0)
            fallback_risk = min(0.95, 0.2 + (recent_failures * 0.08) + ((1 - success_rate) * 0.4))
            return {"failure_risk": round(fallback_risk * 100, 1), "mode": "fallback"}

        vector = np.array(
            [[features.get("recent_failures", 0), features.get("success_rate", 0.0) * 100, features.get("pipeline_length", 5)]],
            dtype=float,
        )
        risk = float(self.model.predict(vector, verbose=0)[0][0]) if hasattr(self.model, "predict") else 0.25
        return {"failure_risk": round(risk * 100, 1)}

    def train(self, dataset):
        if self.model is None:
            raise RuntimeError("TensorFlow model is not available")

        x = np.array([item["features"] for item in dataset])
        y = np.array([item["label"] for item in dataset])
        self.model.fit(x, y, epochs=5, batch_size=8)
        return True
