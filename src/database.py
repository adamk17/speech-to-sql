import psycopg2
import psycopg2.extras


class Database:
    def __init__(self, host: str, port: str, dbname: str, user: str, password: str):
        self._host = host
        self._port = port
        self._dbname = dbname
        self._user = user
        self._password = password
        self._schema_cache: str | None = None

    def _get_connection(self):
        return psycopg2.connect(
            host=self._host,
            port=self._port,
            dbname=self._dbname,
            user=self._user,
            password=self._password,
        )

    def get_schema(self) -> str:
        if self._schema_cache is not None:
            return self._schema_cache

        conn = self._get_connection()
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

        self._schema_cache = "\n".join(lines)
        return self._schema_cache

    def execute_select(self, sql: str) -> tuple[list, list]:
        first_word = sql.strip().upper().split()[0]
        if first_word not in ("SELECT", "WITH"):
            raise ValueError("Only SELECT statements are allowed")
        conn = self._get_connection()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(sql)
                rows = cur.fetchall()
                columns = [desc[0] for desc in cur.description]
                return columns, [dict(row) for row in rows]
        finally:
            conn.close()

    def execute_mutation(self, sql: str) -> int:
        first_word = sql.strip().upper().split()[0]
        if first_word not in ("INSERT", "UPDATE", "DELETE"):
            raise ValueError("Only INSERT, UPDATE, DELETE statements are allowed")
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(sql)
                conn.commit()
                return cur.rowcount
        finally:
            conn.close()