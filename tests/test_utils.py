import pytest
from utils import fix_unit_of_measurement


class TestFixUnitOfMeasurement:
    def test_kpa_variants(self):
        assert fix_unit_of_measurement('kpa') == 'kPa'
        assert fix_unit_of_measurement('KPa') == 'kPa'
        assert fix_unit_of_measurement('KPA') == 'kPa'

    def test_celsius_variants(self):
        assert fix_unit_of_measurement('ºC') == '°C'
        assert fix_unit_of_measurement('°C') == '°C'
        assert fix_unit_of_measurement('DEG C') == '°C'
        assert fix_unit_of_measurement('degc') == '°C'
        assert fix_unit_of_measurement('OC') == '°C'

    def test_fahrenheit_variants(self):
        assert fix_unit_of_measurement('DEG F') == '°F'
        assert fix_unit_of_measurement('degf') == '°F'

    def test_rpm(self):
        assert fix_unit_of_measurement('RPM') == 'rpm'
        assert fix_unit_of_measurement('Rpm') == 'rpm'

    def test_ips(self):
        assert fix_unit_of_measurement('ips') == 'IPS'

    def test_leading_trailing_spaces_stripped(self):
        assert fix_unit_of_measurement('  kpa  ') == 'kPa'

    def test_empty_string_returned_as_is(self):
        assert fix_unit_of_measurement('') == ''
        assert fix_unit_of_measurement('   ') == ''

    def test_unknown_unit_returned_trimmed(self):
        assert fix_unit_of_measurement('  bar  ') == 'bar'
        assert fix_unit_of_measurement('m/s') == 'm/s'

    def test_non_string_passthrough(self):
        assert fix_unit_of_measurement(None) is None
        assert fix_unit_of_measurement(42) == 42
