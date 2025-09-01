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


DATA_FILE = Path("accounts.parquet")


SCHEMA = {
    "contacts": pl.String,
    "payment_method": pl.String,
    "details": pl.String,
    "amount": pl.Decimal(precision=10, scale=2),
    "timestamp": pl.Datetime,
}


class AccountingApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("商户记账软件")
        self.setGeometry(100, 100, 800, 600)

        self.df = self.load_data()

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        entry_group = QGroupBox("记账录入")
        entry_layout = QFormLayout()

        self.qq_entry = QLineEdit()
        entry_layout.addRow("QQ号:", self.qq_entry)
        self.wechat_entry = QLineEdit()
        entry_layout.addRow("微信号:", self.wechat_entry)
        self.taobao_entry = QLineEdit()
        entry_layout.addRow("淘宝号:", self.taobao_entry)

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

        query_group = QGroupBox("查询")
        query_layout = QVBoxLayout()

        query_hlayout = QHBoxLayout()
        self.contact_query = QLineEdit()
        query_hlayout.addWidget(QLabel("联系方式 (QQ/微信/淘宝):"))
        query_hlayout.addWidget(self.contact_query)

        query_button = QPushButton("查询")
        query_button.clicked.connect(self.query_records)
        query_hlayout.addWidget(query_button)

        query_layout.addLayout(query_hlayout)

        self.total_label = QLabel("总付款额: 0.00")
        query_layout.addWidget(self.total_label)

        self.records_table = QTableWidget()
        self.records_table.setColumnCount(5)
        self.records_table.setHorizontalHeaderLabels(
            ["联系方式", "付款方式", "详情", "金额", "时间"]
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
        qq = self.qq_entry.text().strip()
        wechat = self.wechat_entry.text().strip()
        taobao = self.taobao_entry.text().strip()

        if not (qq or wechat or taobao):
            QMessageBox.warning(self, "错误", "至少提供一种联系方式")
            return

        contacts = "$".join(filter(None, [qq, wechat, taobao]))

        existing_contact = None
        if self.df.height > 0:
            for contact in [qq, wechat, taobao]:
                if contact:
                    match = self.df.filter(
                        pl.col("contacts").str.split("$").list.contains(contact)
                    )
                    if not match.is_empty():
                        existing_contact = match["contacts"][0]
                        break

        payment_method = self.payment_method.currentText()
        details = self.details_entry.text().strip()
        amount_float = self.amount_entry.value()
        amount = Decimal(str(amount_float)).quantize(Decimal("0.00"))

        timestamp = datetime.now()

        final_contacts = existing_contact if existing_contact else contacts

        new_row = pl.DataFrame(
            {
                "contacts": [final_contacts],
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
        self.qq_entry.clear()
        self.wechat_entry.clear()
        self.taobao_entry.clear()
        self.details_entry.clear()
        self.amount_entry.setValue(0.0)
        self.payment_method.setCurrentIndex(0)

    def query_records(self):
        contact = self.contact_query.text().strip()
        if not contact:
            QMessageBox.warning(self, "错误", "联系方式不能为空")
            return

        filtered_df = self.df.filter(
            pl.col("contacts").str.split("$").list.contains(contact)
        )

        if filtered_df.is_empty():
            QMessageBox.information(self, "无记录", "没有找到该联系方式的记录")
            self.total_label.setText("总付款额: 0.00")
            self.records_table.setRowCount(0)
            return

        total = sum(filtered_df["amount"].to_list())
        self.total_label.setText(f"总付款额: {total:.2f}")

        self.records_table.setRowCount(filtered_df.height)
        for row_idx, row in enumerate(filtered_df.iter_rows(named=True)):
            self.records_table.setItem(row_idx, 0, QTableWidgetItem(row["contacts"]))
            self.records_table.setItem(
                row_idx, 1, QTableWidgetItem(row["payment_method"])
            )
            self.records_table.setItem(row_idx, 2, QTableWidgetItem(row["details"]))
            self.records_table.setItem(
                row_idx, 3, QTableWidgetItem(f"{row['amount']:.2f}")
            )
            self.records_table.setItem(
                row_idx,
                4,
                QTableWidgetItem(row["timestamp"].strftime("%Y-%m-%d %H:%M:%S")),
            )

        self.records_table.resizeColumnsToContents()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = AccountingApp()
    window.show()
    sys.exit(app.exec())
