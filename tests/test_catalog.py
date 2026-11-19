import json
import re
import unittest

from tariffwire.catalog import chapters_catalog, documents_catalog, search, sources_catalog

GOVERNMENT_HOSTS = (
    "cbsa-asfc.gc.ca",
    "canada.ca",
    "laws-lois.justice.gc.ca",
    "gazette.gc.ca",
    "international.canada.ca",
    "citt-tcce.gc.ca",
)
RATE_BESIDE_CODE = re.compile(r"\d{4}\.\d{2}[\s\S]{0,80}%|%[\s\S]{0,80}\d{4}\.\d{2}")


class CatalogTests(unittest.TestCase):
    def test_stored_index_is_the_parsed_t2026_2_span(self):
        catalog = chapters_catalog()
        self.assertEqual(catalog["edition"], "T2026-2")
        self.assertEqual(catalog["retrieved_at"], "2026-11-13")
        self.assertEqual([item["chapter"] for item in catalog["chapters"]], list(range(1, 100)))
        chapter_9 = catalog["chapters"][8]
        self.assertEqual(chapter_9["title"], "Coffee, tea, maté and spices")
        self.assertEqual(chapter_9["effective_date"], "2026-09-01")
        self.assertIn("ch09-eng.html", chapter_9["html_url"])
        reserved = catalog["chapters"][76]
        self.assertIn("Reserved for possible future use", reserved["title"])
        self.assertFalse(catalog["contains_duty_rates"])
        self.assertFalse(catalog["contains_tariff_items"])

    def test_search_matches_titles_and_does_not_invent_a_rate(self):
        coffee = search("roasted coffee")
        self.assertTrue(any(item["chapter"] == 9 for item in coffee["results"] if item["kind"] == "chapter"))
        code = search("0901.21.00")
        chapter_hits = [item for item in code["results"] if item["kind"] == "chapter"]
        self.assertEqual(chapter_hits[0]["chapter"], 9)
        self.assertIsNone(chapter_hits[0]["duty_rate"])
        self.assertIsNone(chapter_hits[0]["tariff_classification"])
        self.assertIn("did not check", chapter_hits[0]["match_reason"])
        rulings = search("advance ruling")
        self.assertTrue(any(item["id"] == "cbsa-advance-rulings" for item in rulings["results"]))

    def test_documents_cite_real_pages_and_do_not_pair_a_code_with_a_rate(self):
        documents = documents_catalog()["documents"]
        ids = {item["id"] for item in documents}
        for required in (
            "cbsa-classification-guide",
            "cn-26-23",
            "sor-2026-186",
            "finance-us-counter-tariffs",
            "cn-26-22",
            "gac-agreements-catalogue",
        ):
            self.assertIn(required, ids)
        for document in documents:
            self.assertTrue(document["url"].startswith("https://"), document["id"])
            host = document["url"].split("/")[2]
            self.assertTrue(any(host.endswith(allowed) for allowed in GOVERNMENT_HOSTS), document["url"])
            self.assertEqual(document["jurisdiction"], "Canada")
            self.assertTrue(document["retrieved_at"])
            self.assertIsNone(RATE_BESIDE_CODE.search(json.dumps(document)))

    def test_rejected_sources_are_not_marked_as_integrated(self):
        sources = sources_catalog()["sources"]
        rejected = {item["id"]: item for item in sources if item["status"] == "evaluated_not_used"}
        self.assertIn("carm", rejected)
        self.assertIn("wco-explanatory-notes", rejected)
        self.assertIn("tradefacts-and-similar-apis", rejected)
        for source in sources:
            self.assertFalse(source["live_integration"])


if __name__ == "__main__":
    unittest.main()
