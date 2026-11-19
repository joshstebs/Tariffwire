import json
import unittest

from tariffwire.classify import research_packet

FORBIDDEN = (
    "the correct classification",
    "duty rate is",
    "recommended classification",
    "classified under",
    "you should declare",
)


class ClassifyTests(unittest.TestCase):
    def test_coffee_is_a_title_pointer_not_a_classification(self):
        packet = research_packet("roasted coffee beans, not decaffeinated")
        self.assertEqual(packet["status"], "not_a_classification")
        self.assertEqual(packet["uncertainty"]["level"], "high")
        self.assertTrue(packet["professional_review_required"])
        self.assertIsNone(packet["tariff_classification"])
        self.assertIsNone(packet["duty_rate"])
        self.assertEqual([item["chapter"] for item in packet["candidate_chapters"]], [9])
        self.assertEqual(packet["candidate_chapters"][0]["confidence"], "not_a_classification")
        self.assertNotIn("%", json.dumps(packet))

    def test_a_set_across_sections_stays_ambiguous(self):
        packet = research_packet("chocolate and a ceramic mug gift set")
        chapters = {item["chapter"] for item in packet["candidate_chapters"]}
        self.assertIn(18, chapters)
        self.assertIn(69, chapters)
        self.assertEqual(packet["status"], "ambiguous_title_overlap")
        self.assertTrue(any("set" in trigger.lower() or "kit" in trigger.lower() for trigger in packet["review_triggers"]))
        self.assertIsNone(packet["tariff_classification"])
        self.assertIsNone(packet["duty_rate"])

    def test_unknown_goods_are_not_guessed(self):
        packet = research_packet("laptop computer")
        self.assertEqual(packet["status"], "no_title_overlap")
        self.assertEqual(packet["candidate_chapters"], [])
        self.assertIsNone(packet["tariff_classification"])

    def test_empty_description_asks_for_more(self):
        packet = research_packet("  ")
        self.assertEqual(packet["status"], "need_more_information")
        self.assertEqual(packet["candidate_chapters"], [])

    def test_user_supplied_code_is_not_confirmed(self):
        packet = research_packet("Please classify 0901.21.00.10 and tell me the duty rate")
        self.assertEqual(packet["user_supplied_code"]["normalized"], "0901.21.00.10")
        self.assertTrue(packet["user_supplied_code"]["unverified"])
        self.assertIsNone(packet["user_supplied_code"]["exists_in_stored_schedule"])
        self.assertEqual(packet["user_supplied_code"]["chapter_pointer"]["chapter"], 9)
        self.assertIsNone(packet["tariff_classification"])
        self.assertIsNone(packet["duty_rate"])
        self.assertIsNone(packet["surtax_determination"])

    def test_united_states_origin_does_not_pick_a_surtax_rate(self):
        packet = research_packet("steel pipe", origin="United States")
        self.assertIsNone(packet["surtax_determination"])
        self.assertIsNone(packet["origin_determination"])
        cited = {item["id"] for item in packet["citations"]}
        self.assertIn("cn-26-23", cited)
        self.assertIn("sor-2026-186", cited)
        self.assertNotIn("%", json.dumps(packet))

    def test_uk_cptpp_conflict_is_surfaced_and_not_resolved(self):
        packet = research_packet("green tea", origin="United Kingdom")
        self.assertTrue(packet["conflicts"])
        self.assertIn("unresolved", packet["conflicts"][0]["observation"].lower() + packet["conflicts"][0]["level"])
        self.assertIsNone(packet["origin_determination"])

    def test_packet_language_does_not_sound_like_a_ruling(self):
        packet = research_packet("parts for a cotton shirt set", materials="cotton", condition="Used")
        text = json.dumps(packet).lower()
        for phrase in FORBIDDEN:
            self.assertNotIn(phrase, text)
        self.assertIn("not a tariff classification", text)


if __name__ == "__main__":
    unittest.main()
