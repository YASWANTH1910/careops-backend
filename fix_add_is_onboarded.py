"""
One-shot migration script — adds is_onboarded column to businesses table.
Run with: python fix_add_is_onboarded.py
"""
from app.core.database import engine
from sqlalchemy import text, inspect

def main():
    insp = inspect(engine)
    cols = [c['name'] for c in insp.get_columns('businesses')]
    print(f"Current columns: {cols}")

    if 'is_onboarded' in cols:
        print("✅ is_onboarded already exists — nothing to do.")
        return

    with engine.connect() as conn:
        conn.execute(text(
            "ALTER TABLE businesses ADD COLUMN is_onboarded BOOLEAN NOT NULL DEFAULT 0"
        ))
        conn.commit()

    # Verify
    cols_after = [c['name'] for c in inspect(engine).get_columns('businesses')]
    print(f"✅ Done! Columns now: {cols_after}")

if __name__ == "__main__":
    main()
