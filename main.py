import config
import agent
import database
import psycopg2
import openai
import json
import os
from datetime import datetime


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


def export_history(history: list):
    if not history:
        print("(no history to export)\n")
        return
    os.makedirs("history", exist_ok=True)
    filename = f"history/{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.json"
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2, default=str)
    print(f"Exported to {filename}\n")


def print_history(history: list):
    if not history:
        print("(no history)\n")
        return
    for i, entry in enumerate(history, 1):
        print(f"[{i}] {entry['question']}")
        print(f"    SQL: {entry['sql']}")
        print_results(entry['columns'], entry['rows'])
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

        print("\nGenerating SQL query...")
        try:
            sql = agent.ask(question)
        except openai.APIConnectionError:
            print("Error: Cannot connect to LLM API. Check your internet connection.\n")
            continue
        except openai.AuthenticationError:
            print("Error: Invalid LLM API key. Check LLM_API_KEY in .env.\n")
            continue
        except openai.APIError as e:
            print(f"Error: LLM API error: {e}\n")
            continue

        if sql.startswith("ERROR:"):
            print(f"Agent: {sql}\n")
            continue

        print(f"\nSQL:\n{sql}\n")

        print("Executing query...")
        try:
            columns, rows = database.execute_select(sql)
            print("\nResults:")
            print_results(columns, rows)
            history.append({"question": question, "sql": sql, "columns": columns, "rows": rows})
        except psycopg2.OperationalError:
            print("Error: Cannot connect to database. Check your connection settings in .env.\n")
            continue
        except psycopg2.Error as e:
            print(f"Error: Invalid SQL query: {e}\n")
            continue
        except ValueError as e:
            print(f"Error: {e}\n")
            continue

        print()


if __name__ == "__main__":
    main()
