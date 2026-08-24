"""
Database migration to make patient.last_name nullable.
Run this script to alter the database schema.
"""

from sqlalchemy import create_engine, text
from app.config import settings

def migrate():
    engine = create_engine(str(settings.database_url))
    
    try:
        with engine.connect() as conn:
            print("Modifying patients table to allow NULL in last_name column...")
            
            # Alter the column to allow NULL
            conn.execute(text("""
                ALTER TABLE patients 
                ALTER COLUMN last_name DROP NOT NULL;
            """))
            
            conn.commit()
            print("✅ Successfully modified patients.last_name to allow NULL values.")
            
            # Now update existing "Unknown" values to NULL
            print("\nUpdating existing 'Unknown' values to NULL...")
            result = conn.execute(text("""
                UPDATE patients 
                SET last_name = NULL 
                WHERE last_name = 'Unknown';
            """))
            conn.commit()
            
            rows_updated = result.rowcount
            if rows_updated > 0:
                print(f"✅ Updated {rows_updated} patient record(s) from 'Unknown' to NULL.")
            else:
                print("✅ No patients with 'Unknown' last name found.")
                
    except Exception as e:
        print(f"❌ Error during migration: {e}")
        raise

if __name__ == "__main__":
    print("Starting database migration...")
    migrate()
    print("\n✅ Migration complete!")
