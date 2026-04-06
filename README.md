# Speech to SQL

A CLI tool that converts natural language (Polish and English) into PostgreSQL queries using a multi-agent LLM system enhanced with RAG (PostgreSQL documentation).

## Requirements

- Docker
- A running PostgreSQL instance
- An API key for [OpenRouter](https://openrouter.ai) (or any OpenAI-compatible API)

## Setup

1. Copy `.env_example` to `.env` and fill in your values:

```env
# Use localhost when running without Docker
# Use host.docker.internal when running via Docker (Windows/Mac)
DB_HOST=host.docker.internal
DB_PORT=5432
DB_NAME=your_database
DB_USER=your_user
DB_PASSWORD=your_password

LLM_API_KEY=your_api_key
LLM_MODEL=any/model-name
LLM_BASE_URL=https://openrouter.ai/api/v1
```

Any model available on OpenRouter (or any OpenAI-compatible API) can be used — free and paid options are supported.

2. Build the RAG index from PostgreSQL documentation (one-time setup):

```bash
docker-compose run build-index
```

3. Run the app:

```bash
docker-compose run app
```

## Usage

The app automatically classifies your intent — queries retrieve data, mutations modify it.

```
Speech to SQL
Ask a question in Polish or English. Commands: 'print history', 'export history', 'exit'.

Question: show employees earning more than 5000
Question: pracownicy zatrudnieni po 2021 roku
Question: which department has the highest average salary
Question: znajdź 3 klientów którzy wydali najwięcej w każdym mieście
Question: add 5 employees
Question: utwórz 3 produkty z kategorii Electronics
```

When a query returns no results, the app will ask if you want to generate sample data:

```
No results found. Add sample data? [y/N]: y
How many rows? 5
Inserted 5 rows.
```

Mutation queries always require confirmation before execution:

```
Execute? [y/N]: y
Done. 3 rows affected.
```

### Commands

| Command | Description |
|---------|-------------|
| `history` / `print history` | Show all queries from the current session |
| `export` / `export history` | Save session history to `history/` as JSON |
| `exit` / `quit` | Exit the app |

## Running without Docker

```bash
pip install -r requirements.txt
python -m src.rag.build_index  # one-time setup
python src/main.py
```

## Running tests

```bash
docker-compose run test
```

Or locally:

```bash
python -m pytest tests/ -v
```

## Architecture

The system uses a multi-agent pipeline:

- **Pipeline** — orchestrates the full flow: intent classification → agent selection → result handling
- **Orchestrator** — classifies user intent (query vs mutation) using an LLM call
- **Query Agent** — generates and executes SELECT queries with RAG support
- **Mutation Agent** — generates INSERT/UPDATE/DELETE with user confirmation and RAG support
- **Database** — handles PostgreSQL connections, schema fetching (cached), query and mutation execution
- **RAG (DocumentRetriever)** — retrieves relevant PostgreSQL documentation chunks to improve SQL generation

## Tech stack

- Python 3.11
- [openai](https://github.com/openai/openai-python) SDK (OpenAI-compatible, works with OpenRouter)
- psycopg2 — PostgreSQL driver
- python-dotenv — configuration
- chromadb — vector database for RAG
- sentence-transformers — embeddings for RAG
- pdfplumber / pikepdf — PDF processing
- pytest — tests