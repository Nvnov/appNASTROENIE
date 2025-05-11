
import joblib
import os
import torch
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SentimentAnalyzer:
    def __init__(self):
        model_path = os.path.join("model", "model_and_tokenizer.pkl")
        encoder_path = os.path.join("model", "label_encoder_final.pkl")
        try:
            if not os.path.exists(model_path):
                raise FileNotFoundError(f"Модель не найдена: {model_path}")
            data = joblib.load(model_path)
            self.model = data["model"]
            self.tokenizer = data["tokenizer"]
            if not os.path.exists(encoder_path):
                raise FileNotFoundError(f"LabelEncoder не найден: {encoder_path}")
            self.label_encoder = joblib.load(encoder_path)
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            self.model.to(self.device)
            logger.info(f"Загружена модель: {type(self.model)}, токенизатор: {type(self.tokenizer)}, устройство: {self.device}")
        except Exception as e:
            logger.error(f"Ошибка загрузки модели: {e}")
            raise RuntimeError(f"Ошибка загрузки модели: {e}")

    def predict(self, text: str) -> str:
        try:
            self.model.eval()
            inputs = self.tokenizer(
                text,
                return_tensors="pt",
                padding=True,
                truncation=True,
                max_length=128
            )
            inputs = {k: v.to(self.device) for k, v in inputs.items()}
            with torch.no_grad():
                outputs = self.model(**inputs)
                logits = outputs.logits
                predicted_class_id = torch.argmax(logits, dim=1).item()
            return self.label_encoder.inverse_transform([predicted_class_id])[0]
        except Exception as e:
            logger.error(f"Ошибка предсказания: {e}")
            raise RuntimeError(f"Ошибка предсказания: {e}")
