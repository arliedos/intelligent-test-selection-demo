"""T07 - catalogue search (independent of the checkout->payments->gateway chain)."""
from demoshop.catalogue import InMemoryCatalogue


def test_search_matches_case_insensitive_substring():
    catalogue = InMemoryCatalogue()

    results = catalogue.search("wid")

    names = {item.name for item in results}
    assert "Blue Widget" in names
    assert "Red Widget" in names


def test_search_returns_empty_list_for_no_match():
    catalogue = InMemoryCatalogue()

    results = catalogue.search("nonexistent-product-xyz")

    assert results == []


def test_search_empty_query_returns_all_products():
    catalogue = InMemoryCatalogue()

    results = catalogue.search("")

    assert len(results) == len(catalogue.list_all())
