import pytest
from scripts.split_billboard_artists import split_artist_name

def test_split_artist_name_multiple():
    assert split_artist_name("21 Savage & Metro Boomin") == ["21 Savage", "Metro Boomin"]
    assert split_artist_name("Ariana Grande & Nathan Sykes") == ["Ariana Grande", "Nathan Sykes"]
    assert split_artist_name("Artist A x Artist B") == ["Artist A", "Artist B"]
    assert split_artist_name("Artist A, Artist B and Artist C") == ["Artist A", "Artist B", "Artist C"]

def test_split_artist_name_protected_bands():
    assert split_artist_name("Earth, Wind & Fire") == ["Earth, Wind & Fire"]
    assert split_artist_name("AC/DC") == ["AC/DC"]
    assert split_artist_name("Boyz II Men") == ["Boyz II Men"]
    assert split_artist_name("Simon & Garfunkel") == ["Simon & Garfunkel"]

def test_split_artist_name_protected_bands_in_collaboration():
    assert split_artist_name("Earth, Wind & Fire & Santana") == ["Earth, Wind & Fire", "Santana"]
    assert split_artist_name("Santana and Earth, Wind & Fire") == ["Santana", "Earth, Wind & Fire"]

def test_split_artist_name_with_backing_band():
    assert split_artist_name("Bruce Springsteen & The E Street Band") == ["Bruce Springsteen & The E Street Band"]
    assert split_artist_name("Joan Jett & The Blackhearts") == ["Joan Jett & The Blackhearts"]
    # Even if it's not explicitly in the list, heuristics should catch it and combine the last two parts:
    assert split_artist_name("Some Guy & The Band") == ["Some Guy and The Band"]
    assert split_artist_name("Fake Name & His Orchestra") == ["Fake Name and His Orchestra"]
    assert split_artist_name("Artist A, Artist B & The Band") == ["Artist A", "Artist B and The Band"]

def test_split_artist_name_nan():
    import numpy as np
    assert split_artist_name(np.nan) == [""]
    assert split_artist_name(None) == [""]
    assert split_artist_name(123.45) == ["123.45"]
