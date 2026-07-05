import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.stable_id import generate_stable_id

def test_generate_stable_id():
    id1 = generate_stable_id("Bohemian Rhapsody", "Queen")
    id2 = generate_stable_id("bohemian rhapsody  ", "the queen") # normalized
    assert id1 == id2

    id3 = generate_stable_id("Bohemian Rhapsody", "Queen", "Live")
    assert id1 != id3
