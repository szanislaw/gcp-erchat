# How the NLQ System Works — Plain English

This document explains what happens when you ask the system a question like *"How many high severity incidents were there last week?"* — from the moment you hit Send to the moment a chart appears on screen.

---

## The Big Picture

Think of this system as a **translator with a fact-checker**. You speak to it in plain English. It translates your question into database language (SQL), asks the database for the answer, and hands the result back in a format your screen can display.

```
You type a question
        ↓
System checks it's safe and not abusive
        ↓
System builds a very detailed question for the AI
        ↓
AI writes a database query (SQL)
        ↓
System fixes common AI mistakes automatically
        ↓
Database runs the query and returns data
        ↓
System decides how best to display the result
        ↓
You see a chart, table, or number on screen
```

---

## Step by Step

### 1. Your Question Gets Checked for Safety

Before anything else, the system reads your question and checks for anything dangerous — things like hidden code or attempts to manipulate the system. It also cleans up the text (removes stray symbols, trims it to a sensible length).

**Think of it as:** A security guard at the door checking your ID before letting you in.

If anything looks suspicious, the request is blocked immediately with a clear error message. Nothing dangerous ever reaches the AI.

---

### 2. Traffic Control

The system limits how many questions can be processed per second (maximum 2 per second, with short bursts of up to 10). This prevents the AI — which is slow and computationally expensive — from being overwhelmed.

**Think of it as:** A bouncer managing the queue outside a club. If too many people arrive at once, you're asked to wait a moment and try again.

If you're over the limit, the system tells you exactly how many seconds to wait before retrying.

---

### 3. Picking the Right Database

The system supports multiple hotel data sets. Based on your request, it picks which one to use — for example, Peninsula Hotels data or Londoner Granded data. This determines which tables and columns are available.

**Think of it as:** Choosing which filing cabinet to open before searching for a document.

---

### 4. Preparing the Question for the AI

This is the most complex step. The system doesn't just hand your raw question to the AI — it builds a rich, structured brief first.

**4a. Translating your words into database language**

Many words have standard equivalents in the database. The system automatically converts them:

- "Bangkok" → "The Peninsula Bangkok"
- "F&B" → "Food & Beverage"
- "open" → "pending"
- "done" → "completed"
- "serious" → "high"
- "leak" → "Plumbing / Drainage Issue"
- "room 1018" → "Room 1018"

This means you can use casual language and abbreviations — the system handles the translation.

**4b. Telling the AI exactly what "last week" means**

Dates are tricky. "Last week" could mean the rolling past 7 days, or it could mean Monday to Sunday of the previous calendar week. The system decides the correct interpretation and gives the AI the exact date calculation to use — no guessing.

**4c. Telling the AI what the database looks like**

The system fetches the database structure (column names, data types, partition keys) from AWS and converts it into a format the AI understands. It also fetches the actual values that exist in key columns — for example, it tells the AI that severity can be "high", "medium", "low", or "critical" — so the AI uses the exact right words.

**4d. Adding security rules**

Every query must be limited to data the user is allowed to see. The system injects a mandatory filter like "only show data for properties X and Y" into every single prompt. The AI cannot omit this.

**4e. Writing the final brief**

All of the above is assembled into a structured document that tells the AI:
- What question to answer
- The exact database structure (as SQL table definitions)
- 30+ rules about how to write correct queries for this specific database
- Any entity hints (e.g. "use severity_name = 'high'")
- Any date hints (e.g. "use this exact date calculation for last week")

**Think of it as:** A project manager writing a detailed spec sheet for a contractor, rather than just saying "build me a website."

---

### 5. The AI Writes the Query

The AI (a language model fine-tuned for SQL generation) reads the full brief and writes a SQL query. This step takes the most time — typically 1–3 seconds — because it runs on a GPU.

The result of queries are cached: if the exact same question has been asked before, the cached answer is returned instantly instead of running the AI again.

**Think of it as:** A specialist translator who reads your brief and writes the query. If they've translated the exact same thing before, they hand you the previous translation.

---

### 6. Automatic Error Correction (Round 1)

The AI is good but not perfect. Before the query is even checked, the system automatically fixes common mistakes the AI makes:

| What the AI wrote | What it should be | Why |
|---|---|---|
| `year(snapshotdate)` | `year(date_parse(snapshotdate, '%Y-%m-%d'))` | The date column is stored as text, not a real date |
| `current_date - INTERVAL '7 days'` | `date_add('day', -7, current_date)` | This database doesn't support that syntax |
| `GROUP BY month_label` | `GROUP BY 1` | This database doesn't allow column aliases in GROUP BY |

These fixes happen automatically, silently, every time. You never see them.

---

### 7. Automatic Error Correction (Round 2)

A second round of fixes runs using context from your request — specifically, which tables are allowed and which hotels you have access to:

