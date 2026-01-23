"""
Test Questions for NLQ → SQL Effectiveness Testing
Based on incident_combine table schema analysis
"""

# 20 TEST QUESTIONS FOR NLQ EFFECTIVENESS

test_questions = [
    # === BASIC RETRIEVAL (Questions 1-3) ===
    {
        "id": 1,
        "category": "Basic Retrieval",
        "question": "Show me all incidents",
        "difficulty": "Easy",
        "expected_behavior": "Should retrieve all incidents with LIMIT 100"
    },
    {
        "id": 2,
        "category": "Basic Retrieval",
        "question": "Get the last 10 incidents",
        "difficulty": "Easy",
        "expected_behavior": "Should limit to 10 rows, ordered by recent date"
    },
    {
        "id": 3,
        "category": "Basic Retrieval",
        "question": "What incidents happened at The Peninsula Manila?",
        "difficulty": "Easy",
        "expected_behavior": "Should filter by property_name = 'The Peninsula Manila'"
    },
    
    # === TIME-BASED QUERIES (Questions 4-6) ===
    {
        "id": 4,
        "category": "Time-Based",
        "question": "Show me incidents from today",
        "difficulty": "Medium",
        "expected_behavior": "Should filter by current date using date partition or created_date"
    },
    {
        "id": 5,
        "category": "Time-Based",
        "question": "What are the most recent incidents?",
        "difficulty": "Easy",
        "expected_behavior": "Should order by created_date DESC or use MAX(created_date)"
    },
    {
        "id": 6,
        "category": "Time-Based",
        "question": "Show incidents created in the last 7 days",
        "difficulty": "Medium",
        "expected_behavior": "Should calculate date range and filter appropriately"
    },
    
    # === FILTERING BY STATUS/CATEGORY (Questions 7-9) ===
    {
        "id": 7,
        "category": "Filtering",
        "question": "Show all pending incidents",
        "difficulty": "Easy",
        "expected_behavior": "Should filter status_name = 'pending'"
    },
    {
        "id": 8,
        "category": "Filtering",
        "question": "What incidents are related to Room Cleanliness?",
        "difficulty": "Easy",
        "expected_behavior": "Should filter category_name or incident_name with 'Room Cleanliness'"
    },
    {
        "id": 9,
        "category": "Filtering",
        "question": "Show me high severity incidents that are still pending",
        "difficulty": "Medium",
        "expected_behavior": "Should filter by severity_name = 'high' AND status_name = 'pending'"
    },
    
    # === AGGREGATION & COUNTING (Questions 10-13) ===
    {
        "id": 10,
        "category": "Aggregation",
        "question": "How many incidents are there?",
        "difficulty": "Easy",
        "expected_behavior": "Should use COUNT(*)"
    },
    {
        "id": 11,
        "category": "Aggregation",
        "question": "Count incidents by department",
        "difficulty": "Medium",
        "expected_behavior": "Should GROUP BY department_name with COUNT"
    },
    {
        "id": 12,
        "category": "Aggregation",
        "question": "What is the total potential cost of all incidents?",
        "difficulty": "Medium",
        "expected_behavior": "Should use SUM(potential_cost)"
    },
    {
        "id": 13,
        "category": "Aggregation",
        "question": "How many incidents does each property have?",
        "difficulty": "Medium",
        "expected_behavior": "Should GROUP BY property_name with COUNT"
    },
    
    # === SORTING & TOP N (Questions 14-16) ===
    {
        "id": 14,
        "category": "Top N",
        "question": "Show me the top 5 incidents by actual cost",
        "difficulty": "Medium",
        "expected_behavior": "Should ORDER BY actual_cost DESC LIMIT 5"
    },
    {
        "id": 15,
        "category": "Top N",
        "question": "Which department has the most incidents?",
        "difficulty": "Hard",
        "expected_behavior": "Should GROUP BY department_name, COUNT, then ORDER BY count DESC LIMIT 1"
    },
    {
        "id": 16,
        "category": "Sorting",
        "question": "List incidents ordered by severity",
        "difficulty": "Medium",
        "expected_behavior": "Should ORDER BY severity_name (may need CASE for high/medium/low)"
    },
    
    # === COMPLEX MULTI-CONDITION (Questions 17-18) ===
    {
        "id": 17,
        "category": "Complex",
        "question": "Show recent Housekeeping incidents with medium severity",
        "difficulty": "Hard",
        "expected_behavior": "Should filter by department_name='Housekeeping', severity_name='medium', and recent date"
    },
    {
        "id": 18,
        "category": "Complex",
        "question": "What is the average actual cost for completed incidents by category?",
        "difficulty": "Hard",
        "expected_behavior": "Should filter status_name='completed', GROUP BY category_name, AVG(actual_cost)"
    },
    
    # === NATURAL LANGUAGE VARIATIONS (Questions 19-20) ===
    {
        "id": 19,
        "category": "Natural Variation",
        "question": "Give me a list of problems reported at room 1018",
        "difficulty": "Medium",
        "expected_behavior": "Should filter location_name = '1018' (understanding 'problems' = incidents)"
    },
    {
        "id": 20,
        "category": "Natural Variation",
        "question": "How much money was spent on compensations?",
        "difficulty": "Hard",
        "expected_behavior": "Should SUM actual_cost (understanding 'compensations' relates to costs)"
    }
]

# Export as formatted output
if __name__ == "__main__":
    print("=" * 80)
    print("20 TEST QUESTIONS FOR NLQ EFFECTIVENESS EVALUATION")
    print("=" * 80)
    print()
    
    categories = {}
    for q in test_questions:
        cat = q["category"]
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(q)
    
    for category, questions in categories.items():
        print(f"\n{'=' * 80}")
        print(f"{category.upper()} ({len(questions)} questions)")
        print('=' * 80)
        
        for q in questions:
            print(f"\n[Q{q['id']}] {q['difficulty']}")
            print(f"Question: {q['question']}")
            print(f"Expected: {q['expected_behavior']}")
    
    print("\n" + "=" * 80)
    print("DIFFICULTY BREAKDOWN:")
    print("=" * 80)
    difficulty_count = {}
    for q in test_questions:
        diff = q["difficulty"]
        difficulty_count[diff] = difficulty_count.get(diff, 0) + 1
    
    for diff, count in sorted(difficulty_count.items()):
        print(f"  {diff}: {count} questions")
    
    print("\n" + "=" * 80)
    print("TESTING INSTRUCTIONS:")
    print("=" * 80)
    print("""
1. Run each question through the /nlq/execute endpoint
2. Record the following metrics:
   - SQL query generated
   - Execution success (yes/no)
   - Result accuracy (correct/incorrect/partial)
   - Query time (ms)
   - Confidence score

3. Success criteria:
   - Easy questions: >90% accuracy
   - Medium questions: >70% accuracy
   - Hard questions: >50% accuracy
   
4. Common issues to watch for:
   - Incorrect column references
   - Missing WHERE clauses
   - Wrong aggregation functions
   - Date/time handling errors
   - Natural language ambiguity
    """)
