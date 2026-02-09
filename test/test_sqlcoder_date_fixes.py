from app.sqlcoder import fix_bigint_date_comparisons


def test_rewrites_bigint_date_comparison():
    sql = (
        "SELECT * FROM incident_combine "
        "WHERE created_date <= date_add('day', -7, current_date)"
    )
    fixed = fix_bigint_date_comparisons(sql)
    assert "date_parse(snapshotdate, '%Y-%m-%d') <= date_add('day', -7, current_date)" in fixed


def test_rewrites_aliased_bigint_date_comparison():
    sql = (
        "SELECT * FROM incident_combine t "
        "WHERE t.created_date <= current_date"
    )
    fixed = fix_bigint_date_comparisons(sql)
    assert "t.date_parse" not in fixed
    assert "date_parse(snapshotdate, '%Y-%m-%d') <= current_date" in fixed


def test_keeps_order_by_bigint_timestamp():
    sql = (
        "SELECT * FROM incident_combine "
        "WHERE severity_name = 'medium' "
        "ORDER BY created_date DESC LIMIT 10"
    )
    fixed = fix_bigint_date_comparisons(sql)
    assert fixed == sql
