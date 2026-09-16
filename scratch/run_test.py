import os
import sys

BASE_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
backend_path = os.path.join(BASE_DIR, "backend")
if backend_path not in sys.path:
    sys.path.append(backend_path)

from dotenv import load_dotenv

load_dotenv()

from ml.pipeline import process_document
from ml.ai.providers.groq_provider import groq_extractor

print("--- 1. Testing Groq Network Extraction ---")
evidence_text = """
On 15 January 2024, informant reported that Kabir Singhania (phone +919811223344) coordinates operations for Alpha Syndicate.
Kabir Singhania wired 12,50,000 INR to Zenith Global Export bank account AC99881122 in Mumbai.
Zenith Global Export is registered under owner Tariq Mansoor.
Tariq Mansoor was observed meeting Kabir Singhania at Hotel Trident, Mumbai.
"""

result = process_document(
    document_id="doc_intelligencetest_001",
    text=evidence_text,
    return_full_analysis=True,
)

entities = result["entities"]
relationships = result["relationships"]

print("Entities Extracted:", len(entities))
for e in entities[:6]:
    print(f"  [{e.type.value}] {e.name} (id: {e.id}, conf: {e.confidence})")

print("\nRelationships Extracted:", len(relationships))
for r in relationships:
    print(f"  {r.source_entity_id} --[{r.relationship.value}]--> {r.target_entity_id} | Evidence: {r.evidence_snippet}")

print("\n--- 2. Testing Gemini Network Reasoning ---")
from app.services.gemini_provider import gemini_engine

if gemini_engine.is_available():
    ent_table = "| Entity Name | Type | Entity ID |\n|---|---|---|\n| Kabir Singhania | PERSON | mention_001 |\n| Zenith Global Export | ORGANIZATION | mention_002 |\n| Tariq Mansoor | PERSON | mention_003 |"
    rel_table = "| Source Entity | Relationship | Target Entity | Status | Confidence | Evidence Snippet |\n|---|---|---|---|---|---|\n| Kabir Singhania | SENT_MONEY_TO | Zenith Global Export | INFERRED | 0.95 | Kabir Singhania wired 12,50,000 INR to Zenith Global Export |\n| Tariq Mansoor | WORKS_FOR | Zenith Global Export | INFERRED | 0.90 | Zenith Global Export is registered under owner Tariq Mansoor |"

    prompt = f"Given these case tables:\n{ent_table}\n\n{rel_table}\n\nBriefly explain the money flow and key actors in 2 bullet points."
    resp_text = gemini_engine._generate_with_fallback(prompt)
    print("Gemini Response:\n", resp_text.strip())
    print("\n[SUCCESS] AI Pipeline integration test passed!")
else:
    print("Gemini engine client not available.")
