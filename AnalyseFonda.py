import yfinance as yf
import pandas as pd
import numpy as np

def note_indicateur(val, seuils):
    """
    Retourne une évaluation qualitative selon les seuils fournis.
    seuils = (faible, moyen). Ex: (5%,10%)
    """
    if val is None or np.isnan(val):
        return "Donnée indisponible"
    if val < seuils[0]:
        return "❌ Faible"
    elif val < seuils[1]:
        return "⚠️ Moyen"
    else:
        return "✅ Bon"


def analyse_fondamentale(ticker):
    stock = yf.Ticker(ticker)
    info = stock.info

    print("\n==============================")
    print(f"   ANALYSE FONDAMENTALE : {ticker}")
    print("==============================\n")

    # ---------------------------
    # 1) CROISSANCE
    # ---------------------------

    try:
        income = stock.get_income_stmt().T
        income.index = pd.to_datetime(income.index)
        income = income.sort_index()

        rev_growth = income["Total Revenue"].pct_change().mean() * 100
        eps_growth = income["Net Income"].pct_change().mean() * 100
    except:
        rev_growth = None
        eps_growth = None

    print("📌 CROISSANCE")
    print(f" - Croissance moyenne du CA : {rev_growth:.2f}% ({note_indicateur(rev_growth, (0, 5))})" if rev_growth else " - CA : Donnée indisponible")
    print(f" - Croissance du RN/EPS      : {eps_growth:.2f}% ({note_indicateur(eps_growth, (0, 5))})" if eps_growth else " - RN/EPS : Donnée indisponible")
    print("")

    # ---------------------------
    # 2) RENTABILITÉ
    # ---------------------------

    marge_op = info.get("operatingMargins", None)
    marge_net = info.get("profitMargins", None)
    roe = info.get("returnOnEquity", None)
    roa = info.get("returnOnAssets", None)

    print("📌 RENTABILITÉ")
    print(f" - Marge opérationnelle : {marge_op:.2%} ({note_indicateur(marge_op*100 if marge_op else None, (5, 15))})" if marge_op else " - Marge opérationnelle : Indispo")
    print(f" - Marge nette          : {marge_net:.2%} ({note_indicateur(marge_net*100 if marge_net else None, (5, 15))})" if marge_net else " - Marge nette : Indispo")
    print(f" - ROE                  : {roe:.2%} ({note_indicateur(roe*100 if roe else None, (10, 15))})" if roe else " - ROE : Indispo")
    print(f" - ROA                  : {roa:.2%} ({note_indicateur(roa*100 if roa else None, (5, 10))})" if roa else " - ROA : Indispo")
    print("")

    # ---------------------------
    # 3) SANTÉ FINANCIÈRE
    # ---------------------------

    debt_equity = info.get("debtToEquity", None)
    current_ratio = info.get("currentRatio", None)

    def eval_debt(de):
        if de is None:
            return "Donnée indisponible"
        if de > 200:
            return "❌ Endettement élevé"
        elif de > 100:
            return "⚠️ Modéré"
        else:
            return "✅ Bon"

    print("📌 SOLIDITÉ FINANCIÈRE")
    print(f" - Ratio dette/capitaux propres : {debt_equity} ({eval_debt(debt_equity)})")
    print(f" - Ratio de liquidité (current) : {current_ratio} ({note_indicateur(current_ratio, (1, 1.5))})" if current_ratio else " - Liquidité : Indispo")
    print("")

    # ---------------------------
    # 4) VALORISATION
    # ---------------------------

    pe = info.get("trailingPE", None)
    pb = info.get("priceToBook", None)
    ps = info.get("priceToSalesTrailing12Months", None)

    print("📌 VALORISATION")
    print(f" - PER : {pe} ({note_indicateur(100/pe if pe else None, (0, 5))})" if pe else " - PER : Indispo")
    print(f" - Price-to-Book : {pb} ({note_indicateur(1/pb*100 if pb else None, (0, 5))})" if pb else " - P/B : Indispo")
    print(f" - Price-to-Sales : {ps}" if ps else " - P/S : Indispo")
    print("")

    # ---------------------------
    # 5) VERDICT FINAL
    # ---------------------------

    print("🎯 **VERDICT GLOBAL (automatique)**")

    score = 0

    # Croissance
    if rev_growth and rev_growth > 5: score += 1
    if eps_growth and eps_growth > 5: score += 1

    # Rentabilité
    if marge_op and marge_op > 0.10: score += 1
    if roe and roe > 0.12: score += 1

    # Solidité
    if debt_equity and debt_equity < 100: score += 1
    if current_ratio and current_ratio > 1.2: score += 1

    # Conclusion
    print(f"\nScore global : {score}/6")

    if score >= 5:
        print("🟩 **Entreprise de grande qualité, tendance long terme potentiellement solide.**")
    elif score >= 3:
        print("🟨 **Entreprise correcte, mais certains points sont à surveiller.**")
    else:
        print("🟥 **Entreprise fragile : non optimale pour un investissement long terme.**")

    print("\n==============================\n")
    

# Exemple
if __name__ == "__main__":
    analyse_fondamentale("MC.PA")  # LVMH
