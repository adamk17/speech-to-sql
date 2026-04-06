import json
import os
from datetime import datetime

import config
from database import Database
from pipeline import Pipeline, PipelineResult


def print_results(columns: list, rows: list):
    if not rows:
        print("(no results)")
        return
    col_widths = {col: len(col) for col in columns}
    for row in rows:
        for col in columns:
            col_widths[col] = max(col_widths[col], len(str(row[col])))

    header = " | ".join(col.ljust(col_widths[col]) for col in columns)
    separator = "-+-".join("-" * col_widths[col] for col in columns)
    print(header)
    print(separator)
    for row in rows:
        print(" | ".join(str(row[col]).ljust(col_widths[col]) for col in columns))
    print(f"\n({len(rows)} {'row' if len(rows) == 1 else 'rows'})")


def print_history(history: list):
    if not history:
        print("(no history)\n")
        return
    for i, entry in enumerate(history, 1):
        print(f"[{i}] {entry['question']}")
        print(f"    SQL: {entry['sql']}")
        print_results(entry['columns'], entry['rows'])
        print()


def export_history(history: list):
    if not history:
        print("(no history to export)\n")
        return
    os.makedirs("history", exist_ok=True)
    filename = f"history/{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.json"
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2, default=str)
    print(f"Exported to {filename}\n")


def display_result(result: PipelineResult):
    if result.sql:
        print(f"\nSQL:\n{result.sql}\n")
    if result.columns and result.rows:
        print("Results:")
        print_results(result.columns, result.rows)
    if result.message:
        print(result.message)
    print()


def main():
    print("Speech to SQL")
    print("Ask a question in Polish or English. Commands: 'print history', 'export history', 'exit'.\n")
    history = []

    try:
        config.validate()
    except ValueError as e:
        print(f"Configuration error: {e}")
        return

    db = Database(
        host=config.DB_HOST,
        port=config.DB_PORT,
        dbname=config.DB_NAME,
        user=config.DB_USER,
        password=config.DB_PASSWORD,
    )
    pipeline = Pipeline(db=db)

    while True:
        try:
            question = input("Question: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if not question:
            continue
        if question.lower() in ("print history", "history"):
            print_history(history)
            continue
        if question.lower() in ("export history", "export"):
            export_history(history)
            continue
        if question.lower() in ("exit", "quit"):
            print("Goodbye!")
            break

        try:
            result = pipeline.run(question)
        except Exception as e:
            print(f"Error: {e}\n")
            continue

        display_result(result)

        if result.columns and result.rows:
            history.append({
                "question": question,
                "sql": result.sql,
                "columns": result.columns,
                "rows": result.rows,
            })


if __name__ == "__main__":
    main()