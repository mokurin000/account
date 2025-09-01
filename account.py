import sys
from datetime import datetime
from decimal import Decimal
from pathlib import Path

import polars as pl
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

# Data file path
DATA_FILE = Path("accounts.parquet")

# Schema for the DataFrame
SCHEMA = {
    "contact": pl.String,
    "payment_method": pl.String,
    "details": pl.String,
    "amount": pl.Decimal(precision=10, scale=2),  # DECIMAL with 2 decimal places
    "timestamp": pl.Datetime,
}


class AccountingApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("商户记账软件")
        self.setGeometry(100, 100, 800, 600)

        # Load data
        self.df = self.load_data()

        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # Entry group
        entry_group = QGroupBox("记账录入")
        entry_layout = QFormLayout()

        self.contact_entry = QLineEdit()
        entry_layout.addRow("联系方式:", self.contact_entry)

        self.payment_method = QComboBox()
        self.payment_method.addItems(["微信", "淘宝", "支付宝", "银行卡"])
        entry_layout.addRow("付款方式:", self.payment_method)

        self.details_entry = QLineEdit()
        entry_layout.addRow("付款详情:", self.details_entry)

        self.amount_entry = QDoubleSpinBox()
        self.amount_entry.setRange(-1000000, 1000000)
        self.amount_entry.setDecimals(2)
        self.amount_entry.setSingleStep(0.01)
        entry_layout.addRow("金额 (负数为退款):", self.amount_entry)

        submit_button = QPushButton("提交")
        submit_button.clicked.connect(self.submit_entry)
        entry_layout.addRow(submit_button)

        entry_group.setLayout(entry_layout)
        main_layout.addWidget(entry_group)

        # Query group
        query_group = QGroupBox("查询")
        query_layout = QVBoxLayout()

        query_hlayout = QHBoxLayout()
        self.contact_query = QLineEdit()
        query_hlayout.addWidget(QLabel("联系方式:"))
        query_hlayout.addWidget(self.contact_query)

        query_button = QPushButton("查询")
        query_button.clicked.connect(self.query_records)
        query_hlayout.addWidget(query_button)

        query_layout.addLayout(query_hlayout)

        self.total_label = QLabel("总付款额: 0.00")
        query_layout.addWidget(self.total_label)

        self.records_table = QTableWidget()
        self.records_table.setColumnCount(4)
        self.records_table.setHorizontalHeaderLabels(
            ["付款方式", "详情", "金额", "时间"]
        )
        query_layout.addWidget(self.records_table)

        entry_group.setLayout(entry_layout)
        query_group.setLayout(query_layout)

        main_layout.addWidget(entry_group)
        main_layout.addWidget(query_group)

    def load_data(self):
        if DATA_FILE.exists():
            return pl.read_parquet(DATA_FILE)
        else:
            return pl.DataFrame(schema=SCHEMA)

    def save_data(self):
        self.df.write_parquet(DATA_FILE)

    def submit_entry(self):
        contact = self.contact_entry.text().strip()
        if not contact:
            QMessageBox.warning(self, "错误", "联系方式不能为空")
            return

        payment_method = self.payment_method.currentText()
        details = self.details_entry.text().strip()
        amount_float = self.amount_entry.value()
        amount = Decimal(str(amount_float)).quantize(
            Decimal("0.00")
        )  # Ensure 2 decimal places

        timestamp = datetime.now()

        new_row = pl.DataFrame(
            {
                "contact": [contact],
                "payment_method": [payment_method],
                "details": [details],
                "amount": [amount],
                "timestamp": [timestamp],
            },
            schema=SCHEMA,
        )

        self.df = pl.concat([self.df, new_row], how="diagonal_relaxed")
        self.save_data()

        QMessageBox.information(self, "成功", "记账已提交")
        self.clear_entry_fields()

    def clear_entry_fields(self):
        self.contact_entry.clear()
        self.details_entry.clear()
        self.amount_entry.setValue(0.0)
        self.payment_method.setCurrentIndex(0)

    def query_records(self):
        contact = self.contact_query.text().strip()
        if not contact:
            QMessageBox.warning(self, "错误", "联系方式不能为空")
            return

        filtered_df = self.df.filter(pl.col("contact") == contact)
        if filtered_df.is_empty():
            QMessageBox.information(self, "无记录", "没有找到该联系方式的记录")
            self.total_label.setText("总付款额: 0.00")
            self.records_table.setRowCount(0)
            return

        # Calculate total
        total = sum(filtered_df["amount"].to_list())
        self.total_label.setText(f"总付款额: {total:.2f}")

        # Display records
        self.records_table.setRowCount(filtered_df.height)
        for row_idx, row in enumerate(filtered_df.iter_rows(named=True)):
            self.records_table.setItem(
                row_idx, 0, QTableWidgetItem(row["payment_method"])
            )
            self.records_table.setItem(row_idx, 1, QTableWidgetItem(row["details"]))
            self.records_table.setItem(
                row_idx, 2, QTableWidgetItem(f"{row['amount']:.2f}")
            )
            self.records_table.setItem(
                row_idx,
                3,
                QTableWidgetItem(row["timestamp"].strftime("%Y-%m-%d %H:%M:%S")),
            )

        self.records_table.resizeColumnsToContents()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = AccountingApp()
    window.show()
    sys.exit(app.exec())
