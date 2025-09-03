# Account

Qt6 based account software, designed for Chinese businessman.

Now with Xeon v2 processor support! (thanks to polars-lts-cpu)

## Bundle as binary

```bash
uv pip install pyinstaller
uv run pyinstaller -w --onedir --collect-binaries polars --optimize 2 account.py
```