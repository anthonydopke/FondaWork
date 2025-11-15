# **FondaWork — Fundamental Analysis Automation**

FondaWork is a lightweight, extensible Python project designed to automate the process of **fundamental analysis** for stocks.  
It provides a clean modular architecture that fetches data, computes indicators, rates companies, and generates a full analysis report for the user.

The goal is to make fundamental analysis **accessible**, even for users with no programming knowledge.

---

##  Features

- **Automatic ticker resolution**  
  - Uses curated mapping (CAC40 + major US equities)  
  - Falls back to Yahoo Finance unofficial autocomplete API  
  - Works with almost any company name worldwide

- **Modular design**  
  Each responsibility is in its own file:
  - `data_fetcher.py` → Downloads financial statements & key metrics  
  - `fundamental_analysis.py` → Computes ratios & trends  
  - `rating_engine.py` → Scores the company  
  - `result_builder.py` → Produces a clean textual analysis  
  - `stock_map.py` → Ticker resolution logic  
  - `main.py` → User-facing entry point


- **Minimal dependencies**: `yfinance`, `requests`, `pandas`

---


## 📦 Installation

Clone the repository:

```bash
git clone https://github.com/anthonydopke/FondaWork.git
cd FondaWork
pip install -r requirements.txt
python main.py

```


