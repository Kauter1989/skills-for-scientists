import unittest

from median import median


class MedianTest(unittest.TestCase):
    def test_even_length_returns_mean_of_middle_two(self):
        self.assertEqual(median([1, 2, 3, 4]), 2.5)


if __name__ == "__main__":
    unittest.main()