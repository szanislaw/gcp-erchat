# NLQ System — Executive Overview

## What It Does

Staff ask questions in plain English. The system finds the answer from the hotel's incident database and displays it instantly — no SQL knowledge, no dashboards to navigate, no waiting for a report.

**Example questions it can answer:**
- *"How many VIP incidents were reported last month?"*
- *"Which department had the most unresolved complaints this week?"*
- *"Show me all high severity incidents at The Peninsula Manila"*
- *"What is the average cost of incidents by category?"*

---

## How It Works — In Plain Terms

```
Staff member types a question
            │
            ▼
    System understands the intent
    (translates "F&B issues" → Food & Beverage,
     "pending" → open complaints, etc.)
            │
            ▼
    AI generates a database query
    (a local AI model, running on our own server,
     never sends data to OpenAI or any external AI)
            │
            ▼
    Query runs against the hotel's live data
    (AWS Athena — the same cloud data warehouse
     already storing incident records)
            │
            ▼
    Results returned in the right format
    (table, bar chart, pie chart, or a single KPI number)
            │
            ▼
    Staff sees the answer in seconds
```

---

## Key Facts

| | |
|---|---|
| **AI model** | Runs entirely on our own server — no data leaves to third-party AI providers |
| **Data source** | AWS Athena (existing cloud data warehouse) |
| **Response time** | ~4–6 seconds end-to-end for a fresh query; under 1 second for repeated questions |
| **Properties supported** | Peninsula Hotels group, Londoner Granded |
| **Access control** | Each query is automatically restricted to the properties the user has access to — it is not possible to query another property's data |

---

## Safety & Access Control

Every query, without exception, is automatically locked to the requesting user's property. The system enforces this at two independent points — even if the AI makes a mistake in the first pass, a second safety check catches and corrects it before any data is returned.

The system also blocks all attempts to modify or delete data. Only read queries are permitted.

```
User at Property A                  User at Property B
asks a question                     asks the same question
        │                                   │
        ▼                                   ▼
Results scoped to                   Results scoped to
Property A data only                Property B data only
(enforced automatically)            (enforced automatically)
```

---

## Self-Healing Queries

If the AI produces a query that doesn't run correctly against the database, the system automatically tries to fix it — up to two times — before returning an error. This happens invisibly in the background.

```
AI writes query → Query fails → System analyses the error
                                        │
                                        ▼
                              AI rewrites the query
                              with the error as guidance
                                        │
                                        ▼
                              Retried automatically
                              (up to 2 attempts)
```

In practice, over 96% of queries succeed on the first try.

---

## Smart Result Formatting

The system automatically chooses the most appropriate way to display each answer:

| Answer type | Display |
|---|---|
| Single number ("How many...") | Large KPI card |
| Comparison across categories | Bar chart |
| Share of a whole | Pie chart |
| Change over time | Line chart |
| List of records | Table |

Staff can also override this if they prefer a different view.

---

## Infrastructure at a Glance

```
┌─────────────────────────────────────────────────┐
│              Our Server (GCP / on-prem)         │
│                                                 │
│   ┌─────────────┐       ┌─────────────────┐    │
│   │  Web / API  │──────▶│  AI Model (7B)  │    │
│   │  (FastAPI)  │       │  runs locally   │    │
│   └──────┬──────┘       └─────────────────┘    │
└──────────┼──────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────────────┐
│              AWS Cloud                          │
│                                                 │
│   ┌─────────────┐       ┌─────────────────┐    │
│   │  AWS Athena │       │   AWS Glue      │    │
│   │ (run query) │       │ (table schema)  │    │
│   └─────────────┘       └─────────────────┘    │
└─────────────────────────────────────────────────┘
```

No external AI APIs (OpenAI, Anthropic, etc.) are used. The AI model runs on our own hardware. Hotel incident data is only ever queried within our own AWS environment.

---

## Limitations to Be Aware Of

- **One data source:** The system currently queries incident records only. Connecting other data sources (e.g. revenue, occupancy) would require additional integration work.
- **English-first:** The question input works best in English. The database itself stores data in English.
- **Row cap:** Results are capped at 100 rows per query to maintain performance. Bulk exports would use a separate reporting tool.
- **Not a replacement for BI tools:** Best suited for ad-hoc operational questions. Complex multi-table analytics with custom visualizations still benefit from a dedicated BI layer.
