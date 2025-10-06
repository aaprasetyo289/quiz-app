#!/usr/bin/env python3
"""
Simple validation script to check if the Streamlit app is properly configured.
"""
import sys
import os

print("=" * 50)
print("Quiz Webapp Validation")
print("=" * 50)

# Check imports
print("\n1. Checking required imports...")
try:
    import streamlit as st
    print("   ✓ streamlit")
except ImportError:
    print("   ✗ streamlit (NOT INSTALLED)")
    sys.exit(1)

try:
    import pandas as pd
    print("   ✓ pandas")
except ImportError:
    print("   ✗ pandas (NOT INSTALLED)")
    sys.exit(1)

try:
    from google.cloud import firestore
    print("   ✓ google-cloud-firestore")
except ImportError:
    print("   ⚠ google-cloud-firestore (NOT INSTALLED - needed for save/load)")

# Check if CSV file exists
print("\n2. Checking data files...")
csv_file = "multichoice-uts-mankeb.csv"
if os.path.exists(csv_file):
    print(f"   ✓ {csv_file} found")
    # Try to read it
    try:
        df = pd.read_csv(csv_file)
        print(f"   ✓ CSV has {len(df)} rows")
        print(f"   ✓ Columns: {list(df.columns)}")
    except Exception as e:
        print(f"   ✗ Error reading CSV: {e}")
else:
    print(f"   ✗ {csv_file} NOT FOUND")

# Check if the app file has correct structure
print("\n3. Checking app structure...")
try:
    with open("quiz_webapp.py", "r") as f:
        content = f.read()
        
    # Check for key components
    checks = [
        ("load_questions function", "def load_questions("),
        ("save_state function", "def save_state("),
        ("load_state function", "def load_state("),
        ("Screen 1 logic", "Screen 1: Subject Selection"),
        ("Screen 2 logic", "Screen 2: Quiz Configuration"),
        ("Screen 3 logic", "Screen 3: The Quiz"),
    ]
    
    for name, pattern in checks:
        if pattern in content:
            print(f"   ✓ {name}")
        else:
            print(f"   ✗ {name} MISSING")

except Exception as e:
    print(f"   ✗ Error reading app file: {e}")

print("\n" + "=" * 50)
print("Validation complete!")
print("=" * 50)
print("\nTo run the app:")
print("  streamlit run quiz_webapp.py")
print("\nNote: Save/Load features require:")
print("  - google-cloud-firestore package")
print("  - Firestore credentials in .streamlit/secrets.toml")
