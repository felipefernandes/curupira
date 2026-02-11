import dateparser
from datetime import datetime

def test_parse(input_str):
    settings = {'PREFER_DATES_FROM': 'future', 'DATE_ORDER': 'DMY'}
    # Mock "now" isn't directly supported by dateparser.parse without a trick, 
    # but we can rely on system time being relatively constant involved in the logic.
    # Actually, dateparser uses datetime.now() internally.
    
    print(f"Input: '{input_str}'")
    res = dateparser.parse(input_str, settings=settings)
    print(f"Result: {res}")
    
    now = datetime.now()
    if res:
        diff = res - now
        print(f"Difference from now: {diff}")
    print("-" * 20)



print("\n--- Testing Fixes (Smarter Regex) ---")
import re

def fix_time(s):
    # Regex to replace '10h' or '9h' with '10:00'
    # BUT NOT if preceded by 'em ', 'sem ', 'daqui a ', 'in '
    # Note: 'daqui a' implies relative. 'em' implies relative.
    
    # Case 1: Explicit "as/às/at" -> Always absolute
    s = re.sub(r'(?i)\b(?:as|às|at)\s+(\d{1,2})[hH]\b', r'às \1:00', s)
    
    # Case 2: "10h" without "em/daqui a" before it.
    # Lookbehind in python re is fixed width, so we can't do (?<!daqui a ). 
    # We'll use a specific replace approach or handle the "daqui a" case separately.
    
    # Alternative: If "daqui" or "em" is in the string, assume relative and DON'T touch 'Xh'? 
    # But "daqui a 2 dias as 10h" mixes both.
    
    # Let's try to match the "relative markers" and if found, ignore the *immediate* following time?
    # Or just replace "Xh" with "X:00" unless it looks like a duration.
    
    # Simplest safe fix for now: Handle "as 10h" specifically, as that was the user's input.
    # User said: "amanhã as 10h".
    
    # Case 3: Cleanup "na ", "no ", "em " before weekdays or general
    # Also " feira" -> "" (dateparser handles "sexta" better than "sexta feira" sometimes?)
    
    # Remove "na ", "no ", "em " at start or after space
    s = re.sub(r'(?i)\b(?:na|no|em)\s+', '', s)
    
    # Remove " feira" (optional)
    s = re.sub(r'(?i)\s+feira\b', '', s)
    
    # Remove "próxima " (let dateparser handle future preference)
    s = re.sub(r'(?i)\bpróxima\s+', '', s)
    
    return s

test_parse(fix_time("amanhã as 10h"))
test_parse(fix_time("amanhã às 10h"))
test_parse(fix_time("amanhã 10h"))
test_parse(fix_time("daqui a 10h"))

print("\n--- Testing Weekdays (Fixed) ---")
test_parse(fix_time("sexta"))
test_parse(fix_time("na próxima sexta"))
test_parse(fix_time("sexta feira"))
test_parse(fix_time("na sexta"))
