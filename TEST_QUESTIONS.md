# 20 TEST QUESTIONS FOR NLQ EFFECTIVENESS EVALUATION
# Based on incident_combine table: incidents from hotel properties

## BASIC RETRIEVAL (Easy - 3 questions)
1. "Show me all incidents"
2. "Get the last 10 incidents"
3. "What incidents happened at The Peninsula Manila?"

## TIME-BASED QUERIES (Easy-Medium - 3 questions)
4. "Show me incidents from today"
5. "What are the most recent incidents?"
6. "Show incidents created in the last 7 days"

## FILTERING BY STATUS/CATEGORY (Easy-Medium - 3 questions)
7. "Show all pending incidents"
8. "What incidents are related to Room Cleanliness?"
9. "Show me high severity incidents that are still pending"

## AGGREGATION & COUNTING (Easy-Medium - 4 questions)
10. "How many incidents are there?"
11. "Count incidents by department"
12. "What is the total potential cost of all incidents?"
13. "How many incidents does each property have?"

## SORTING & TOP N (Medium - 3 questions)
14. "Show me the top 5 incidents by actual cost"
15. "Which department has the most incidents?"
16. "List incidents ordered by severity"

## COMPLEX MULTI-CONDITION (Hard - 2 questions)
17. "Show recent Housekeeping incidents with medium severity"
18. "What is the average actual cost for completed incidents by category?"

## NATURAL LANGUAGE VARIATIONS (Medium-Hard - 2 questions)
19. "Give me a list of problems reported at room 1018"
20. "How much money was spent on compensations?"

---

## TESTING METRICS TO TRACK:
- SQL query generated
- Execution success (yes/no)
- Result accuracy (correct/incorrect/partial)
- Query execution time (ms)
- Confidence score

## SUCCESS CRITERIA:
- Easy questions: >90% accuracy
- Medium questions: >70% accuracy  
- Hard questions: >50% accuracy

## KEY COLUMNS IN incident_combine TABLE:
- property_name, category_name, incident_name, department_name
- severity_name (high/medium/low), status_name (pending/completed/cancelled)
- location_name (room numbers), description
- created_date, incident_time, completed_date, cancelled_date
- potential_cost, actual_cost
- account_uuid, property_uuid
- Partitions: account, property, date
