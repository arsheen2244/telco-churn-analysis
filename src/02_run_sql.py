"""Step 2: load the cleaned CSV into SQLite and run every query in sql/queries.sql.

Usage: python -I src/02_run_sql.py data/telco_clean.csv sql/queries.sql outputs
"""
import re
import sqlite3
import sys
from pathlib import Path

import pandas as pd

csv_path, sql_path, out_dir = sys.argv[1], sys.argv[2], Path(sys.argv[3])
out_dir.mkdir(exist_ok=True)

conn = sqlite3.connect(":memory:")
pd.read_csv(csv_path).to_sql("customers", conn, index=False)

text = Path(sql_path).read_text()
# Split on the '-- Qn:' headers; each block is one query
blocks = re.split(r"^-- (Q\d+): (.*)$", text, flags=re.MULTILINE)
# blocks = [preamble, 'Q1', 'title', body, 'Q2', 'title', body, ...]
for i in range(1, len(blocks), 3):
    qid, title, body = blocks[i], blocks[i + 1], blocks[i + 2]
    body = "\n".join(l for l in body.splitlines() if not l.strip().startswith("--")).strip()
    result = pd.read_sql_query(body, conn)
    result.to_csv(out_dir / f"sql_{qid.lower()}.csv", index=False)
    print(f"\n{qid}: {title}")
    print(result.to_string(index=False))
