import sqlite3

conn = sqlite3.connect('entretien_automatise.db')
cur = conn.cursor()

# Check candidates table columns
print("Candidates table columns:")
cur.execute('PRAGMA table_info(candidates)')
columns = cur.fetchall()
for col in columns:
    print(f"  {col[1]}")

# Check candidate data
print("\nCandidate 5 data:")
cur.execute('SELECT * FROM candidates WHERE id = 5')
result = cur.fetchone()
if result:
    for i, col in enumerate(columns):
        print(f"  {col[1]}: {result[i]}")
else:
    print("  No data found")

conn.close()