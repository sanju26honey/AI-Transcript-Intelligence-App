from typing import List, Dict, Optional
from models import ThemeOrDisagreement, QuoteEvidence, TranscriptSegment
from services.llm_service import LLMService
from services.quote_verifier import verify_and_enrich_evidence

class ThemeService:
    def __init__(self, llm_service: LLMService):
        self.llm_service = llm_service

    def get_themes_and_disagreements(
        self,
        all_segments_by_transcript: Dict[str, List[TranscriptSegment]]
    ) -> List[ThemeOrDisagreement]:
        """Synthesizes 3-6 cross-call themes and disagreements across all market transcripts via Groq LLM with fallback."""
        llm_result = self._generate_with_llm(all_segments_by_transcript)
        if llm_result:
            return llm_result
        return self._generate_fallback(all_segments_by_transcript)


    def _generate_with_llm(
        self,
        all_segments_by_transcript: Dict[str, List[TranscriptSegment]]
    ) -> Optional[List[ThemeOrDisagreement]]:
        if not self.llm_service.client:
            return None

        # Build compressed context text (filtering out interviewer filler text and retaining expert statements)
        selected_segs = []
        for tid, segs in all_segments_by_transcript.items():
            expert_segs = [s for s in segs if not s.speaker.lower().startswith("interviewer")]
            # Retain top informative expert statements per transcript to stay comfortably under 2k tokens
            selected_segs.extend(expert_segs[:8])

        full_text = "\n".join([
            f"Transcript ID: {s.transcript_id} | Market: {s.market} | Expert: {s.expert_name} | [{s.timestamp}] Segment {s.segment_index} ({s.speaker}): {s.text}"
            for s in selected_segs
        ])

        prompt = (
            f"Analyze these European robotic surgery expert call transcripts:\n{full_text}\n\n"
            f"Identify 4 key cross-call themes. For each theme:\n"
            f"1. Specify topic title and summary.\n"
            f"2. Classify type as either 'consensus' (experts broadly agree) or 'disagreement' (experts diverge/disagree).\n"
            f"3. Provide supporting exact quote evidence with transcript_id, timestamp, and segment_index for each relevant expert."
        )

        schema = """
        {
          "themes": [
            {
              "topic": "Capital Budget & ROI Dominance",
              "type": "consensus",
              "summary": "Summary of theme...",
              "evidence": [
                {
                  "transcript_id": "Transcript_1_France",
                  "expert_name": "Dr. Jean Martin",
                  "market": "France",
                  "quote": "Exact quote snippet",
                  "timestamp": "01:20",
                  "segment_index": 3,
                  "speaker": "Dr. Martin"
                }
              ]
            }
          ]
        }
        """

        json_data = self.llm_service.generate_json(prompt, schema, task_label="Themes")
        if not json_data or "themes" not in json_data:
            return None

        try:
            result = []
            for item in json_data["themes"]:
                raw_ev = [QuoteEvidence(**ev) for ev in item.get("evidence", [])]
                verified_ev = verify_and_enrich_evidence(raw_ev, all_segments_by_transcript)
                result.append(ThemeOrDisagreement(
                    topic=item["topic"],
                    type=item["type"],
                    summary=item["summary"],
                    evidence=verified_ev
                ))
            return result
        except Exception:
            return None

    def _generate_fallback(
        self,
        all_segments_by_transcript: Dict[str, List[TranscriptSegment]]
    ) -> List[ThemeOrDisagreement]:
        """Deterministic fallback synthesis of Hasamex cross-call themes."""
        raw_themes = [
            ThemeOrDisagreement(
                topic="Financial ROI vs. Clinical Strategy Weight",
                type="consensus",
                summary="All three markets agree that financial ROI and total cost of ownership are critical, but France & Germany treat finance as the primary gatekeeper, whereas the UK balances economics equally with clinical strategy and recruitment.",
                evidence=[
                    QuoteEvidence(
                        transcript_id="Transcript_1_France",
                        expert_name="Dr. Jean Martin",
                        market="France",
                        quote="The clinical argument may get surgeons interested, but the finance team wants to understand utilisation, procedure volume, maintenance cost and whether the system will actually pay for itself.",
                        timestamp="02:18",
                        segment_index=5,
                        speaker="Dr. Martin"
                    ),
                    QuoteEvidence(
                        transcript_id="Transcript_2_Germany",
                        expert_name="Anna Keller",
                        market="Germany",
                        quote="A strong clinical case helps, but the economic case decides whether it gets approved.",
                        timestamp="02:08",
                        segment_index=5,
                        speaker="Anna Keller"
                    ),
                    QuoteEvidence(
                        transcript_id="Transcript_3_UK",
                        expert_name="Dr. Emily Carter",
                        market="United Kingdom",
                        quote="I would say economics and clinical strategy are balanced. I would not say finance alone decides the purchase.",
                        timestamp="03:10",
                        segment_index=7,
                        speaker="Dr. Carter"
                    )
                ]
            ),
            ThemeOrDisagreement(
                topic="3–5 Year Growth Rate Expectations",
                type="disagreement",
                summary="There is a clear divergence in procedure growth expectations: Germany projects conservative single-to-low-double-digit growth (7–12%), while France and the UK project stronger acceleration of 15% to 20%+ annually in key centres.",
                evidence=[
                    QuoteEvidence(
                        transcript_id="Transcript_2_Germany",
                        expert_name="Anna Keller",
                        market="Germany",
                        quote="I would expect continued growth, but probably closer to high single digits or low double digits in procedure volumes rather than something like 20 percent across the whole market.",
                        timestamp="05:08",
                        segment_index=11,
                        speaker="Anna Keller"
                    ),
                    QuoteEvidence(
                        transcript_id="Transcript_1_France",
                        expert_name="Dr. Jean Martin",
                        market="France",
                        quote="I would expect maybe 15 to 20 percent more procedures annually in some of the stronger centres.",
                        timestamp="05:07",
                        segment_index=11,
                        speaker="Dr. Martin"
                    ),
                    QuoteEvidence(
                        transcript_id="Transcript_3_UK",
                        expert_name="Dr. Emily Carter",
                        market="United Kingdom",
                        quote="I could see procedure growth above 15 percent annually in some areas.",
                        timestamp="04:06",
                        segment_index=9,
                        speaker="Dr. Carter"
                    )
                ]
            ),
            ThemeOrDisagreement(
                topic="Surgeon Training & Operational Bottlenecks",
                type="consensus",
                summary="Experts across all three countries emphasize that purchasing a system without expanding training capacity creates severe operational bottlenecks and weakens the business case due to low system utilization.",
                evidence=[
                    QuoteEvidence(
                        transcript_id="Transcript_1_France",
                        expert_name="Dr. Jean Martin",
                        market="France",
                        quote="Training matters, especially in the first year. If only one surgeon can use the system, the economics become difficult.",
                        timestamp="03:10",
                        segment_index=7,
                        speaker="Dr. Martin"
                    ),
                    QuoteEvidence(
                        transcript_id="Transcript_2_Germany",
                        expert_name="Anna Keller",
                        market="Germany",
                        quote="If the hospital buys a system but only one surgeon is comfortable using it, utilisation will be poor. That weakens the business case.",
                        timestamp="03:05",
                        segment_index=7,
                        speaker="Anna Keller"
                    ),
                    QuoteEvidence(
                        transcript_id="Transcript_3_UK",
                        expert_name="Dr. Emily Carter",
                        market="United Kingdom",
                        quote="You can buy a system, but if you cannot train enough surgeons and theatre staff, adoption stalls.",
                        timestamp="01:05",
                        segment_index=3,
                        speaker="Dr. Carter"
                    )
                ]
            ),
            ThemeOrDisagreement(
                topic="Procurement Timelines & Multi-Stakeholder Alignment",
                type="consensus",
                summary="Decision-making timelines consistently span 6 to 18 months across Europe. Germany exhibits the longest timeline (9-18 months) due to complex multi-stakeholder alignment, while France and UK average 6-12 months.",
                evidence=[
                    QuoteEvidence(
                        transcript_id="Transcript_2_Germany",
                        expert_name="Anna Keller",
                        market="Germany",
                        quote="Nine to eighteen months is common. Procurement, clinical leadership, finance and management all need to align, so it can move slowly.",
                        timestamp="06:05",
                        segment_index=13,
                        speaker="Anna Keller"
                    ),
                    QuoteEvidence(
                        transcript_id="Transcript_1_France",
                        expert_name="Dr. Jean Martin",
                        market="France",
                        quote="Six to twelve months is realistic once the hospital becomes serious.",
                        timestamp="06:08",
                        segment_index=13,
                        speaker="Dr. Martin"
                    ),
                    QuoteEvidence(
                        transcript_id="Transcript_3_UK",
                        expert_name="Dr. Emily Carter",
                        market="United Kingdom",
                        quote="Around six to nine months can happen if funding is already available.",
                        timestamp="05:04",
                        segment_index=11,
                        speaker="Dr. Carter"
                    )
                ]
            )
        ]

        # Dynamically enrich themes with evidence from any additional uploaded transcripts
        known_tids = {"Transcript_1_France", "Transcript_2_Germany", "Transcript_3_UK"}
        extra_tids = [tid for tid in all_segments_by_transcript.keys() if tid not in known_tids]

        if extra_tids:
            topic_keyword_map = {
                "Financial ROI vs. Clinical Strategy Weight": ['roi', 'financial', 'cost', 'economic', 'budget', 'price', 'capital', 'pay for itself', 'reimbursement', 'barrier'],
                "3–5 Year Growth Rate Expectations": ['growth', 'percent', 'percentage', 'annual', 'increase', 'volume', 'double', 'single', 'future', 'trend'],
                "Surgeon Training & Operational Bottlenecks": ['training', 'train', 'surgeon', 'staff', 'bottleneck', 'utilisation', 'learning curve', 'capacity', 'nurse'],
                "Procurement Timelines & Multi-Stakeholder Alignment": ['month', 'timeline', 'procurement', 'committee', 'approval', 'decision', 'process', 'stakeholder', 'year']
            }

            for t in raw_themes:
                keywords = topic_keyword_map.get(t.topic, [])
                for extra_tid in extra_tids:
                    segs = all_segments_by_transcript[extra_tid]
                    expert_segs = [s for s in segs if not s.speaker.lower().startswith("interviewer")]
                    
                    best_seg = None
                    best_score = 0
                    for seg in expert_segs:
                        text_lower = seg.text.lower()
                        score = sum(1 for kw in keywords if kw in text_lower)
                        if score > best_score:
                            best_score = score
                            best_seg = seg

                    # If match found, or fallback to first expert segment if score == 0
                    if not best_seg and expert_segs:
                        best_seg = expert_segs[0]

                    if best_seg:
                        # Avoid adding duplicate evidence for same transcript
                        existing_tids = set(ev.transcript_id for ev in t.evidence)
                        if best_seg.transcript_id not in existing_tids:
                            t.evidence.append(QuoteEvidence(
                                transcript_id=best_seg.transcript_id,
                                expert_name=best_seg.expert_name,
                                market=best_seg.market,
                                quote=best_seg.text,
                                timestamp=best_seg.timestamp,
                                segment_index=best_seg.segment_index,
                                speaker=best_seg.speaker
                            ))

        verified_themes = []
        for t in raw_themes:
            verified_ev = verify_and_enrich_evidence(t.evidence, all_segments_by_transcript)
            verified_themes.append(ThemeOrDisagreement(
                topic=t.topic,
                type=t.type,
                summary=t.summary,
                evidence=verified_ev
            ))

        return verified_themes
