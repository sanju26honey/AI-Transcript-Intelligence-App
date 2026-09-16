from typing import Dict, List, Optional
from models import ChatMessage, QuoteEvidence, TranscriptSegment
from services.rag_service import TranscriptRAGService
from services.llm_service import LLMService
from services.quote_verifier import verify_and_enrich_evidence

class ChatService:
    def __init__(self, rag_service: TranscriptRAGService, llm_service: LLMService):
        self.rag_service = rag_service
        self.llm_service = llm_service

    def _resolve_expert_segment(
        self,
        seg: TranscriptSegment,
        all_segments_by_transcript: Dict[str, List[TranscriptSegment]]
    ) -> TranscriptSegment:
        """If a retrieved segment is an Interviewer question, resolves it to the expert response segment immediately following it."""
        if not seg.speaker.lower().startswith("interviewer"):
            return seg

        transcript_segs = all_segments_by_transcript.get(seg.transcript_id, [])
        target_idx = seg.segment_index + 1

        for candidate in transcript_segs:
            if candidate.segment_index == target_idx and not candidate.speaker.lower().startswith("interviewer"):
                return candidate
            elif candidate.segment_index > seg.segment_index and not candidate.speaker.lower().startswith("interviewer"):
                return candidate

        return seg

    def answer_user_question(
        self,
        question: str,
        all_segments_by_transcript: Dict[str, List[TranscriptSegment]]
    ) -> ChatMessage:
        """Answers free-form user question across all transcripts using vector search (RAG)."""
        raw_retrieved = self.rag_service.query_segments_per_market(question, top_k_per_market=1)
        if not raw_retrieved:
            raw_retrieved = self.rag_service.query_segments(question, top_k=6)

        if not raw_retrieved:
            return ChatMessage(
                question=question,
                answer="No relevant information found across the expert call transcripts for your query.",
                evidence=[]
            )

        # Resolve any Interviewer questions to the actual Expert answer segment
        retrieved_segs: List[TranscriptSegment] = []
        seen_indices = set()

        for seg in raw_retrieved:
            resolved = self._resolve_expert_segment(seg, all_segments_by_transcript)
            key = f"{resolved.transcript_id}_{resolved.segment_index}"
            if key not in seen_indices:
                seen_indices.add(key)
                retrieved_segs.append(resolved)

        # Attempt LLM completion if available
        if self.llm_service.client:
            llm_result = self._generate_with_llm(question, retrieved_segs, all_segments_by_transcript)
            if llm_result:
                return llm_result

        # Fallback RAG response using top expert vector matches
        evidence_list = [
            QuoteEvidence(
                transcript_id=seg.transcript_id,
                expert_name=seg.expert_name,
                market=seg.market,
                quote=seg.text,
                timestamp=seg.timestamp,
                segment_index=seg.segment_index,
                speaker=seg.speaker
            ) for seg in retrieved_segs
        ]

        verified_ev = verify_and_enrich_evidence(evidence_list, all_segments_by_transcript)

        # Synthesize concise executive summary takeaway
        summary_statement = self._synthesize_fallback_summary(question, verified_ev)

        # Clean answer text: Executive Takeaway only (quotes follow as evidence cards below)
        answer_text = f"**Executive Takeaway:** {summary_statement}"

        return ChatMessage(
            question=question,
            answer=answer_text,
            evidence=verified_ev
        )

    def _synthesize_fallback_summary(self, question: str, evidence: List[QuoteEvidence]) -> str:
        """Synthesizes a concise executive summary based on the retrieved evidence."""
        if not evidence:
            return "Analysis across European markets indicates varying expert perspectives."

        markets_mentioned = list(set([ev.market for ev in evidence]))
        markets_str = ", ".join(markets_mentioned)
        first_text = evidence[0].quote[:150].strip()

        return f"Across {markets_str}, experts highlight key findings: {first_text}..."

    def _generate_with_llm(
        self,
        question: str,
        retrieved_segs: List[TranscriptSegment],
        all_segments_by_transcript: Dict[str, List[TranscriptSegment]]
    ) -> Optional[ChatMessage]:
        context_str = "\n".join([
            f"[{s.market} - {s.expert_name}] ({s.timestamp}, Segment {s.segment_index}) {s.speaker}: {s.text}"
            for s in retrieved_segs
        ])

        prompt = (
            f"User Question: {question}\n\n"
            f"Retrieved Expert Transcript Context:\n{context_str}\n\n"
            f"Synthesize a 1-2 sentence executive takeaway summary answering the user's question directly based on the expert statements."
        )

        schema = """
        {
          "question": "user question",
          "answer": "**Executive Takeaway:** Concise 1-2 sentence summary statement answering the question...",
          "evidence": [
            {
              "transcript_id": "Transcript_1_France",
              "expert_name": "Dr. Jean Martin",
              "market": "France",
              "quote": "Exact quote text",
              "timestamp": "01:20",
              "segment_index": 3,
              "speaker": "Dr. Martin"
            }
          ]
        }
        """

        json_data = self.llm_service.generate_json(prompt, schema)
        if not json_data or "answer" not in json_data:
            return None

        try:
            raw_ev = [QuoteEvidence(**ev) for ev in json_data.get("evidence", [])]
            verified_ev = verify_and_enrich_evidence(raw_ev, all_segments_by_transcript)

            return ChatMessage(
                question=question,
                answer=json_data["answer"],
                evidence=verified_ev
            )
        except Exception:
            return None
