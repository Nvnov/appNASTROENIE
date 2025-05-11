
from PySide6.QtWidgets import QMainWindow, QWidget, QPushButton, QVBoxLayout, QStackedWidget, QHBoxLayout
from ui.text_analysis import TextAnalysisWidget
from ui.post_analysis import PostAnalysisWidget
from PySide6.QtGui import QIcon
from ui.group_analysis import GroupAnalysisWidget
from ui.post_comments_analysis import PostCommentsAnalysisWidget
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("NASTROENIE")
        self.setMinimumSize(1000, 700)
        self.setWindowIcon(QIcon("resources/icon2.png"))
        

        self.current_theme = "light"
        self.apply_theme()

        self.stacked_widget = QStackedWidget()

        self.text_analysis_page = TextAnalysisWidget()
        self.post_analysis_page = PostAnalysisWidget()
        self.group_analysis_page = GroupAnalysisWidget(main_window=self)

        self.stacked_widget.addWidget(self.text_analysis_page)
        self.stacked_widget.addWidget(self.post_analysis_page)
        self.stacked_widget.addWidget(self.group_analysis_page)

        central_widget = QWidget()
        central_layout = QVBoxLayout(central_widget)

        self.menu_layout = QHBoxLayout()

        self.text_analysis_button = QPushButton("Анализ текста")
        self.post_analysis_button = QPushButton("Анализ поста")
        self.group_analysis_button = QPushButton("Анализ группы")
        self.theme_button = QPushButton("Сменить тему")

        self.text_analysis_button.clicked.connect(lambda: self.stacked_widget.setCurrentIndex(0))
        self.post_analysis_button.clicked.connect(lambda: self.stacked_widget.setCurrentIndex(1))
        self.group_analysis_button.clicked.connect(lambda: self.stacked_widget.setCurrentIndex(2))
        self.theme_button.clicked.connect(self.toggle_theme)

        self.menu_layout.addWidget(self.text_analysis_button)
        self.menu_layout.addWidget(self.post_analysis_button)
        self.menu_layout.addWidget(self.group_analysis_button)
        self.menu_layout.addWidget(self.theme_button)

        central_layout.addLayout(self.menu_layout)
        central_layout.addWidget(self.stacked_widget)

        self.setCentralWidget(central_widget)

    def apply_theme(self):
        qss_file = os.path.join("themes", self.current_theme)
        try:
            if not os.path.exists(qss_file):
                logger.error(f"Файл темы {qss_file} не найден")
                return
            with open(qss_file, "r", encoding="utf-8") as f:
                self.setStyleSheet(f.read())
                logger.info(f"Тема {self.current_theme} успешно загружена из {qss_file}")
        except Exception as e:
            logger.error(f"Ошибка загрузки темы {qss_file}: {e}")

    def toggle_theme(self):
        self.current_theme = "dark" if self.current_theme == "light" else "light"
        logger.info(f"Тема изменена на: {self.current_theme}")

        # Обновляем тему для всех страниц
        self.text_analysis_page.current_theme = self.current_theme
        self.post_analysis_page.current_theme = self.current_theme
        self.group_analysis_page.current_theme = self.current_theme

        # Обновляем графики и таблицы только для активной вкладки
        current_widget = self.stacked_widget.currentWidget()
        current_widget.current_theme = self.current_theme
        if hasattr(current_widget, 'last_sentiment_counts') and current_widget.last_sentiment_counts:
            current_widget.show_graphs()
            if hasattr(current_widget, 'filter_comments'):
                current_widget.filter_comments(current_widget.filter_combo.currentText())
            elif hasattr(current_widget, 'filter_posts'):
                current_widget.filter_posts(current_widget.filter_combo.currentText())

        self.apply_theme()

    def return_to_group_analysis(self):
        logger.info("Возврат на вкладку анализа группы")
        self.stacked_widget.setCurrentWidget(self.group_analysis_page)