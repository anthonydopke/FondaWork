from DataFetcher import DataFetcher
from FundamentalAnalysis import FundamentalAnalysis
from RatingEngine import RatingEngine
from ResultBuilder import ResultBuilder
from StockMap import resolve_ticker
from Valuation import simple_valuation


def run_analysis():
    user_input = input("Enter a stock name or ticker: ")
    ticker = resolve_ticker(user_input)

    print(f"Resolved ticker: {ticker}")

    # Fetch financial data
    fetcher = DataFetcher(ticker)
    income = fetcher.get_income_statement()
    balance = fetcher.get_balance_sheet()
    cashflow = fetcher.get_cashflow()
    info = fetcher.get_info()

    # Fundamental analysis
    analysis = FundamentalAnalysis(income, balance, cashflow, info)

    indicators = {
        "Revenue Growth (%)": analysis.compute_revenue_growth(),
        "Net Income Growth (%)": analysis.compute_net_income_growth(),
        "Operating Margin": analysis.get_operating_margin(),
        "Net Margin": analysis.get_net_margin(),
        "ROE": analysis.get_roe(),
        "ROA": analysis.get_roa(),
        "Debt/Equity": analysis.get_debt_to_equity(),
        "Current Ratio": analysis.get_current_ratio(),
        "PE Ratio": analysis.get_pe_ratio(),
        "Price to Book": analysis.get_price_to_book(),
        "Price to Sales": analysis.get_price_to_sales(),
    }

    ratings = {
        "Revenue Growth": RatingEngine.rate_value(indicators["Revenue Growth (%)"], (0, 5)),
        "Net Income Growth": RatingEngine.rate_value(indicators["Net Income Growth (%)"], (0, 5)),
        "Operating Margin": RatingEngine.rate_value(indicators["Operating Margin"], (0.05, 0.15)),
        "ROE": RatingEngine.rate_value(indicators["ROE"], (0.10, 0.15)),
        "Debt/Equity": "Good" if indicators["Debt/Equity"] and indicators["Debt/Equity"] < 100 else "Weak"
    }

    score = RatingEngine.compute_global_score(ratings)

    # Valuation analysis
    valuation_info = simple_valuation(info)

    # Build report
    report = ResultBuilder().build_text_report(ticker, indicators, ratings, score)

    # Append valuation to report
    report += "\n\n--- Valuation ---\n"
    for ratio, val in valuation_info["valuation_ratios"].items():
        report += f"{ratio}: {val}\n"
    report += f"Current Price: {valuation_info['current_price']}\n"
    report += f"Suggested Entry Price: {valuation_info['suggested_entry']}\n"

    print(report)


if __name__ == "__main__":
    run_analysis()
