#!/usr/bin/env python3
"""
Simple test to verify the quiz app can load questions correctly
"""
import sys
sys.path.insert(0, '/Users/aap/Code/uni-programs/ipb/uts-mc')

from quiz_app import load_questions

# Test loading questions
questions = load_questions('/Users/aap/Code/uni-programs/ipb/uts-mc/multichoice-uts-mankeb.csv')

if questions:
    print(f"✓ Successfully loaded {len(questions)} questions")
    print("\nFirst question:")
    print(f"  Q: {questions[0]['question']}")
    print(f"  Options: {len(questions[0]['options'])} choices")
    print(f"  Answer: {questions[0]['answer']}")
    print("\n✓ Quiz app is working correctly!")
else:
    print("✗ Failed to load questions")
