
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QTextEdit, QPushButton
from logic.sentiment_model import SentimentAnalyzer

class TextAnalysisWidget(QWidget):
    def __init__(self):
        super().__init__()

        self.analyzer = SentimentAnalyzer()

        layout = QVBoxLayout()

        self.text_input = QTextEdit()
        self.text_input.setPlaceholderText("Введите текст для анализа...")
        layout.addWidget(self.text_input)

        self.analyze_button = QPushButton("Анализировать")
        self.analyze_button.clicked.connect(self.analyze_text)
        layout.addWidget(self.analyze_button)

        self.result_label = QLabel("Результат: ")
        layout.addWidget(self.result_label)

        self.setLayout(layout)

    def analyze_text(self):
        text = self.text_input.toPlainText().strip()
        if not text:
            self.result_label.setText("Ошибка: Введите текст")
            return
        try:
            sentiment = self.analyzer.predict(text)
            self.result_label.setText(f"Результат: {sentiment}")
        except Exception as e:
            self.result_label.setText(f"Ошибка анализа: {e}")
