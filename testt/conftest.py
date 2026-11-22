"""Makes the project folder importable so tests can do `from main import app`."""
import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
os.environ.pop("GEMINI_API_KEY", None)  # tests check the fixed rule-based replies, so they run without the model
