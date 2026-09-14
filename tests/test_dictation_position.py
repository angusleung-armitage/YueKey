"""Desktop geometry and presentation must preserve dictation's target guards."""
from dataclasses import replace
import unittest

from quick_hk.dictation_position import indicator_position, valid_rect
from quick_hk.windows_state import Target, Request


class PositionTests(unittest.TestCase):
    def test_caret_edges_and_monitors(self):
        area = (0, 0, 1920, 1040)
        self.assertEqual(indicator_position((400, 300, 1, 20), area, 64, 24), (368, 326))
        self.assertEqual(indicator_position((1900, 1020, 1, 20), area, 64, 24), (1850, 990))
        self.assertEqual(indicator_position((-1300, -100, 1, 20),
                         (-1920, -200, 1920, 1080), 64, 24), (-1332, -74))
        self.assertEqual(indicator_position((-4000, -4000, 1, 20), area, 64, 24), (6, 6))
        self.assertEqual(indicator_position((400, 300, 600, 32), area, 64, 24), (374, 338))
        # 200% scale: both indicator and gap remain beside the physical caret.
        self.assertEqual(indicator_position((800, 600, 2, 40),
                         (0, 0, 3840, 2080), 128, 48, 12), (736, 652))

    def test_unreported_and_invalid_geometry(self):
        self.assertTrue(valid_rect((0, 0, 0, 18)))
        for value in (None, (), (0, 0, 0, 0), (0, 0, -1, 20),
                      (float('nan'), 0, 1, 20), (0, float('inf'), 1, 20)):
            self.assertFalse(valid_rect(value))

    def test_presentation_geometry_does_not_weaken_target_identity(self):
        target = Target(1, 2, (3,), 4, (100, 100, 1, 20))
        self.assertTrue(Request('id', target, 'finishing').consume(
            'id', replace(target, anchor=(200, 200, 1, 20))))
        for values in ({'window': 5}, {'process': 5}, {'runtime_id': (5,)}, {'activity': 5}):
            self.assertFalse(Request('id', target, 'finishing').consume('id', replace(target, **values)))
