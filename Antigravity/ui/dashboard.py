from PyQt6.QtWidgets import (
    QWidget,
    QLabel,
    QVBoxLayout,
    QGridLayout,
    QFrame
)

from database.db_manager import (
    get_latest_portfolio,
    get_total_trades,
    get_win_rate,
    get_total_profit
)


class DashboardPage(QWidget):

    def __init__(self):

        super().__init__()

        self.build_ui()

    def metric_card(self, title, value):

        card = QFrame()

        card.setFrameShape(QFrame.Shape.Box)

        layout = QVBoxLayout()

        title_label = QLabel(title)

        value_label = QLabel(str(value))

        value_label.setStyleSheet(
            "font-size:20px;font-weight:bold;"
        )

        layout.addWidget(title_label)

        layout.addWidget(value_label)

        card.setLayout(layout)

        return card

    def build_ui(self):

        layout = QVBoxLayout()

        capital = get_latest_portfolio()

        trades = get_total_trades()

        winrate = get_win_rate()

        profit = get_total_profit()

        grid = QGridLayout()

        grid.addWidget(
            self.metric_card(
                "Capital",
                f"₹{capital:,.0f}"
            ),
            0,
            0
        )

        grid.addWidget(
            self.metric_card(
                "Profit",
                f"₹{profit:,.0f}"
            ),
            0,
            1
        )

        grid.addWidget(
            self.metric_card(
                "Win Rate",
                f"{winrate}%"
            ),
            1,
            0
        )

        grid.addWidget(
            self.metric_card(
                "Trades",
                trades
            ),
            1,
            1
        )

        layout.addLayout(grid)

        self.setLayout(layout)