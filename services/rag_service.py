from typing import List, Dict, Optional
import chromadb
from chromadb.config import Settings
from models import TranscriptSegment

class TranscriptRAGService:
    def __init__(self):
        # Initialize in-memory ChromaDB vector collection
        self.client = chromadb.Client(Settings(anonymized_telemetry=False, is_persistent=False))
        self.collection = self.client.get_or_create_collection(name="hasamex_transcripts")
        self.segment_map: Dict[str, TranscriptSegment] = {}
        self.is_indexed = False

    def index_transcripts(self, all_segments: List[TranscriptSegment]):
        """Indexes all transcript segments into the ChromaDB vector database."""
        if not all_segments:
            return

        documents = []
        metadatas = []
        ids = []

        for seg in all_segments:
            doc_id = f"{seg.transcript_id}_{seg.segment_index}"
            doc_text = f"Market: {seg.market} | Expert: {seg.expert_name} ({seg.speaker}) | [{seg.timestamp}]: {seg.text}"
            
            documents.append(doc_text)
            metadatas.append({
                "transcript_id": seg.transcript_id,
                "expert_name": seg.expert_name,
                "market": seg.market,
                "timestamp": seg.timestamp,
                "segment_index": seg.segment_index,
                "speaker": seg.speaker,
                "start_seconds": seg.start_seconds
            })
            ids.append(doc_id)
            self.segment_map[doc_id] = seg

        # Add to Chroma collection
        self.collection.add(
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )
        self.is_indexed = True

    def query_segments(
        self,
        query: str,
        top_k: int = 5,
        market_filter: Optional[str] = None
    ) -> List[TranscriptSegment]:
        """Queries the vector database for relevant transcript segments."""
        if not self.is_indexed:
            return []

        where_clause = {}
        if market_filter:
            where_clause = {"market": market_filter}

        results = self.collection.query(
            query_texts=[query],
            n_results=top_k,
            where=where_clause if where_clause else None
        )

        matched_segments = []
        if results and "ids" in results and results["ids"]:
            matched_ids = results["ids"][0]
            for doc_id in matched_ids:
                if doc_id in self.segment_map:
                    matched_segments.append(self.segment_map[doc_id])

        return matched_segments
