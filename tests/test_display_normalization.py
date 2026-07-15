from src.normalization import normalize_display_text


def test_normalize_display_text_preserves_accents_and_fixes_typography():
    assert normalize_display_text("Beyoncé") == "Beyoncé"
    assert normalize_display_text("Billy Idol - \xa0Rebel Yell") == "Billy Idol - Rebel Yell"
    assert normalize_display_text("La Femme D´Argent") == "La Femme D'Argent"
    assert normalize_display_text("freedom bossa～避暑地で聞きたいリゾートボッサ～") == "freedom bossa~避暑地で聞きたいリゾートボッサ~"
    assert normalize_display_text("R%C3%9CF%C3%9CS DU SOL") == "RÜFÜS DU SOL"
    assert normalize_display_text("https://example.com/R%C3%9CF%C3%9CS") == "https://example.com/R%C3%9CF%C3%9CS"
