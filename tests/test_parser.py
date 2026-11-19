import unittest

from tariffwire.index_parser import parse_chapter_index, require_complete_chapter_span

FIXTURE = """
<h1>Customs Tariff chapter-by-chapter (T2026-2)</h1>
<h3>Section I: Live Animals; Animal Products</h3>
<table>
  <tr><th>Title</th><th>Effective date</th><th>Format</th></tr>
  <tr>
    <th scope="row"><p>Chapter 1 - Live animals</p></th>
    <td>2026-09-01</td>
    <td><a href="/trade-commerce/tariff-tarif/2026/html/02/ch01-eng.html">HTML</a></td>
  </tr>
  <tr>
    <th>Chapter 2 - Meat and edible meat offal</th>
    <td>2026-09-01</td>
    <td><a href="/trade-commerce/tariff-tarif/2026/html/02/ch02-eng.html">HTML</a></td>
  </tr>
</table>
<h3>Section XXI: Works of art</h3>
<table>
  <tr><th>Title</th><th>Effective date</th><th>Format</th></tr>
  <tr>
    <th>Chapter 77 - (<i>Reserved for possible future use in the Harmonized System</i>)</th>
    <td>2026-09-01</td>
    <td><a href="/trade-commerce/tariff-tarif/2026/html/02/ch77-eng.html">HTML</a></td>
  </tr>
</table>
"""


class ParserTests(unittest.TestCase):
    def test_header_row_does_not_swallow_the_first_chapter(self):
        catalog = parse_chapter_index(FIXTURE, retrieved_on="2026-11-13")
        by_number = {item["chapter"]: item for item in catalog["chapters"]}
        self.assertEqual(set(by_number), {1, 2, 77})
        self.assertEqual(by_number[1]["title"], "Live animals")
        self.assertEqual(by_number[1]["section"], "I")
        self.assertTrue(by_number[1]["html_url"].endswith("/ch01-eng.html"))
        self.assertEqual(
            by_number[77]["title"],
            "(Reserved for possible future use in the Harmonized System)",
        )
        self.assertFalse(catalog["contains_duty_rates"])

    def test_incomplete_index_is_rejected(self):
        catalog = parse_chapter_index(FIXTURE, retrieved_on="2026-11-13")
        with self.assertRaises(ValueError):
            require_complete_chapter_span(catalog)


if __name__ == "__main__":
    unittest.main()