| What the AI wrote | What it should be | Why |
|---|---|---|
| `incident_combine_2025` | `incident_combine` | The AI invented a table name that doesn't exist |
| `CAST(x AS FLOAT)` | `CAST(x AS DOUBLE)` | This database has no FLOAT type |
| `WHERE property_name IN ('uuid')` | `WHERE property IN ('uuid')` | The AI used the display name column instead of the ID column |
| *(no property filter at all)* | `WHERE property IN ('uuid1', 'uuid2')` | The AI dropped a mandatory security filter — it's injected back |

**The property filter** (which hotels you're allowed to see) has two separate safety nets: one that fixes the wrong column name, and one that adds the filter back if the AI dropped it entirely. This is intentional — it's a security boundary, not just a data quality check.

---

### 8. Security Check

The fixed query goes through a final security check before touching the database:

- **No dangerous operations** — DROP, DELETE, UPDATE, INSERT, and similar commands are blocked
- **No unsupported syntax** — certain SQL features that could cause errors are rejected
- **Table access control** — if the query tries to read from a table the user isn't allowed to access, it's blocked

**Think of it as:** A legal review before a contract is signed.

---

### 9. Running the Query (or Skipping It)

If `dry_run` is enabled, this step is skipped entirely — the system just returns the SQL it would have run. This is useful for testing.

Otherwise, the query is sent to AWS Athena (Amazon's cloud database service). The system waits for the result, polling every fraction of a second.

**AWS also caches results:** if the exact same query was run within the last hour, Athena returns the cached result instead of re-scanning the data. This makes repeated queries much faster.

#### What happens if the query fails?

If Athena returns an error, the system doesn't give up — it tries to fix the query automatically:

1. Takes the failed query and the exact error message
2. Asks the AI to write a corrected version, explaining what went wrong
3. Runs the same safety checks on the new version
4. Tries Athena again

This retry loop runs up to **2 times**. If all retries fail, the error is returned to the user.

**Think of it as:** Sending a letter, getting it returned with a correction note, rewriting it, and sending again — but limited to 2 attempts so it doesn't go on forever.

---

### 10. Making Column Names Human-Readable

The database uses technical column names like `snapshotdate`, `category_name`, `actual_cost`. Before showing the data to you, the system converts these to readable labels:

| Database name | Display name |
|---|---|
| `snapshotdate` | Date |
| `category_name` | Category |
| `department_name` | Department |
| `actual_cost` | Actual Cost |
| `vip` | VIP |
| `severity_name` | Severity |

This happens automatically for every result.

---

### 11. Deciding How to Display the Result

The system picks the best visual format for your answer based on four levels of rules (checked in order):

**Level 1 — You specified it.** If your request includes a display type (e.g. "show as bar chart"), that wins.

**Level 2 — It's a known question.** 60 common questions are hardcoded with their ideal display type. "How many total incidents?" always shows as a single number (metric). "Status distribution" always shows as a pie chart.

**Level 3 — Pattern matching.** Questions starting with "how many" → single number. Questions containing "trend" or "per month" → line chart. Questions about breakdowns → pie chart. Questions about counts by department/category → bar chart.

**Level 4 — Analyse the data.** If nothing else works, the system looks at the actual result — how many rows, how many columns, whether there's a date column, whether there's aggregation — and picks the most sensible format.

**Supported display types:** table, metric (single number), bar chart, pie chart, line chart, card, list

---

### 12. Packaging the Result

Everything is assembled into a single response:

- **The SQL query** that was run (so you can inspect or copy it)
- **The data** (rows and columns, with readable column names)
- **The display format** chosen (and chart-ready data if it's a chart)
- **Timing breakdown** — how long each step took (prompt building, AI inference, Athena execution, etc.)
- **How many self-correction attempts** were needed (usually 0)

The full request and response are also saved to a log file so they can be reviewed later.

---

## Why Things Are Done This Way

**Why so many automatic fixes?**
The AI was trained on many databases and often makes mistakes specific to this one — wrong date syntax, wrong column names, dropped filters. Rather than training the AI from scratch, it's faster and more reliable to fix known failure patterns automatically.

**Why two rounds of fixes?**
The first round fixes general AI output mistakes (syntax, type issues). The second round needs to know which tables and users are involved — information only available from the request. Splitting them keeps the logic clean.

**Why is the property filter added by the system, not just relied on from the AI?**
Because it's a security boundary. The AI occasionally drops this filter when writing complex queries. Having the system enforce it independently means a forgotten filter can never expose data the user isn't authorised to see.

**Why does the system cache so many things?**
The AI and the database are the two slowest parts. Caching the AI's output means repeated questions are instant. Caching the database schema means the system doesn't need to ask AWS what the table looks like on every request.

**Why limit to 100 rows?**
Returning thousands of rows would be slow, expensive, and mostly useless for a dashboard. The 100-row limit keeps responses fast and displays readable. For aggregate queries (counts, sums, averages), you rarely need more than a handful of rows anyway.
