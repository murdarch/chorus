"""Memory system with vector search for Chorus bots."""

import asyncio
import json
import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import numpy as np
from sentence_transformers import SentenceTransformer

from src.llm_client import get_llm_client

logger = logging.getLogger(__name__)


class MemorySystem:
    """Manages bot memories with vector similarity search."""

    def __init__(self, db_path: str, bot_name: str, model_name: str):
        """Initialize the memory system.

        Args:
            db_path: Path to SQLite database file
            bot_name: Name of the bot (for LLM context)
            model_name: LLM model name (for memory extraction)
        """
        self.db_path = db_path
        self.bot_name = bot_name
        self.model_name = model_name
        self.llm_client = get_llm_client()

        # Ensure database directory exists
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

        # Initialize embedding model
        logger.info(f"Loading sentence-transformers model: all-MiniLM-L6-v2")
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        self.embedding_dim = 384  # Dimension for all-MiniLM-L6-v2

        # Initialize database
        self._init_database()

        logger.info(f"Initialized memory system for {bot_name} at {db_path}")

    def _init_database(self):
        """Initialize the SQLite database with schema."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Create memories table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT NOT NULL,
                memory_type TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                confidence REAL DEFAULT 1.0,
                embedding BLOB,
                metadata TEXT
            )
        """)

        # Load sqlite-vss extension and create virtual table
        try:
            # Enable extension loading
            conn.enable_load_extension(True)

            # Use sqlite_vss.load() helper which handles the loading properly
            import sqlite_vss
            sqlite_vss.load(conn)
            logger.info("Loaded sqlite-vss extension successfully")

            # Create VSS virtual table for vector similarity search
            cursor.execute(f"""
                CREATE VIRTUAL TABLE IF NOT EXISTS vss_memories USING vss0(
                    embedding({self.embedding_dim})
                )
            """)
            logger.info("VSS virtual table created successfully")

        except Exception as e:
            logger.warning(f"VSS setup failed (vector search will use fallback): {e}")

        conn.commit()
        conn.close()

    def _generate_embedding(self, text: str) -> np.ndarray:
        """Generate embedding vector for text.

        Args:
            text: Text to embed

        Returns:
            Embedding vector as numpy array
        """
        try:
            embedding = self.embedding_model.encode(text, convert_to_numpy=True)
            return embedding
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            # Return zero vector as fallback
            return np.zeros(self.embedding_dim)

    def _serialize_embedding(self, embedding: np.ndarray) -> bytes:
        """Serialize embedding to bytes for storage.

        Args:
            embedding: Numpy array embedding

        Returns:
            Serialized bytes
        """
        return embedding.astype(np.float32).tobytes()

    def _deserialize_embedding(self, data: bytes) -> np.ndarray:
        """Deserialize embedding from bytes.

        Args:
            data: Serialized embedding bytes

        Returns:
            Numpy array embedding
        """
        return np.frombuffer(data, dtype=np.float32)

    async def store_memory(
        self,
        content: str,
        memory_type: str = "general",
        confidence: float = 1.0,
        metadata: Optional[Dict] = None,
    ) -> int:
        """Store a memory with vector embedding.

        Args:
            content: Memory content
            memory_type: Type of memory (fact, impression, decision, context)
            confidence: Confidence score (0.0-1.0)
            metadata: Optional metadata dictionary

        Returns:
            Memory ID
        """
        try:
            # Generate embedding asynchronously to avoid blocking
            loop = asyncio.get_event_loop()
            embedding = await loop.run_in_executor(
                None, self._generate_embedding, content
            )

            # Serialize embedding
            embedding_blob = self._serialize_embedding(embedding)

            # Serialize metadata
            metadata_json = json.dumps(metadata) if metadata else None

            # Store in database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO memories (content, memory_type, confidence, embedding, metadata)
                VALUES (?, ?, ?, ?, ?)
            """, (content, memory_type, confidence, embedding_blob, metadata_json))

            memory_id = cursor.lastrowid

            # Try to add to VSS index
            try:
                cursor.execute("""
                    INSERT INTO vss_memories(rowid, embedding)
                    VALUES (?, ?)
                """, (memory_id, embedding_blob))
            except Exception as e:
                logger.debug(f"VSS insert failed (will use fallback search): {e}")

            conn.commit()
            conn.close()

            logger.info(
                f"Stored memory #{memory_id} ({memory_type}): {content[:50]}..."
            )

            return memory_id

        except Exception as e:
            logger.error(f"Error storing memory: {e}", exc_info=True)
            return -1

    async def search_memories(
        self,
        query: str,
        limit: int = 5,
        memory_type: Optional[str] = None,
    ) -> List[Dict]:
        """Search memories using vector similarity.

        Args:
            query: Search query text
            limit: Maximum number of results
            memory_type: Optional filter by memory type

        Returns:
            List of memory dictionaries with similarity scores
        """
        try:
            # Generate query embedding
            loop = asyncio.get_event_loop()
            query_embedding = await loop.run_in_executor(
                None, self._generate_embedding, query
            )

            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Try VSS search first
            try:
                type_filter = f"AND memory_type = '{memory_type}'" if memory_type else ""

                # Join with memories table to get full data
                cursor.execute(f"""
                    SELECT
                        m.id, m.content, m.memory_type, m.timestamp,
                        m.confidence, m.metadata,
                        vss.distance
                    FROM vss_memories vss
                    JOIN memories m ON vss.rowid = m.id
                    WHERE vss_search(vss.embedding, ?)
                    {type_filter}
                    ORDER BY vss.distance
                    LIMIT ?
                """, (self._serialize_embedding(query_embedding), limit))

                results = cursor.fetchall()

            except Exception as e:
                logger.debug(f"VSS search failed, using fallback: {e}")
                # Fallback: compute similarity manually
                type_filter = f"WHERE memory_type = '{memory_type}'" if memory_type else ""
                cursor.execute(f"""
                    SELECT id, content, memory_type, timestamp, confidence, embedding, metadata
                    FROM memories
                    {type_filter}
                """)

                all_memories = cursor.fetchall()

                # Calculate similarities
                scored_memories = []
                for mem in all_memories:
                    mem_id, content, mem_type, timestamp, confidence, embedding_blob, metadata = mem
                    mem_embedding = self._deserialize_embedding(embedding_blob)
                    similarity = np.dot(query_embedding, mem_embedding) / (
                        np.linalg.norm(query_embedding) * np.linalg.norm(mem_embedding) + 1e-8
                    )
                    # Convert similarity to distance (lower is better)
                    distance = 1.0 - similarity
                    scored_memories.append((mem_id, content, mem_type, timestamp, confidence, metadata, distance))

                # Sort by distance and take top N
                scored_memories.sort(key=lambda x: x[6])
                results = scored_memories[:limit]

            conn.close()

            # Format results
            memories = []
            for row in results:
                memory = {
                    "id": row[0],
                    "content": row[1],
                    "memory_type": row[2],
                    "timestamp": row[3],
                    "confidence": row[4],
                    "metadata": json.loads(row[5]) if row[5] else None,
                    "similarity_distance": row[6] if len(row) > 6 else None,
                }
                memories.append(memory)

            logger.info(f"Found {len(memories)} relevant memories for query: {query[:50]}...")
            return memories

        except Exception as e:
            logger.error(f"Error searching memories: {e}", exc_info=True)
            return []

    async def process_for_memories(
        self,
        conversation_history: List[Dict[str, str]],
        current_response: str,
    ) -> List[str]:
        """Extract important information from conversation to store as memories.

        Args:
            conversation_history: Recent conversation history
            current_response: Bot's current response

        Returns:
            List of memory contents to store
        """
        try:
            # Build context from conversation
            context_lines = []
            for msg in conversation_history[-5:]:
                context_lines.append(f"{msg['sender']}: {msg['text']}")
            context_lines.append(f"{self.bot_name}: {current_response}")
            context = "\n".join(context_lines)

            # Ask LLM to extract memorable information
            system_prompt = f"""You are {self.bot_name}, analyzing a conversation to extract important information to remember.

