"""Store and search vectors using PostgreSQL + pgvector."""
from typing import Any
import json
import psycopg
from .models import Chunk


class PgVectorStore:
    def __init__(self, database_url: str, dimensions: int) -> None:
        self.database_url = database_url
        self.dimensions = dimensions

    def get_connection(self):
        return psycopg.connect(self.database_url)

    def create_schema(self) -> None:
        """Create extension and chunks table with vector column and metadata."""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
                cur.execute(f"""
                    CREATE TABLE IF NOT EXISTS chunks (
                        id BIGSERIAL PRIMARY KEY,
                        strategy VARCHAR(32) NOT NULL,
                        chunk_id VARCHAR(128) NOT NULL,
                        document_id VARCHAR(128) NOT NULL,
                        source VARCHAR(256) NOT NULL,
                        page INTEGER NOT NULL,
                        section VARCHAR(64),
                        text TEXT NOT NULL,
                        metadata JSONB NOT NULL DEFAULT '{{}}'::jsonb,
                        embedding vector({self.dimensions}) NOT NULL,
                        CONSTRAINT uq_strategy_chunk UNIQUE (strategy, chunk_id)
                    );
                """)
                cur.execute("CREATE INDEX IF NOT EXISTS idx_chunks_strat ON chunks(strategy);")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_chunks_sect ON chunks(section);")
            conn.commit()

    def upsert(self, strategy: str, chunks: list[Chunk], vectors: list[list[float]]) -> None:
        """Idempotently store chunks and their embeddings for a given strategy.
        
        Deletes existing chunks for this strategy first, ensuring re-ingestion
        does not produce duplicates and cleans out obsolete chunks.
        """
        if len(chunks) != len(vectors):
            raise ValueError(f"Chunk count ({len(chunks)}) does not match vector count ({len(vectors)})")

        with self.get_connection() as conn:
            with conn.cursor() as cur:
                # Idempotent cleanup: remove existing chunks for this strategy
                cur.execute("DELETE FROM chunks WHERE strategy = %s;", (strategy,))
                
                # Batch insert
                query = f"""
                    INSERT INTO chunks (
                        strategy, chunk_id, document_id, source, page, section, text, metadata, embedding
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s::vector
                    );
                """
                batch_data = []
                for c, v in zip(chunks, vectors):
                    sec = c.metadata.get("section", "")
                    meta_json = json.dumps(c.metadata, ensure_ascii=False)
                    vec_str = "[" + ",".join(str(x) for x in v) + "]"
                    batch_data.append((
                        strategy, c.chunk_id, c.document_id, c.source, c.page, sec, c.text, meta_json, vec_str
                    ))
                
                cur.executemany(query, batch_data)
            conn.commit()

    def search(
        self,
        strategy: str,
        query_vector: list[float],
        top_k: int = 3,
        filters: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        """Filter metadata in SQL, rank by cosine distance, and return top-k."""
        vec_str = "[" + ",".join(str(x) for x in query_vector) + "]"
        
        conditions = ["strategy = %s"]
        params: list[Any] = [strategy]
        
        # Apply metadata filters if provided
        if filters:
            for k, val in filters.items():
                if k == "section":
                    conditions.append("section = %s")
                    params.append(val)
                else:
                    # JSONB metadata filter
                    conditions.append(f"metadata->>%s = %s")
                    params.extend([k, str(val)])
                    
        where_clause = " AND ".join(conditions)
        sql = f"""
            SELECT
                chunk_id,
                document_id,
                source,
                page,
                section,
                text,
                metadata,
                (embedding <=> %s::vector) AS distance
            FROM chunks
            WHERE {where_clause}
            ORDER BY distance ASC
            LIMIT %s;
        """
        params_with_vec = [vec_str] + params + [top_k]
        
        # Reconstruct correct parameter order: embedding is in SELECT
        # Query: SELECT ... (embedding <=> %s::vector) AS distance WHERE ... ORDER BY distance ASC LIMIT %s
        sql = f"""
            SELECT
                chunk_id,
                document_id,
                source,
                page,
                section,
                text,
                metadata,
                (embedding <=> %s::vector) AS distance
            FROM chunks
            WHERE {where_clause}
            ORDER BY embedding <=> %s::vector ASC
            LIMIT %s;
        """
        full_params = [vec_str] + params + [vec_str, top_k]
        
        results: list[dict[str, Any]] = []
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, full_params)
                rows = cur.fetchall()
                for r in rows:
                    distance = float(r[7])
                    # Cosine similarity for normalized vectors is 1 - distance
                    score = round(1.0 - distance, 4)
                    results.append({
                        "chunk_id": r[0],
                        "document_id": r[1],
                        "source": r[2],
                        "page": r[3],
                        "section": r[4],
                        "text": r[5],
                        "metadata": r[6],
                        "score": score,
                        "distance": round(distance, 4)
                    })
        return results
