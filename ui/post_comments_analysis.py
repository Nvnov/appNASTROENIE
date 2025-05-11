import pandas as pd
import os
import logging
from PySide6.QtWidgets import QMessageBox, QWidget, QVBoxLayout, QLabel, QPushButton, QTableWidget, QTableWidgetItem, QFileDialog, QHBoxLayout, QGridLayout, QComboBox, QProgressBar
from PySide6.QtCore import Signal, Qt
from logic.sentiment_model import SentimentAnalyzer
from logic.vk_client import VKClient
from config import VK_API_TOKEN
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import vk_api
from datetime import datetime
import matplotlib.pyplot as plt

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PostCommentsAnalysisWidget(QWidget):
    back_clicked = Signal()

    def __init__(self, owner_id, post_id):
        super().__init__()
        self.owner_id = owner_id
        self.post_id = post_id
        self.post_url = f"https://vk.com/wall{owner_id}_{post_id}"
        self.last_sentiment_counts = {}
        self.vk_client = VKClient(VK_API_TOKEN)
        self.analyzer = SentimentAnalyzer()
        self.current_theme = "light"
        self.all_comments_data = []

        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        self.post_label = QLabel(f"Анализ комментариев к посту: {self.post_url}")
        layout.addWidget(self.post_label)

        self.back_button = QPushButton("Назад")
        self.back_button.clicked.connect(self.back_clicked.emit)
        layout.addWidget(self.back_button)

        buttons_layout = QHBoxLayout()
        self.load_button = QPushButton("Загрузить комментарии")
        self.load_button.clicked.connect(self.load_comments)
        buttons_layout.addWidget(self.load_button)

        self.clear_button = QPushButton("Очистить")
        self.clear_button.clicked.connect(self.clear_data)
        buttons_layout.addWidget(self.clear_button)
        buttons_layout.addStretch()
        layout.addLayout(buttons_layout)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        filter_sort_layout = QHBoxLayout()
        filter_sort_layout.setSpacing(10)
        self.filter_combo = QComboBox()
        self.filter_combo.addItems(["Все", "позитив", "негатив", "нейтрально", "сарказм_ирония", "смешанные_эмоции"])
        self.filter_combo.currentTextChanged.connect(self.filter_comments)
        filter_sort_layout.addWidget(QLabel("Фильтр:"))
        filter_sort_layout.addWidget(self.filter_combo)

        self.sort_combo = QComboBox()
        self.sort_combo.addItems([
            "Текст (А-Я)", "Текст (Я-А)",
            "Тональность (А-Я)", "Тональность (Я-А)",
            "Дата (новые)", "Дата (старые)"
        ])
        self.sort_combo.currentTextChanged.connect(self.sort_comments)
        filter_sort_layout.addWidget(QLabel("Сортировка:"))
        filter_sort_layout.addWidget(self.sort_combo)
        filter_sort_layout.addStretch()
        layout.addLayout(filter_sort_layout)

        self.comments_table = QTableWidget()
        self.comments_table.setColumnCount(4)
        self.comments_table.setHorizontalHeaderLabels(["Дата", "Автор", "Комментарий", "Тональность"])
        self.comments_table.horizontalHeader().setStretchLastSection(True)
        self.comments_table.setWordWrap(True)
        self.comments_table.resizeColumnsToContents()
        layout.addWidget(self.comments_table)

        self.graphs_layout = QGridLayout()
        self.graphs_layout.setSpacing(10)
        layout.addLayout(self.graphs_layout)

        self.save_buttons_layout = QHBoxLayout()
        self.save_buttons_layout.setSpacing(10)
        self.save_graph_button = QPushButton("Сохранить графики")
        self.save_graph_button.clicked.connect(self.save_graphs)
        self.save_buttons_layout.addWidget(self.save_graph_button)

        self.save_text_button = QPushButton("Сохранить текст в Excel")
        self.save_text_button.clicked.connect(self.save_text)
        self.save_buttons_layout.addWidget(self.save_text_button)
        self.save_buttons_layout.addStretch()
        layout.addLayout(self.save_buttons_layout)

        self.setLayout(layout)
        self.vk_client.progress_updated.connect(self.update_progress)

    def update_progress(self, value):
        self.progress_bar.setValue(value)
        if value == 100:
            self.progress_bar.setVisible(False)
        else:
            self.progress_bar.setVisible(True)

    def clear_data(self):
        logger.info("Очистка данных в PostCommentsAnalysisWidget")
        self.comments_table.setRowCount(0)
        self.all_comments_data = []
        self.last_sentiment_counts = {}
        for i in reversed(range(self.graphs_layout.count())):
            widget = self.graphs_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)
        self.progress_bar.setVisible(False)
        self.filter_combo.setCurrentText("Все")
        self.sort_combo.setCurrentText("Текст (А-Я)")

    def load_comments(self):
        comments = self.get_comments()
        logger.info(f"Загружено комментариев: {len(comments)}")

        self.all_comments_data = []
        sentiment_counts = {}

        for comment in comments:
            try:
                sentiment = self.analyzer.predict(comment["text"])
                logger.info(f"Комментарий: {comment['text'][:50]}..., Тональность: {sentiment}")
                comment_date = datetime.fromtimestamp(comment["date"]).strftime("%Y-%m-%d %H:%M")
                self.all_comments_data.append({ 
                    "date": comment["date"],
                    "date_str": comment_date,
                    "author": comment["author"],
                    "text": comment["text"],
                    "sentiment": sentiment
                })
                sentiment_counts[sentiment] = sentiment_counts.get(sentiment, 0) + 1
            except Exception as e:
                logger.error(f"Ошибка анализа комментария: {e}")

        self.last_sentiment_counts = sentiment_counts
        logger.info(f"Итоговые тональности: {sentiment_counts}")
        self.filter_comments("Все")
        self.show_graphs(sentiment_counts)

    def filter_comments(self, sentiment_filter):
        logger.info(f"Применение фильтра: {sentiment_filter}")
        filtered_comments = [
            comment for comment in self.all_comments_data
            if sentiment_filter == "Все" or comment["sentiment"] == sentiment_filter
        ]
        self.sort_comments(self.sort_combo.currentText(), filtered_comments)

    def sort_comments(self, sort_option, comments=None):
        logger.info(f"Применение сортировки: {sort_option}")
        if comments is None:
            comments = [
                comment for comment in self.all_comments_data
                if self.filter_combo.currentText() == "Все" or comment["sentiment"] == self.filter_combo.currentText()
            ]
        if sort_option == "Текст (А-Я)":
            comments.sort(key=lambda x: x["text"].lower())
        elif sort_option == "Текст (Я-А)":
            comments.sort(key=lambda x: x["text"].lower(), reverse=True)
        elif sort_option == "Тональность (А-Я)":
            comments.sort(key=lambda x: x["sentiment"])
        elif sort_option == "Тональность (Я-А)":
            comments.sort(key=lambda x: x["sentiment"], reverse=True)
        elif sort_option == "Дата (новые)":
            comments.sort(key=lambda x: x["date"], reverse=True)
        elif sort_option == "Дата (старые)":
            comments.sort(key=lambda x: x["date"])

        self.comments_table.setRowCount(len(comments))
        for row, comment in enumerate(comments):
            self.comments_table.setItem(row, 2, QTableWidgetItem(comment["text"]))
            self.comments_table.setItem(row, 3, QTableWidgetItem(comment["sentiment"]))
            self.comments_table.setItem(row, 1, QTableWidgetItem(comment["author"]))
            self.comments_table.setItem(row, 0, QTableWidgetItem(comment["date_str"]))
        self.comments_table.resizeColumnsToContents()

    def get_comments(self):
        try:
            self.progress_bar.setVisible(True)
            self.progress_bar.setValue(0)
            return self.vk_client.get_comments(self.post_url, max_count=100)
        except vk_api.exceptions.ApiError as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка VK API: {e}")
            self.progress_bar.setVisible(False)
            return []
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось загрузить комментарии: {e}")
            self.progress_bar.setVisible(False)
            return []

    def save_graphs(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "Сохранить графики", "", "PNG Files (*.png)")
        if file_path:
            for i in range(self.graphs_layout.count()):
                widget = self.graphs_layout.itemAt(i).widget()
                if isinstance(widget, FigureCanvas):
                    base, ext = os.path.splitext(file_path)
                    widget.figure.savefig(f"{base}_{i+1}{ext}")
                    logger.info(f"График {i+1} сохранен: {base}_{i+1}{ext}")

    def save_text(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "Сохранить текст в Excel", "", "Excel Files (*.xlsx)")
        if file_path:
            data = []
            for row in range(self.comments_table.rowCount()):
                date = self.comments_table.item(row, 0).text()
                author = self.comments_table.item(row, 1).text()
                comment = self.comments_table.item(row, 2).text()
                sentiment = self.comments_table.item(row, 3).text()
                data.append([date, author, comment, sentiment])
            df = pd.DataFrame(data, columns=["Дата", "Автор", "Комментарий", "Тональность"])
            df.to_excel(file_path, index=False, engine="openpyxl")
            logger.info(f"Текст сохранён в {file_path}")

    def show_graphs(self, sentiment_counts=None):
        if sentiment_counts is None:
            sentiment_counts = self.last_sentiment_counts
        if not sentiment_counts:
            logger.warning("Нет данных для отображения графиков")
            return

        # Очистка старых графиков
        for i in reversed(range(self.graphs_layout.count())):
            widget = self.graphs_layout.itemAt(i).widget()
            if widget:
                if isinstance(widget, FigureCanvas):
                    plt.close(widget.figure)  # Закрываем старую фигуру
                widget.setParent(None)
        logger.info("Старые графики очищены")

        background_color = '#2b2b2b' if self.current_theme == "dark" else 'white'
        text_color = 'white' if self.current_theme == "dark" else 'black'
        sector_colors = ['#2ca02c', '#d62728', '#ff7f0e', '#9467bd', '#1f77b4']

        labels = list(sentiment_counts.keys())
        sizes = list(sentiment_counts.values())
        logger.info(f"График 1 - Категории: {labels}, Значения: {sizes}")

        # Круговая диаграмма
        fig1 = Figure(figsize=(4, 3))
        ax1 = fig1.add_subplot(111)
        fig1.patch.set_facecolor(background_color)
        ax1.pie(
            sizes,
            labels=labels,
            colors=sector_colors[:len(labels)],
            autopct='%1.1f%%',
            textprops={'color': text_color}
        )
        ax1.set_title("Распределение тональностей", color=text_color)

        # Общая тональность
        dominant_sentiment = max(sentiment_counts, key=sentiment_counts.get) if sentiment_counts else "Нет данных"
        sentiment_label = QLabel(f"Общая тональность: {dominant_sentiment}")
        sentiment_label.setStyleSheet(f"color: {text_color}; font-size: 14px;")
        sentiment_label.setAlignment(Qt.AlignCenter)

        try:
            self.graphs_layout.addWidget(FigureCanvas(fig1), 0, 0)
            self.graphs_layout.addWidget(sentiment_label, 0, 1)
            logger.info("График и метка тональности успешно добавлены в layout")
        except Exception as e:
            logger.error(f"Ошибка при добавлении графика или метки в layout: {e}")