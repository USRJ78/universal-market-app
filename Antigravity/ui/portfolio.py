from PyQt6.QtWidgets import QWidget, QLabel, QVBoxLayout

class PortfolioPage(QWidget):

    def __init__(self):
        super().__init__()

        layout = QVBoxLayout()

        layout.addWidget(
            QLabel("Portfolio")
        )

        self.setLayout(layout)