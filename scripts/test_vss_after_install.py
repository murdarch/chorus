"""Test if VSS extension works after installing dependencies."""

import sqlite3
import sqlite_vss

print("Testing sqlite-vss after installing system dependencies...\n")

conn = sqlite3.connect(':memory:')

try:
    # Enable extension loading (required for security)
    conn.enable_load_extension(True)

    # Use the sqlite_vss.load() helper
    sqlite_vss.load(conn)
    print("✅ sqlite_vss.load() succeeded!")

    # Test VSS functions
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT vss_version()")
        version = cursor.fetchone()
        print(f"✅ VSS Version: {version[0]}")
    except Exception as e:
        print(f"⚠️  vss_version() failed: {e}")

    # Try to create a virtual table
    try:
        cursor.execute("""
            CREATE VIRTUAL TABLE test_vss USING vss0(
                embedding(384)
            )
        """)
        print("✅ Created VSS virtual table successfully!")

        # Insert a test vector
        import numpy as np
        test_vector = np.random.rand(384).astype(np.float32).tobytes()
        cursor.execute("INSERT INTO test_vss(rowid, embedding) VALUES (?, ?)", (1, test_vector))
        print("✅ Inserted test vector successfully!")

        print("\n🎉 SQLITE-VSS IS FULLY WORKING!")

    except Exception as e:
        print(f"❌ Virtual table test failed: {e}")

except Exception as e:
    print(f"❌ Failed to load sqlite-vss: {e}")
    print("\nYou may still need to install system dependencies:")
    print("  sudo apt-get install -y libblas3 liblapack3")

conn.close()
