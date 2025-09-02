## TODO

- 除了查询功能 还能搞个分块显示下 最近十几二十条输入的信息
  - 并且能在这个框里面删除 输入错误的信息

## Bundle binary

```bash
uv run pyinstaller -w --onedir --collect-binaries polars --optimize 2 account.py
```