import re

def preprocess(text):
    # Current regex
    return re.sub(r'(?i)\b(?:as|às|at)\s+(\d{1,2})[hH]\b', r'às \1:00', text)

def test(t):
    res = preprocess(t)
    print(f"'{t}' -> '{res}'")
    if t != res and "30" in t and "0030" in res:
        print("FAIL: Broke 10h30 format")
    elif t == res and "30" in t:
         print("PASS: Preserved 10h30 format")

print("--- Testing Regex ---")
test("amanhã as 10h")
test("amanhã as 10h30")
test("amanhã às 10H")
test("amanhã at 09h")
test("amanhã as 10") # Test if 'as 10' is handled

