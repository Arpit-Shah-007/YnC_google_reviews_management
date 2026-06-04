import json
from generate_stores import build_google_maps_url, parse_site_list


def test_build_google_maps_url_encodes_address():
    url = build_google_maps_url("Taco Bell", "3 Path Plaza, Jersey City, NJ 07036")
    assert url.startswith("https://www.google.com/maps/search/?api=1&query=")
    assert "Taco+Bell" in url or "Taco%20Bell" in url
    assert "Jersey+City" in url or "Jersey%20City" in url


def test_build_google_maps_url_no_spaces():
    url = build_google_maps_url("Taco Bell", "3 Path Plaza, Jersey City, NJ 07036")
    assert " " not in url


def test_parse_site_list_returns_correct_counts(tmp_path):
    # This test runs against the real Site List.xlsx in the project root
    stores = parse_site_list("Site List.xlsx")
    taco = [s for s in stores if s["group"] == "Taco Bell"]
    north = [s for s in stores if s["group"] == "Wendy's North"]
    south = [s for s in stores if s["group"] == "Wendy's South"]
    assert len(taco) == 14
    assert len(north) > 0
    assert len(south) > 0


def test_parse_site_list_store_has_required_fields():
    stores = parse_site_list("Site List.xlsx")
    for store in stores:
        assert "brand" in store
        assert "group" in store
        assert "store_number" in store
        assert "name" in store
        assert "address" in store
        assert "google_maps_url" in store
        assert store["google_maps_url"].startswith("https://")


def test_parse_site_list_no_section_headers_in_output():
    stores = parse_site_list("Site List.xlsx")
    names = [s["name"] for s in stores]
    assert "Taco Bells" not in names
    assert "Wendy's North" not in names
    assert "Wendy's South" not in names
