import unittest

from rating.processing import rates
from rating.processing.utils import ConfigurationException

class TestConversion(unittest.TestCase):

    def test_conversion_byte_second_to_hour_harder(self):
        rating_unit = 'GiB-hours'
        metric_unit = 'byte-seconds'
        qty = 7e12
        converted = rates.convert_metrics_unit(metric_unit,
                                               rating_unit,
                                               qty)
        self.assertAlmostEqual(converted, 1.8109050061, delta=1e-6)

    def test_conversion_core_second_to_hour_basic(self):
        rating_unit = 'core-hours'
        metric_unit = 'core-seconds'
        qty = 10
        converted = rates.convert_metrics_unit(metric_unit,
                                               rating_unit,
                                               qty)
        self.assertAlmostEqual(converted, 0.002777, delta=1e-6)

    def test_conversion_core_second_to_hour_harder(self):
        rating_unit = 'core-hours'
        metric_unit = 'core-seconds'
        qty = 24
        converted = rates.convert_metrics_unit(metric_unit,
                                               rating_unit,
                                               qty)
        self.assertAlmostEqual(converted, 0.006666, delta=1e-6)

    def test_wrong_conversion(self):
        rating_unit = 'some-random-rating_unit'
        metric_unit = 'core-seconds'
        qty = 1
        with self.assertRaisesRegex(ConfigurationException,
                                    'Unsupported key'):
            rates.convert_metrics_unit(metric_unit,
                                       rating_unit,
                                       qty)
