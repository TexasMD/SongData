import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.normalization import normalize_text, normalize_artist

def test_normalize_text():
    assert normalize_text("  Hello  World!  ") == "hello world"
    assert normalize_text("Beyoncé") == "beyonce"
    assert normalize_text("A_B-C.D,E") == "a_b-c.d,e"

def test_normalize_artist():
    assert normalize_artist("The Beatles") == "beatles"
    assert normalize_artist("the strokes") == "strokes"
    assert normalize_artist("Queen") == "queen"
