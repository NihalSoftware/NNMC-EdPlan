from app.db.base import Base


def test_graduation_audit_source_tables_are_registered_in_metadata():
    assert {"ed_plans", "plan_courses", "programs", "courses"}.issubset(Base.metadata.tables)
