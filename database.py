import psycopg2
import psycopg2.extras
import config

_schema_cache = None


def get_connection():
    return psycopg2.connect(
        host=config.DB_HOST,
        port=config.DB_PORT,
        dbname=config.DB_NAME,
        user=config.DB_USER,
        password=config.DB_PASSWORD,
    )


def get_schema() -> str:
    global _schema_cache
    if _schema_cache:
        return _schema_cache

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    c.table_name,
                    c.column_name,
                    c.data_type,
                    c.is_nullable,
                    tc.constraint_type
                FROM information_schema.columns c
                LEFT JOIN information_schema.key_column_usage kcu
                    ON c.table_name = kcu.table_name
                    AND c.column_name = kcu.column_name
                    AND c.table_schema = kcu.table_schema
                LEFT JOIN information_schema.table_constraints tc
                    ON kcu.constraint_name = tc.constraint_name
                    AND kcu.table_schema = tc.table_schema
                WHERE c.table_schema = 'public'
                ORDER BY c.table_name, c.ordinal_position
            """)
            rows = cur.fetchall()
    finally:
        conn.close()

    tables = {}
    for table, column, dtype, nullable, constraint in rows:
        if table not in tables:
            tables[table] = []
        flags = []
        if constraint == "PRIMARY KEY":
            flags.append("PK")
        if constraint == "FOREIGN KEY":
            flags.append("FK")
        if nullable == "NO" and constraint != "PRIMARY KEY":
            flags.append("NOT NULL")
        flag_str = f" [{', '.join(flags)}]" if flags else ""
        tables[table].append(f"  {column} ({dtype}){flag_str}")

    lines = []
    for table, columns in tables.items():
        lines.append(f"Table: {table}")
        lines.extend(columns)
        lines.append("")

    _schema_cache = "\n".join(lines)
    return _schema_cache


def execute_query(sql: str) -> tuple[list, list]:
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql)
            rows = cur.fetchall()
            columns = [desc[0] for desc in cur.description]
            return columns, [dict(row) for row in rows]
    finally:
        conn.close()


def execute_select(sql: str) -> tuple[list, list]:
    if not sql.strip().upper().startswith("SELECT"):
        raise ValueError("Only SELECT statements are allowed")
    return execute_query(sql)
