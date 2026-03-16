
import os
import sys
import requests
import time
from dotenv import load_dotenv

API_URL = "http://localhost:4001/api/query"

TEST_CATEGORIES = {
    "A) Usage & Adoption": [
        "How many videos are being uploaded, processed, and published over time?"
    ],
    "B) Output Mix & Content Type Trends": [
        "What is the split by output type (reels, shorts, summaries, chapters, etc.)?"
    ],
    "C) Publishing Funnel & Efficiency": [
        "What is the gap between processed and published content?"
    ],
    "D) Team / User / Language / Platform Insights": [
        "Which features or platforms are most active?"
    ],
    "E) Data Quality & Governance": [
        "How much data is missing or marked as 'Unknown'?"
    ]
}

def run_tests():
    print("=" * 80)
    print("🚀 STARTING COMPREHENSIVE BUSINESS LOGIC API TESTS")
    print("=" * 80)
    
    total_passed = 0
    total_failed = 0
    
    for category, questions in TEST_CATEGORIES.items():
        print(f"\n\n{'='*60}\n📂 CATEGORY: {category}\n{'='*60}")
        for i, question in enumerate(questions, 1):
            print(f"\n[Test {i}/{len(questions)}] Question: \"{question}\"")
            
            print("  Querying Agent API (timeout=180s)...")
            start_time = time.time()
            try:
                response = requests.post(API_URL, json={"question": question}, timeout=180)
                response.raise_for_status()
                api_data = response.json()
                duration = time.time() - start_time
                
                print(f"  API Response Time: {duration:.2f}s")
                
                sql = api_data.get("sql", "").strip()
                resp = api_data.get("response", "").strip()
                error = api_data.get("error", "").strip()
                
                if not sql and not error:
                    print("  ⚠️ WARNING: No SQL generated. (Agent might have handled conversationally)")
                    
                if error:
                    print(f"  ❌ FAIL: {error[:200]}")
                    total_failed += 1
                elif "error" in resp.lower() and "400" in resp:
                    print(f"  ❌ FAIL: Internal Agent Error.\n  Snippet: {resp[:200]}")
                    total_failed += 1
                elif not resp:
                    print("  ❌ FAIL: Empty response from agent.")
                    total_failed += 1
                else:
                    print("  ✅ PASS")
                    total_passed += 1
                    
                print("\n  [AGENT SQL]")
                print("  " + (sql.replace("\n", "\n  ") if sql else "None"))
                print("\n  [AGENT RESPONSE (Snippet)]")
                print("  " + resp[:300].replace("\n", "\n  ") + "...")
                
            except requests.exceptions.RequestException as e:
                print(f"  ❌ API REQUEST FAILED: {str(e)}")
                total_failed += 1
                
    print("\n" + "=" * 80)
    print(f"🏁 FINISHED ALL TESTS. Passed: {total_passed}, Failed: {total_failed}")
    print("=" * 80)

if __name__ == "__main__":
    run_tests()
