import pandas as pd
import os
import logging
from PySide6.QtWidgets import QFileDialog, QWidget, QVBoxLayout, QLabel, QPushButton, QLineEdit, QTableWidget, QTableWidgetItem, QHBoxLayout, QGridLayout, QComboBox, QProgressBar
from PySide6.QtCore import Qt
from logic.sentiment_model import SentimentAnalyzer
from logic.vk_client import VKClient
from config import VK_API_TOKEN
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from ui.post_comments_analysis import PostCommentsAnalysisWidget
from datetime import datetime
import matplotlib.pyplot as plt

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GroupAnalysisWidget(QWidget):
    def __init__(self, main_window=None):
        super().__init__()
        self.main_window = main_window
        self.vk_client = VKClient(VK_API_TOKEN)
        self.analyzer = SentimentAnalyzer()
        self.last_sentiment_counts = {}
        self.posts = []
        self.current_theme = "light"
        self.all_posts_data = []

        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        self.group_link_input = QLineEdit()
        self.group_link_input.setPlaceholderText("Введите ссылку на группу ВКонтакте (например, https://vk.com/themovieblog?from=groups)...")
        layout.addWidget(self.group_link_input)

        buttons_layout = QHBoxLayout()
        self.load_button = QPushButton("Загрузить посты")
        self.load_button.clicked.connect(self.load_posts)
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
        self.filter_combo.currentTextChanged.connect(self.filter_posts)
        filter_sort_layout.addWidget(QLabel("Фильтр:"))
        filter_sort_layout.addWidget(self.filter_combo)

        self.sort_combo = QComboBox()
        self.sort_combo.addItems([
            "Текст (А-Я)", "Текст (Я-А)",
            "Тональность (А-Я)", "Тональность (Я-А)",
            "Дата (новые)", "Дата (старые)"
        ])
        self.sort_combo.currentTextChanged.connect(self.sort_posts)
        filter_sort_layout.addWidget(QLabel("Сортировка:"))
        filter_sort_layout.addWidget(self.sort_combo)
        filter_sort_layout.addStretch()
        layout.addLayout(filter_sort_layout)

        self.posts_table = QTableWidget()
        self.posts_table.setColumnCount(5)
        self.posts_table.setHorizontalHeaderLabels(["Дата", "Пост", "Комментарии", "Тональность", "Действия"])
        self.posts_table.horizontalHeader().setStretchLastSection(True)
        self.posts_table.setWordWrap(True)
        self.posts_table.resizeColumnsToContents()
        layout.addWidget(self.posts_table)

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
        logger.info("Очистка данных в GroupAnalysisWidget")
        self.group_link_input.clear()
        self.posts_table.setRowCount(0)
        self.posts = []
        self.all_posts_data = []
        self.last_sentiment_counts = {}
        for i in reversed(range(self.graphs_layout.count())):
            widget = self.graphs_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)
        self.progress_bar.setVisible(False)
        self.filter_combo.setCurrentText("Все")
        self.sort_combo.setCurrentText("Текст (А-Я)")

    def load_posts(self):
        group_url = self.group_link_input.text().strip()
        if not group_url:
            logger.warning("Пустая ссылка на группу")
            self.posts_table.setRowCount(0)
            return

        try:
            self.progress_bar.setVisible(True)
            self.progress_bar.setValue(0)
            self.posts = self.vk_client.get_posts(group_url, max_count=100)
            logger.info(f"Загружено постов: {len(self.posts)}")
        except Exception as e:
            logger.error(f"Не удалось загрузить посты: {e}")
            self.posts_table.setRowCount(0)
            self.progress_bar.setVisible(False)
            return

        self.all_posts_data = []
        sentiment_counts = {}

        for post in self.posts:
            try:
                sentiment = self.analyzer.predict(post["text"])
                logger.info(f"Пост: {post['text'][:50]}..., Тональность: {sentiment}")
                post_date = datetime.fromtimestamp(post["date"]).strftime("%Y-%m-%d %H:%M")
                comments_count = post.get("comments_count", 0)
                if "comments_count" not in post:
                    logger.warning(f"Поле comments_count отсутствует для поста {post.get('post_id')}")
                self.all_posts_data.append({
                    "date": post["date"],
                    "date_str": post_date,
                    "owner_id": post["owner_id"],
                    "post_id": post["post_id"],
                    "text": post["text"],
                    "sentiment": sentiment,
                    "comments_count": comments_count
                })
                sentiment_counts[sentiment] = sentiment_counts.get(sentiment, 0) + 1
            except Exception as e:
                logger.error(f"Ошибка анализа поста: {e}")

        self.last_sentiment_counts = sentiment_counts
        logger.info(f"Итоговые тональности: {sentiment_counts}")
        self.filter_posts("Все")
        self.show_graphs(sentiment_counts)

    def filter_posts(self, sentiment_filter):
        logger.info(f"Применение фильтра: {sentiment_filter}")
        filtered_posts = [
            post for post in self.all_posts_data
            if sentiment_filter == "Все" or post["sentiment"] == sentiment_filter
        ]
        self.posts = [
            {
                "date": post["date"],
                "date_str": post["date_str"],
                "text": post["text"],
                "owner_id": post["owner_id"],
                "post_id": post["post_id"],
                "comments_count": post["comments_count"]
            }
            for post in filtered_posts
        ]
        logger.info(f"Отфильтровано постов: {len(self.posts)}")
        self.sort_posts(self.sort_combo.currentText())

    def sort_posts(self, sort_option):
        logger.info(f"Применение сортировки: {sort_option}")
        filtered_posts = [
            post for post in self.all_posts_data
            if self.filter_combo.currentText() == "Все" or post["sentiment"] == self.filter_combo.currentText()
        ]
        if sort_option == "Текст (А-Я)":
            filtered_posts.sort(key=lambda x: x["text"].lower())
        elif sort_option == "Текст (Я-А)":
            filtered_posts.sort(key=lambda x: x["text"].lower(), reverse=True)
        elif sort_option == "Тональность (А-Я)":
            filtered_posts.sort(key=lambda x: x["sentiment"])
        elif sort_option == "Тональность (Я-А)":
            filtered_posts.sort(key=lambda x: x["sentiment"], reverse=True)
        elif sort_option == "Дата (новые)":
            filtered_posts.sort(key=lambda x: x["date"], reverse=True)
        elif sort_option == "Дата (старые)":
            filtered_posts.sort(key=lambda x: x["date"])

        self.posts = [
            {
                "date": post["date"],
                "date_str": post["date_str"],
                "text": post["text"],
                "owner_id": post["owner_id"],
                "post_id": post["post_id"],
                "comments_count": post["comments_count"]
            }
            for post in filtered_posts
        ]
        logger.info(f"Отсортировано постов: {len(self.posts)}")
        self.posts_table.setRowCount(len(filtered_posts))
        for row, post in enumerate(filtered_posts):
            self.posts_table.setItem(row, 0, QTableWidgetItem(post["date_str"]))
            self.posts_table.setItem(row, 1, QTableWidgetItem(post["text"]))
            self.posts_table.setItem(row, 2, QTableWidgetItem(str(post["comments_count"])))
            self.posts_table.setItem(row, 3, QTableWidgetItem(post["sentiment"]))
            analyze_button = QPushButton("Анализировать")
            analyze_button.clicked.connect(lambda _, r=row: self.open_post_comments(r, 0))
            self.posts_table.setCellWidget(row, 4, analyze_button)
        self.posts_table.resizeColumnsToContents()
        self.posts_table.cellDoubleClicked.connect(self.open_post_comments)

    def open_post_comments(self, row, column):
        logger.info(f"Попытка открыть комментарии для строки {row}, столбца {column}")
        if not self.posts:
            logger.warning("Список постов пуст")
            return
        if row < 0 or row >= len(self.posts):
            logger.warning(f"Неверный индекс строки: {row}, длина posts: {len(self.posts)}")
            return
        post = self.posts[row]
        owner_id = post.get("owner_id")
        post_id = post.get("post_id")
        if not owner_id or not post_id:
            logger.error(f"Неверные данные поста: owner_id={owner_id}, post_id={post_id}")
            return
        logger.info(f"Открытие анализа комментариев для поста: wall{owner_id}_{post_id}")
        if not self.main_window:
            logger.error("MainWindow не передан в GroupAnalysisWidget")
            return
        try:
            comments_widget = PostCommentsAnalysisWidget(owner_id, post_id)
            comments_widget.current_theme = self.current_theme
            comments_widget.back_clicked.connect(self.main_window.return_to_group_analysis)
            self.main_window.stacked_widget.addWidget(comments_widget)
            self.main_window.stacked_widget.setCurrentWidget(comments_widget)
            logger.info(f"Успешно открыт виджет анализа комментариев для поста wall{owner_id}_{post_id}")
        except Exception as e:
            logger.error(f"Ошибка при открытии анализа комментариев: {e}")

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
            for row in range(self.posts_table.rowCount()):
                post = self.posts_table.item(row, 1).text()
                comments_count = self.posts_table.item(row, 2).text()
                sentiment = self.posts_table.item(row, 3).text()
                date = self.posts_table.item(row, 0).text()
                data.append([post, comments_count, sentiment, date])
            df = pd.DataFrame(data, columns=["Пост", "Комментарии", "Тональность", "Дата"])
            df.to_excel(file_path, index=False, engine="openpyxl")
            logger.info(f"Текст сохранён в {file_path}")