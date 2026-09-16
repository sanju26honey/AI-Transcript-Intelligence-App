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
        """Indexes all transcript segments into the ChromaDB vector database with Topic-Enriched Q+A Context."""
        if not all_segments:
            return

        documents = []
        metadatas = []
        ids = []

        topic_rules = [
            (['timeline', 'purchase', 'process', 'how long', 'duration', 'take', 'decision'], 'Purchase Decision Timeline Procurement Cycle Duration Months'),
            (['adoption', 'market status', 'describe', 'current'], 'Current Robotic Surgery Adoption Rate & Hospital Access'),
            (['barrier', 'hurdle', 'challenge', 'issue', 'problem'], 'Adoption Barriers Hurdles Capital Budget Approval Training'),
            (['economic', 'roi', 'financial', 'cost', 'pay for itself', 'price'], 'Financial ROI Total Cost of Ownership Economic Case'),
            (['training', 'surgeon', 'nurse', 'operational', 'staff'], 'Surgeon Training Operational Capacity Staffing Sustainability'),
            (['outlook', 'growth', 'expect', 'three to five', 'future'], 'Three to Five Year Procedure Growth Rate Outlook')
        ]

        # Group segments by transcript to find preceding interviewer questions
        segs_by_tx: Dict[str, List[TranscriptSegment]] = {}
        for seg in all_segments:
            segs_by_tx.setdefault(seg.transcript_id, []).append(seg)

        for tid, seg_list in segs_by_tx.items():
            for i in range(len(seg_list)):
                seg = seg_list[i]
                doc_id = f"{seg.transcript_id}_{seg.segment_index}"

                q_prompt = ""
                if i > 0 and seg_list[i-1].speaker.lower().startswith("interviewer"):
                    q_prompt = seg_list[i-1].text

                inferred_topic = "Robotic Surgery Intelligence"
                q_lower = q_prompt.lower()
                for keywords, topic_name in topic_rules:
                    if any(kw in q_lower for kw in keywords):
                        inferred_topic = topic_name
                        break

                doc_text = (
                    f"Project: European Robotic Surgery Market | Market: {seg.market} | "
                    f"Topic: {inferred_topic} | Question: {q_prompt} | "
                    f"Expert {seg.expert_name} ({seg.speaker}): [{seg.timestamp}] {seg.text}"
                )

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

    def query_segments_per_market(
        self,
        query: str,
        top_k_per_market: int = 1
    ) -> List[TranscriptSegment]:
        """Queries vector database per market to guarantee 100% equal market representation."""
        if not self.is_indexed:
            return []

        markets = list(set([s.market for s in self.segment_map.values()]))
        if not markets:
            return self.query_segments(query, top_k=top_k_per_market * 3)

        matched_segments = []
        seen_keys = set()

        for mkt in sorted(markets):
            results = self.collection.query(
                query_texts=[query],
                n_results=top_k_per_market,
                where={"market": mkt}
            )
            if results and "ids" in results and results["ids"]:
                for doc_id in results["ids"][0]:
                    if doc_id in self.segment_map and doc_id not in seen_keys:
                        seen_keys.add(doc_id)
                        matched_segments.append(self.segment_map[doc_id])

        return matched_segments
