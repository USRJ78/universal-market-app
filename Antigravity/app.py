import sys

from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QPushButton,
    QVBoxLayout,
    QHBoxLayout,
    QStackedWidget
)

from ui.dashboard import DashboardPage
from ui.portfolio import PortfolioPage
from ui.strategies import StrategiesPage
from ui.research import ResearchPage
from ui.settings import SettingsPage


class MainWindow(QMainWindow):

    def __init__(self):

        super().__init__()

        self.setWindowTitle("Antigravity Trading Platform")

        self.resize(1400, 900)

        # ==================================================
        # CENTRAL WIDGET
        # ==================================================

        central_widget = QWidget()

        self.setCentralWidget(central_widget)

        main_layout = QHBoxLayout()

        # ==================================================
        # SIDEBAR
        # ==================================================

        sidebar = QVBoxLayout()

        self.dashboard_btn = QPushButton("Dashboard")

        self.portfolio_btn = QPushButton("Portfolio")

        self.strategies_btn = QPushButton("Strategies")

        self.research_btn = QPushButton("Research Lab")

        self.settings_btn = QPushButton("Settings")

        sidebar.addWidget(self.dashboard_btn)

        sidebar.addWidget(self.portfolio_btn)

        sidebar.addWidget(self.strategies_btn)

        sidebar.addWidget(self.research_btn)

        sidebar.addWidget(self.settings_btn)

        sidebar.addStretch()

        # ==================================================
        # STACKED PAGES
        # ==================================================

        self.pages = QStackedWidget()

        self.dashboard_page = DashboardPage()

        self.portfolio_page = PortfolioPage()

        self.strategies_page = StrategiesPage()

        self.research_page = ResearchPage()

        self.settings_page = SettingsPage()

        self.pages.addWidget(self.dashboard_page)

        self.pages.addWidget(self.portfolio_page)

        self.pages.addWidget(self.strategies_page)

        self.pages.addWidget(self.research_page)

        self.pages.addWidget(self.settings_page)

        # ==================================================
        # BUTTON CONNECTIONS
        # ==================================================

        self.dashboard_btn.clicked.connect(
            lambda: self.pages.setCurrentIndex(0)
        )

        self.portfolio_btn.clicked.connect(
            lambda: self.pages.setCurrentIndex(1)
        )

        self.strategies_btn.clicked.connect(
            lambda: self.pages.setCurrentIndex(2)
        )

        self.research_btn.clicked.connect(
            lambda: self.pages.setCurrentIndex(3)
        )

        self.settings_btn.clicked.connect(
            lambda: self.pages.setCurrentIndex(4)
        )

        # ==================================================
        # LAYOUT
        # ==================================================

        main_layout.addLayout(sidebar, 1)

        main_layout.addWidget(self.pages, 5)

        central_widget.setLayout(main_layout)


def main():

    app = QApplication(sys.argv)

    window = MainWindow()

    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":

    main()