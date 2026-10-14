"""One tiny Vertex Gemini call (5 output tokens, < $0.001) to test whether generation is allowed. Exit 0 = OK."""

import sys

from google import genai
from google.genai import types

from pitchops.config import get_settings

s = get_settings()
client = genai.Client(vertexai=True, project=s.gcp_project_id, location=s.gemini_location)
try:
    client.models.generate_content(model=s.gemini_model_lite, contents="Reply: ok",
                                   config=types.GenerateContentConfig(max_output_tokens=5, temperature=0))
    print("PROBE_OK")
    sys.exit(0)
except Exception as e:
    print("PROBE_FAIL", str(e)[:120])
    sys.exit(1)
