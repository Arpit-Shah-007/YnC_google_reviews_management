from analyze import load_latest_reviews, group_reviews_by_store, calculate_avg_rating
from analyze import build_gemini_prompt, parse_gemini_response


def test_load_latest_reviews_returns_list(tmp_path, monkeypatch):
    import json
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "reviews_2025-06-01_test.json").write_text(
        json.dumps([{"title": "Taco Bell", "url": "https://maps?query=TB", "stars": 4, "text": "Good"}])
    )
    reviews = load_latest_reviews(data_dir=str(tmp_path / "data"))
    assert isinstance(reviews, list)
    assert len(reviews) == 1


def test_group_reviews_by_store_matches_by_query_param():
    stores = [
        {
            "group": "Taco Bell",
            "name": "Taco Bell #1",
            "address": "123 Main St, Newark, NJ 07101",
            "google_maps_url": "https://www.google.com/maps/search/?api=1&query=Taco+Bell+123+Main+St",
        }
    ]
    reviews = [
        {"title": "Taco Bell", "url": "https://www.google.com/maps/search/?api=1&query=Taco+Bell+123+Main+St&query_place_id=ABC123", "stars": 5, "text": "Great!"},
        {"title": "Taco Bell", "url": "https://www.google.com/maps/search/?api=1&query=Taco+Bell+123+Main+St&query_place_id=ABC123", "stars": 3, "text": "Okay"},
    ]
    grouped = group_reviews_by_store(reviews, stores)
    assert len(grouped) == 1
    assert grouped[0]["store"]["name"] == "Taco Bell #1"
    assert len(grouped[0]["reviews"]) == 2


def test_group_reviews_by_store_no_match_skips_gracefully():
    stores = [
        {
            "group": "Taco Bell",
            "name": "Taco Bell #1",
            "address": "123 Main St",
            "google_maps_url": "https://www.google.com/maps/search/?api=1&query=Taco+Bell+123+Main+St",
        }
    ]
    reviews = [
        {"title": "Taco Bell", "url": "https://www.google.com/maps/search/?api=1&query=Completely+Different&query_place_id=ZZZ", "stars": 4, "text": "Fine"},
    ]
    grouped = group_reviews_by_store(reviews, stores)
    assert len(grouped) == 1
    assert grouped[0]["reviews"] == []


def test_calculate_avg_rating_correct():
    reviews = [{"stars": 5}, {"stars": 3}, {"stars": 4}]
    assert calculate_avg_rating(reviews) == 4.0


def test_calculate_avg_rating_empty_returns_none():
    assert calculate_avg_rating([]) is None


def test_build_gemini_prompt_contains_store_name():
    reviews = [{"stars": 4, "text": "Great food"}, {"stars": 2, "text": "Slow service"}]
    prompt = build_gemini_prompt("Taco Bell #041966", "3 Path Plaza, Jersey City, NJ 07036", reviews)
    assert "Taco Bell #041966" in prompt
    assert "Jersey City" in prompt
    assert "Great food" in prompt
    assert "Slow service" in prompt


def test_parse_gemini_response_extracts_summary_and_actions():
    raw = "SUMMARY: Food quality is consistently praised but drive-through wait times are too long.\nACTIONS: 1. Add a second order-taker during peak hours. 2. Review drive-through staffing schedule. 3. Set a target of under 4 minutes per car."
    result = parse_gemini_response(raw)
    assert "Food quality" in result["summary"]
    assert len(result["actions"]) == 3
    assert "Add a second" in result["actions"][0]


def test_parse_gemini_response_handles_unexpected_format():
    raw = "Some unexpected response without the expected format."
    result = parse_gemini_response(raw)
    assert "summary" in result
    assert "actions" in result
    assert isinstance(result["actions"], list)
