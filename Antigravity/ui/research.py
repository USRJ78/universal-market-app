from PyQt6.QtWidgets import QWidget, QLabel, QVBoxLayout

class ResearchPage(QWidget):

    def __init__(self):
        super().__init__()

        layout = QVBoxLayout()

        layout.addWidget(
            QLabel("Research Lab")
        )

        self.setLayout(layout)