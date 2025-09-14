import sys
from datetime import datetime
from decimal import Decimal
from pathlib import Path

import polars as pl
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
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
    QDateEdit,
    QAbstractItemView,
)
from PySide6.QtCore import QDate
from PySide6.QtGui import Qt

DATA_FILE = Path("accounts.parquet")
EXPORT_FILE = Path("accounts.xlsx")

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
        main_hlayout = QHBoxLayout(central_widget)

        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)

        entry_group = QGroupBox("记账录入")
        entry_layout = QFormLayout()

        # Replace QLineEdit with QComboBox for contacts
        self.qq_combo = QComboBox()
        self.qq_combo.setEditable(True)
        entry_layout.addRow("QQ号:", self.qq_combo)
        self.wechat_combo = QComboBox()
        self.wechat_combo.setEditable(True)
        entry_layout.addRow("微信号:", self.wechat_combo)
        self.taobao_combo = QComboBox()
        self.taobao_combo.setEditable(True)
        entry_layout.addRow("淘宝号:", self.taobao_combo)

        # Populate combos with existing contacts
        self.populate_contact_combos()

        # Connect combo box signals to update other fields
        self.qq_combo.currentTextChanged.connect(
            lambda: self.update_contact_fields("qq")
        )
        self.wechat_combo.currentTextChanged.connect(
            lambda: self.update_contact_fields("wechat")
        )
        self.taobao_combo.currentTextChanged.connect(
            lambda: self.update_contact_fields("taobao")
        )

        self.payment_method = QComboBox()
        self.payment_method.addItems(
            [
                "微信",
                "淘宝",
                "支付宝",
                "京东",
                "拼多多",
                "（内部交易）",
            ]
        )
        entry_layout.addRow("付款方式:", self.payment_method)

        self.details_entry = QLineEdit()
        entry_layout.addRow("付款详情:", self.details_entry)

        self.amount_entry = QDoubleSpinBox()
        self.amount_entry.setRange(-1000000, 1000000)
        self.amount_entry.setDecimals(2)
        self.amount_entry.setSingleStep(0.01)
        entry_layout.addRow("金额 (负数为退款):", self.amount_entry)

        # Add checkbox for internal transaction
        self.internal_checkbox = QCheckBox("内部交易")
        entry_layout.addRow(self.internal_checkbox)

        submit_button = QPushButton("提交")
        submit_button.clicked.connect(self.submit_entry)
        entry_layout.addRow(submit_button)

        # Add copy to clipboard button
        copy_button = QPushButton("复制到剪贴板")
        copy_button.clicked.connect(self.copy_to_clipboard)
        entry_layout.addRow(copy_button)
        entry_group.setLayout(entry_layout)

        left_layout.addWidget(entry_group)

        # Add date selection for export
        date_layout = QHBoxLayout()
        self.start_date = QDateEdit()
        self.start_date.setDate(QDate.currentDate().addDays(-1))
        date_layout.addWidget(QLabel("开始日期:"))
        date_layout.addWidget(self.start_date)
        self.end_date = QDateEdit()
        self.end_date.setDate(QDate.currentDate())
        date_layout.addWidget(QLabel("结束日期:"))
        date_layout.addWidget(self.end_date)
        left_layout.addLayout(date_layout)

        # Add export button
        export_button = QPushButton("导出为Excel")
        export_button.clicked.connect(self.export_to_excel)
        left_layout.addWidget(export_button)

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

        query_group.setLayout(query_layout)

        left_layout.addWidget(query_group)

        main_hlayout.addWidget(left_widget)

        # Add right panel for recent 50 records
        recent_group = QGroupBox("最近50条记录")
        recent_layout = QVBoxLayout()

        delete_button = QPushButton("删除选中记录")
        delete_button.clicked.connect(self.delete_selected_record)
        recent_layout.addWidget(delete_button)

        self.recent_table = QTableWidget()
        self.recent_table.setColumnCount(5)
        self.recent_table.setHorizontalHeaderLabels(
            ["联系方式", "付款方式", "详情", "金额", "时间"]
        )
        self.recent_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.recent_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        recent_layout.addWidget(self.recent_table)

        recent_group.setLayout(recent_layout)
        main_hlayout.addWidget(recent_group)

        # Add totals panel to the right
        totals_group = QGroupBox("各付款方式总额")
        totals_layout = QVBoxLayout()

        self.totals_table = QTableWidget()
        self.totals_table.setColumnCount(2)
        self.totals_table.setHorizontalHeaderLabels(["付款方式", "总额"])
        self.totals_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        totals_layout.addWidget(self.totals_table)

        totals_group.setLayout(totals_layout)
        main_hlayout.addWidget(totals_group, alignment=Qt.AlignmentFlag.AlignRight)

        self.populate_recent_table()
        self.populate_totals_table()

    def load_data(self):
        if DATA_FILE.exists():
            return pl.read_parquet(DATA_FILE)
        else:
            return pl.DataFrame(schema=SCHEMA)

    def save_data(self):
        self.df.write_parquet(DATA_FILE)
        # Refresh combos after saving new data
        self.clear_entry_fields()
        self.populate_recent_table()
        self.populate_totals_table()

    def populate_contact_combos(self):
        """Populate contact combo boxes with unique values from DataFrame."""
        if self.df.is_empty():
            return

        # Get unique contacts by splitting the contacts column
        contacts = self.df["contacts"].unique().str.split("$").sort()

        for combo in [
            self.qq_combo,
            self.wechat_combo,
            self.taobao_combo,
        ]:
            combo.addItem("")

        for qq, wechat, taobao in contacts:
            self.qq_combo.addItem(qq)
            self.wechat_combo.addItem(wechat)
            self.taobao_combo.addItem(taobao)

    def update_contact_fields(self, changed_field):
        """Update other contact fields based on the selected contact."""
        if self.df.is_empty():
            return

        # Get the selected contact
        if changed_field == "qq":
            selected = self.qq_combo.currentText().strip()
        elif changed_field == "wechat":
            selected = self.wechat_combo.currentText().strip()
        else:  # taobao
            selected = self.taobao_combo.currentText().strip()

        if not selected:
            return

        # Find matching record
        match = self.df.filter(
            pl.col("contacts").str.split("$").list.contains(selected)
        )
        if match.is_empty():
            return

        # Get the contacts from the first matching record
        contact: str = match["contacts"][0]
        qq, wechat, taobao = contact.split("$")

        # Update other fields, but avoid infinite recursion
        if changed_field != "qq":
            self.qq_combo.blockSignals(True)
            self.qq_combo.setCurrentText(qq)
            self.qq_combo.blockSignals(False)
        if changed_field != "wechat":
            self.wechat_combo.blockSignals(True)
            self.wechat_combo.setCurrentText(wechat)
            self.wechat_combo.blockSignals(False)
        if changed_field != "taobao":
            self.taobao_combo.blockSignals(True)
            self.taobao_combo.setCurrentText(taobao)
            self.taobao_combo.blockSignals(False)

    def copy_to_clipboard(self):
        qq = self.qq_combo.currentText().strip()
        wechat = self.wechat_combo.currentText().strip()
        taobao = self.taobao_combo.currentText().strip()
        payment = self.payment_method.currentText()
        details = self.details_entry.text().strip()
        amount = self.amount_entry.value()

        lines = []
        if qq:
            lines.append(f"qq号: {qq}")
        if wechat:
            lines.append(f"微信号: {wechat}")
        if taobao:
            lines.append(f"淘宝号: {taobao}")
        action = "退款" if amount < 0 else "支付"
        abs_amount = abs(amount)
        lines.append(f"客户通过{payment}，{action}了 {abs_amount:.2f} 元")
        if details:
            lines.append(f"相关详情: {details}")

        text = "\n".join(lines)
        QApplication.clipboard().setText(text)
        QMessageBox.information(self, "成功", "已复制到剪贴板")

    def export_to_excel(self):
        try:
            if self.df.is_empty():
                QMessageBox.warning(self, "警告", "没有数据可导出")
                return

            start = self.start_date.date().toPython()
            end = self.end_date.date().toPython()

            filtered = self.df.filter(
                pl.col("timestamp").dt.date().is_between(start, end)
            )

            if filtered.is_empty():
                QMessageBox.warning(self, "警告", "选定日期范围内没有数据")
                return

            filtered.write_excel(EXPORT_FILE)
            QMessageBox.information(self, "成功", f"数据已导出到 {EXPORT_FILE}")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"导出失败: {str(e)}")

    def submit_entry(self):
        qq = self.qq_combo.currentText().strip()
        wechat = self.wechat_combo.currentText().strip()
        taobao = self.taobao_combo.currentText().strip()

        if not (qq or wechat or taobao):
            QMessageBox.warning(self, "错误", "至少提供一种联系方式")
            return

        # Join all contacts, including empty strings
        contacts = "$".join([qq, wechat, taobao])

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

        # If internal transaction checkbox is checked, add offsetting record
        if self.internal_checkbox.isChecked():
            offset_contacts = "内部交易$内部交易$内部交易"
            offset_amount = -amount
            offset_row = pl.DataFrame(
                {
                    "contacts": [offset_contacts],
                    "payment_method": ["（内部交易）"],
                    "details": [details],
                    "amount": [offset_amount],
                    "timestamp": [timestamp],
                },
                schema=SCHEMA,
            )
            self.df = pl.concat([self.df, offset_row], how="diagonal_relaxed")

        self.save_data()

        QMessageBox.information(self, "成功", "记账已提交")
        self.clear_entry_fields()

    def clear_entry_fields(self):
        self.qq_combo.clear()
        self.wechat_combo.clear()
        self.taobao_combo.clear()
        self.populate_contact_combos()

        self.details_entry.clear()
        self.amount_entry.setValue(0.0)
        self.payment_method.setCurrentIndex(0)
        self.internal_checkbox.setChecked(False)

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

    def populate_recent_table(self):
        if self.df.is_empty():
            self.recent_table.setRowCount(0)
            return

        recent_df = self.df.sort("timestamp", descending=True).head(50)
        self.recent_table.setRowCount(recent_df.height)
        for row_idx, row in enumerate(recent_df.iter_rows(named=True)):
            self.recent_table.setItem(row_idx, 0, QTableWidgetItem(row["contacts"]))
            self.recent_table.setItem(
                row_idx, 1, QTableWidgetItem(row["payment_method"])
            )
            self.recent_table.setItem(row_idx, 2, QTableWidgetItem(row["details"]))
            self.recent_table.setItem(
                row_idx, 3, QTableWidgetItem(f"{row['amount']:.2f}")
            )
            self.recent_table.setItem(
                row_idx,
                4,
                QTableWidgetItem(row["timestamp"].strftime("%Y-%m-%d %H:%M:%S")),
            )

        self.recent_table.resizeColumnsToContents()

    def populate_totals_table(self):
        if self.df.is_empty():
            self.totals_table.setRowCount(0)
            return

        totals_df = (
            self.df.group_by("payment_method")
            .agg(pl.col("amount").sum().alias("total"))
            .sort("payment_method")
        )

        self.totals_table.setRowCount(totals_df.height)
        for row_idx, row in enumerate(totals_df.iter_rows(named=True)):
            self.totals_table.setItem(
                row_idx, 0, QTableWidgetItem(row["payment_method"])
            )
            self.totals_table.setItem(
                row_idx, 1, QTableWidgetItem(f"{row['total']:.2f}")
            )

        self.totals_table.resizeColumnsToContents()

    def delete_selected_record(self):
        selected_row = self.recent_table.currentRow()
        if selected_row == -1:
            QMessageBox.warning(self, "错误", "请先选择一条记录")
            return

        contacts = self.recent_table.item(selected_row, 0).text()
        payment = self.recent_table.item(selected_row, 1).text()
        details = self.recent_table.item(selected_row, 2).text()
        ts_str = self.recent_table.item(selected_row, 4).text()

        print(f"deleting: {contacts} - {payment} - {ts_str} [{details or '-'}]")

        self.df = self.df.filter(
            ~(
                (pl.col("timestamp").dt.strftime("%Y-%m-%d %H:%M:%S") == ts_str)
                & (pl.col("contacts") == contacts)
                & (pl.col("payment_method") == payment)
                & (pl.col("details") == details)
            )
        )
        self.save_data()
        QMessageBox.information(self, "成功", "记录已删除")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = AccountingApp()
    window.show()
    sys.exit(app.exec())
