class Calculator:
    @staticmethod
    def calculate_growth_rate(current: float, previous: float) -> float:
        if previous == 0:
            return 0.0
        return (current - previous) / abs(previous) * 100

    @staticmethod
    def calculate_margin(income: float, revenue: float) -> float:
        if revenue == 0:
            return 0.0
        return (income / revenue) * 100

    @staticmethod
    def calculate_roe(net_income: float, equity: float) -> float:
        if equity == 0:
            return 0.0
        return (net_income / equity) * 100

    @staticmethod
    def calculate_roa(net_income: float, total_assets: float) -> float:
        if total_assets == 0:
            return 0.0
        return (net_income / total_assets) * 100
