import sys
from app.database import engine
from sqlalchemy import text

def run_migration():
    with engine.connect() as conn:
        print("Adding claim_number column to risk_scores table if not exists...")
        conn.execute(text("ALTER TABLE risk_scores ADD COLUMN IF NOT EXISTS claim_number VARCHAR(100);"))
        
        print("Backfilling claim_number from claims table...")
        conn.execute(text("""
            UPDATE risk_scores 
            SET claim_number = claims.claim_number 
            FROM claims 
            WHERE risk_scores.claim_id = claims.id;
        """))
        conn.commit()
        print("Migration completed successfully!")

if __name__ == "__main__":
    run_migration()