Extract key facts, decisions, preferences, or context that would be useful to remember for future conversations.

For each piece of information, provide:
1. A clear, standalone statement
2. The type: fact, impression, decision, or context

Respond in JSON format:
[
  {{"content": "User prefers Python over JavaScript", "type": "preference"}},
  {{"content": "Team is building a web scraper for news", "type": "fact"}}
]

If there's nothing important to remember, respond with an empty array: []"""

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Recent conversation:\n{context}\n\nWhat should I remember?"},
            ]

            response = await self.llm_client.get_completion(
                model=self.model_name,
                messages=messages,
                temperature=0.3,
                max_tokens=500,
            )

            if response:
                # Parse JSON response
                try:
                    # Extract JSON from response (might have markdown code blocks)
                    json_str = response.strip()
                    if json_str.startswith("```"):
                        json_str = json_str.split("```")[1]
                        if json_str.startswith("json"):
                            json_str = json_str[4:]
                    json_str = json_str.strip()

                    memories_data = json.loads(json_str)

                    # Store each memory
                    memory_ids = []
                    for mem_data in memories_data:
                        memory_id = await self.store_memory(
                            content=mem_data.get("content", ""),
                            memory_type=mem_data.get("type", "general"),
                            confidence=0.8,
                        )
                        memory_ids.append(memory_id)

                    logger.info(f"Extracted and stored {len(memory_ids)} memories")
                    return [mem["content"] for mem in memories_data]

                except json.JSONDecodeError as e:
                    logger.warning(f"Failed to parse memories JSON: {e}")
                    logger.debug(f"Response was: {response}")
                    return []

            return []

        except Exception as e:
            logger.error(f"Error processing memories: {e}", exc_info=True)
            return []

    def get_all_memories(self, limit: int = 100) -> List[Dict]:
        """Get all memories (for debugging/testing).

        Args:
            limit: Maximum number of memories to return

        Returns:
            List of memory dictionaries
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                SELECT id, content, memory_type, timestamp, confidence, metadata
                FROM memories
                ORDER BY timestamp DESC
                LIMIT ?
            """, (limit,))

            results = cursor.fetchall()
            conn.close()

            memories = []
            for row in results:
                memory = {
                    "id": row[0],
                    "content": row[1],
                    "memory_type": row[2],
                    "timestamp": row[3],
                    "confidence": row[4],
                    "metadata": json.loads(row[5]) if row[5] else None,
                }
                memories.append(memory)

            return memories

        except Exception as e:
            logger.error(f"Error getting memories: {e}", exc_info=True)
            return []
