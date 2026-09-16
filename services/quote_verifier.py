import difflib
from typing import List, Dict, Optional
from models import QuoteEvidence, TranscriptSegment

def find_best_matching_segment(
    quote_text: str,
    segments: List[TranscriptSegment]
) -> Optional[TranscriptSegment]:
    """Finds the best matching TranscriptSegment for a given quote snippet."""
    if not segments or not quote_text:
        return None

    clean_quote = quote_text.lower().strip()
    best_segment = None
    best_score = 0.0

    for seg in segments:
        seg_text = seg.text.lower().strip()
        # Direct substring check
        if clean_quote in seg_text:
            return seg

        # Fuzzy sequence matcher
        matcher = difflib.SequenceMatcher(None, clean_quote, seg_text)
        score = matcher.ratio()

        # Word overlap score boost
        quote_words = set(clean_quote.split())
        seg_words = set(seg_text.split())
        overlap = len(quote_words.intersection(seg_words)) / max(len(quote_words), 1)

        combined_score = (score * 0.5) + (overlap * 0.5)

        if combined_score > best_score:
            best_score = combined_score
            best_segment = seg

    # Require minimum confidence threshold
    if best_score >= 0.35:
        return best_segment

    return None

def verify_and_enrich_evidence(
    evidence_list: List[QuoteEvidence],
    all_segments_by_transcript: Dict[str, List[TranscriptSegment]]
) -> List[QuoteEvidence]:
    """Verifies and enriches LLM-generated QuoteEvidence items with exact segment metadata."""
    verified_list: List[QuoteEvidence] = []

    for ev in evidence_list:
        segments = all_segments_by_transcript.get(ev.transcript_id, [])
        if not segments:
            verified_list.append(ev)
            continue

        # Check if segment_index is valid and matches
        matched_seg = None
        if 0 <= ev.segment_index < len(segments):
            seg_candidate = segments[ev.segment_index]
            if ev.quote.lower().strip() in seg_candidate.text.lower().strip():
                matched_seg = seg_candidate

        # Fallback to fuzzy search across all segments of the transcript
        if not matched_seg:
            matched_seg = find_best_matching_segment(ev.quote, segments)

        if matched_seg:
            verified_list.append(QuoteEvidence(
                transcript_id=matched_seg.transcript_id,
                expert_name=matched_seg.expert_name,
                market=matched_seg.market,
                quote=ev.quote if len(ev.quote) > 10 else matched_seg.text[:120],
                timestamp=matched_seg.timestamp,
                segment_index=matched_seg.segment_index,
                speaker=matched_seg.speaker
            ))
        else:
            verified_list.append(ev)

    return verified_list
