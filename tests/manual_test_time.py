import asyncio
import logging
import sys
import os
sys.path.append(os.getcwd())

# Setup Logging
logging.basicConfig(level=logging.INFO)

async def run_tests():
    # Import inside verify to use the updated file
    from skills.time import GetTimeSkill
    
    skill = GetTimeSkill()
    context = {} # Context not used heavily here
    
    print("--- Test 1: Get Time ---")
    res = await skill.execute(context)
    print(res)
    
    assert "time" in res, "Missing time field"
    assert "date" in res, "Missing date field"
    assert "weekday" in res, "Missing weekday field"
    assert "info" in res, "Missing formatted info"
    
    print(f"Formatted Output: {res['info']}")
    print("\nALL TESTS PASSED!")

if __name__ == "__main__":
    asyncio.run(run_tests())
