import os
import sys

def run_tests():
    print("=== Testing Hasamex Pipeline Services ===")

    # 1. Test Transcript Parser
    from services.transcript_parser import parse_transcript_file
    fpath = "D:\\Hasamex Case Study\\Transcript_1_France.txt"
    if not os.path.exists(fpath):
        fpath = "Transcript_1_France.txt"

    meta, segs = parse_transcript_file(fpath)
    print(f"[OK] Parsed Transcript 1: {meta.expert_name} ({meta.market}), {len(segs)} segments.")
    assert len(segs) > 0, "No segments parsed!"

    # 2. Test Interview Guide Parser
    from services.guide_parser import parse_interview_guide
    gpath = "D:\\Hasamex Case Study\\Interview_Guide.txt"
    if not os.path.exists(gpath):
        gpath = "Interview_Guide.txt"

    questions = parse_interview_guide(gpath)
    print(f"[OK] Parsed Interview Guide: {len(questions)} questions found.")
    assert len(questions) == 6, f"Expected 6 questions, got {len(questions)}"

    # 3. Test Vector RAG Storage
    from services.rag_service import TranscriptRAGService
    rag = TranscriptRAGService()
    rag.index_transcripts(segs)
    res = rag.query_segments("barriers to adoption", top_k=3)
    print(f"[OK] Vector Search Test: Retrieved {len(res)} matching segments for 'barriers to adoption'.")
    assert len(res) > 0, "Vector search returned no results!"

    # 4. Test Quote Verifier
    from services.quote_verifier import verify_and_enrich_evidence
    from models import QuoteEvidence
    raw_ev = QuoteEvidence(
        transcript_id=meta.transcript_id,
        expert_name=meta.expert_name,
        market=meta.market,
        quote="capital budget approval",
        timestamp="00:00",
        segment_index=0
    )
    verified = verify_and_enrich_evidence([raw_ev], {meta.transcript_id: segs})
    print(f"[OK] Quote Verifier Test: Matched quote to segment index {verified[0].segment_index} ({verified[0].timestamp}).")
    assert verified[0].segment_index >= 0, "Quote verification failed!"

    print("=== ALL BACKEND PIPELINE TESTS PASSED SUCCESSFULY! ===")

if __name__ == "__main__":
    run_tests()
