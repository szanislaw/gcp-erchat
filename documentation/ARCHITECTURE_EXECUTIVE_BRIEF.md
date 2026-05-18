# NLQ System — Executive Brief

## What It Does
- Staff ask questions in plain English; system returns answers from the hotel incident database
- No SQL knowledge, no dashboards, no waiting for reports
- Example questions:
  - *"How many VIP incidents were reported last month?"*
  - *"Which department had the most unresolved complaints this week?"*
  - *"Show me all high severity incidents at The Peninsula Manila"*
  - *"What is the average cost of incidents by category?"*

---

## How It Works
1. Staff types a question
2. System translates informal terms (e.g. "F&B" → Food & Beverage, "pending" → open complaints)
3. Local AI model generates a database query
4. Query runs against live hotel data in AWS
5. Results displayed in the right format automatically (chart, table, KPI)
6. Answer returned in ~4–6 seconds

---

## Key Facts
- **AI model** — runs on our own server; no data sent to OpenAI or any external AI provider
- **Data source** — AWS Athena (existing cloud data warehouse)
- **Speed** — 4–6 sec for new queries; under 1 sec for repeated questions
- **Properties** — Peninsula Hotels group, Londoner Granded
- **Access control** — queries are automatically restricted to the user's own properties

---

## Safety & Access Control
- Every query is locked to the requesting user's property — cross-property data access is not possible
- Two independent enforcement points: even if the AI makes a mistake, a second check catches it
- Only read queries permitted — modifying or deleting data is blocked outright

---

## Self-Healing Queries
- If a query fails, the system automatically retries (up to 2 times) using the error as feedback
- Happens invisibly in the background
- **96%+ of queries succeed on the first attempt**

---

## Result Formatting
| Answer type | Display |
|---|---|
| Single number | Large KPI card |
| Comparison across categories | Bar chart |
| Share of a whole | Pie chart |
| Change over time | Line chart |
| List of records | Table |
- Staff can override the auto-selected format

---

## Infrastructure
- AI model runs on our own server (GCP / on-prem) — not a third-party API
- Hotel data stays within our own AWS environment (Athena + Glue)
- No incident data is ever sent outside our infrastructure

---

## Limitations
- **One data source** — incident records only; other data (revenue, occupancy) needs separate integration
- **English-first** — question input and database values are in English
- **100-row cap** — per query; bulk exports require a separate tool
- **Not a BI replacement** — best for ad-hoc operational questions; complex multi-table analytics still need a dedicated BI layer
