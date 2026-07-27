from backend.api.knowledge import clean_knowledge_text_with_pandas, extract_text_from_upload


def test_txt_upload_text_is_decoded_and_cleaned():
    raw = "宋PLUS DM-i 适合家用，空间大。\n\n宋PLUS DM-i 适合家用，空间大。\n  油耗低，适合城市通勤。  ".encode("utf-8")

    text = extract_text_from_upload("cars.txt", raw)
    cleaned = clean_knowledge_text_with_pandas(text)

    assert cleaned.count("宋PLUS DM-i 适合家用") == 1
    assert "油耗低，适合城市通勤。" in cleaned
    assert "\n\n" not in cleaned
