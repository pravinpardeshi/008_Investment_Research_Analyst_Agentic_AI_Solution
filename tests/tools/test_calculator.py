import pytest
from api.tools import Calculator


class TestCalculator:
    def test_growth_rate(self):
        rate = Calculator.calculate_growth_rate(120, 100)
        assert rate == 20.0

    def test_growth_rate_zero_previous(self):
        rate = Calculator.calculate_growth_rate(100, 0)
        assert rate == 0.0

    def test_margin(self):
        margin = Calculator.calculate_margin(30, 100)
        assert margin == 30.0

    def test_roe(self):
        roe = Calculator.calculate_roe(15, 100)
        assert roe == 15.0

    def test_roa(self):
        roa = Calculator.calculate_roa(10, 200)
        assert roa == 5.0
