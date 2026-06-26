import re


class Metrics:
    @staticmethod
    def count_citations(report: str) -> int:
        citations = re.findall(r'\[(\d+)\]', report)
        return len(citations)

    @staticmethod
    def count_chunks_retrieved(findings: list[dict]) -> int:
        count = 0
        for f in findings:
            citations = f.get("citations", [])
            if isinstance(citations, list):
                count += len(citations)
        return count

    @staticmethod
    def check_report_completeness(report: str) -> dict[str, bool]:
        required_sections = [
            "Executive Summary",
            "Company Overview",
            "Financial Analysis",
            "Strategic Analysis",
            "Risk Analysis",
            "Investment Thesis",
            "Conclusion",
        ]
        result = {}
        for section in required_sections:
            result[section] = section.lower() in report.lower()
        return result

    @staticmethod
    def report_length(report: str) -> int:
        return len(report.split())
