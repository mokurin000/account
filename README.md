## TODO

- 付款方式栏/银行卡这个条目改成（内部交易）
- 这个导出为xlsx 能不能设置 导出数据的时间段
- 能根据填写信息自动生成一段可以复制的文本吗
- 除了查询功能 还能搞个分块显示下 最近十几二十条输入的信息
  - 并且能在这个框里面删除 输入错误的信息

## Bundle binary

```bash
uv run pyinstaller -w --onedir --collect-binaries polars --optimize 2 account.py
```