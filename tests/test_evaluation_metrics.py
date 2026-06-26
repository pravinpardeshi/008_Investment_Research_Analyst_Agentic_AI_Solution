import pytest
from api.evaluation import Metrics


class TestMetrics:
    def test_count_citations(self):
        report = "Growth was strong [1]. Margins improved [2]."
        assert Metrics.count_citations(report) == 2

    def test_count_citations_none(self):
        assert Metrics.count_citations("No citations here.") == 0

    def test_check_completeness_all(self):
        report = "# Executive Summary\n# Company Overview\n# Financial Analysis\n# Strategic Analysis\n# Risk Analysis\n# Investment Thesis\n# Conclusion"
        result = Metrics.check_report_completeness(report)
        assert all(result.values())

    def test_check_completeness_missing(self):
        report = "# Executive Summary"
        result = Metrics.check_report_completeness(report)
        assert result["Executive Summary"] is True
        assert result["Conclusion"] is False

    def test_report_length(self):
        report = "one two three four five"
        assert Metrics.report_length(report) == 5
