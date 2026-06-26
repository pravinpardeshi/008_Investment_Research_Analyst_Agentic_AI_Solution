from sqlalchemy.orm import Session

from api.models import ResearchRun, Finding, Report, EvaluationMetric


class PostgresMemory:
    def __init__(self, db: Session):
        self.db = db

    def create_research_run(self, question: str) -> ResearchRun:
        run = ResearchRun(question=question, status="pending")
        self.db.add(run)
        self.db.commit()
        self.db.refresh(run)
        return run

    def update_run_status(self, run_id: int, status: str):
        run = self.db.query(ResearchRun).filter(ResearchRun.id == run_id).first()
        if run:
            run.status = status
            self.db.commit()

    def store_finding(self, run_id: int, topic: str, content: str) -> Finding:
        finding = Finding(research_run_id=run_id, topic=topic, content=content)
        self.db.add(finding)
        self.db.commit()
        self.db.refresh(finding)
        return finding

    def get_findings(self, run_id: int) -> list[Finding]:
        return self.db.query(Finding).filter(Finding.research_run_id == run_id).all()

    def store_report(self, run_id: int, report_text: str) -> Report:
        report = Report(research_run_id=run_id, report_text=report_text)
        self.db.add(report)
        self.db.commit()
        self.db.refresh(report)
        return report

    def get_report(self, run_id: int) -> Report | None:
        return self.db.query(Report).filter(Report.research_run_id == run_id).first()

    def get_run(self, run_id: int) -> ResearchRun | None:
        return self.db.query(ResearchRun).filter(ResearchRun.id == run_id).first()

    def get_previous_questions(self) -> list[str]:
        runs = self.db.query(ResearchRun.question).all()
        return [r[0] for r in runs]

    def store_metric(self, run_id: int, name: str, value: int):
        metric = EvaluationMetric(research_run_id=run_id, metric_name=name, metric_value=value)
        self.db.add(metric)
        self.db.commit()
