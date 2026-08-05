#!/usr/bin/env python3
"""
Test suite for the output-side JSON unwrapping in process_v2.py.

Tests the unwrap_model_response() function and the _strip_build_json_from_text()
helper against all known leakage patterns from the playtest.

Run: python3 test_unwrapper.py
"""
import json, re, sys

# Import the unwrapper functions
_re = re
code = open('process_v2.py').read()
start = code.index('def _strip_markdown_fences')
end = code.index('# ─── Vectorize API')
exec(code[start:end])

passed = 0
failed = 0

def check(name, condition, detail=""):
    global passed, failed
    if condition:
        passed += 1
    else:
        failed += 1
        print(f"  ✗ FAIL: {name} — {detail}")

def test_case(name, raw_input, expect_reply_contains=None, expect_json_leak=False,
              expect_commands=None):
    """Run a test case and verify results."""
    result = unwrap_model_response(raw_input)
    reply = result["reply"]
    commands = result["commands"]

    # Check for JSON leakage
    json_leak = (
        '{"type"' in reply or
        '"createPart"' in reply or
        '"addLight"' in reply or
        '"commands"' in reply[:100] or
        '"reply"' in reply[:50]
    )

    if expect_reply_contains:
        check(f"{name}: reply contains '{expect_reply_contains}'",
              expect_reply_contains.lower() in reply.lower(),
              f"reply was: {reply[:100]}")

    check(f"{name}: no JSON leakage", not json_leak == (not expect_json_leak),
          f"json_leak={json_leak}, expected_json_leak={expect_json_leak}, reply={reply[:100]}")

    if expect_commands is not None:
        check(f"{name}: command count", len(commands) == expect_commands,
              f"expected {expect_commands}, got {len(commands)}")


# ─── Test Cases ─────────────────────────────────────────────────────────────

print("=== Output-Side JSON Unwrapper Tests ===\n")

# 1. Clean JSON — baseline
test_case("Clean JSON",
    '{"reply": "Tower is up.", "commands": [{"type": "createPart", "params": {"name": "T"}}]}',
    expect_reply_contains="Tower is up",
    expect_commands=1,
)

# 2. Double-encoded reply (JSON string inside reply field)
test_case("Double-encoded reply",
    '{"reply": "{\\"reply\\": \\"Tower is up.\\", \\"commands\\": []}", "commands": []}',
    expect_reply_contains="Tower is up",
)

# 3. Conversational (no JSON)
test_case("Conversational",
    "I cannot build that, sorry.",
    expect_reply_contains="sorry",
)

# 4. Markdown fenced JSON
test_case("Markdown fenced",
    '```json\n{"reply": "Done.", "commands": []}\n```',
    expect_reply_contains="Done",
)

# 5. Prose + JSON
test_case("Prose + JSON",
    'Sure thing! Here you go:\n{"reply": "Built it.", "commands": []}',
    expect_reply_contains="Built it",
)

# 6. Reply is a dict (object)
test_case("Reply is dict",
    '{"reply": {"text": "Tower built"}, "commands": []}',
    expect_reply_contains="Tower built",
)

# 7. Build commands embedded in reply text
test_case("Commands in reply text",
    '{"reply": "Built a tower with {\\"type\\": \\"createPart\\", \\"params\\": {\\"name\\": \\"Tower\\"}}, here you go!", "commands": []}',
    expect_reply_contains="here you go",
)

# 8. Double-stringified entire response
test_case("Everything as string",
    '"{\\"reply\\": \\"Built it\\", \\"commands\\": []}"',
    expect_reply_contains="Built it",
)

# 9. Multiple JSON objects
test_case("Multiple JSON objects",
    '{"reply": "Thinking..."}{"reply": "Done!", "commands": [{"type": "createPart", "params": {"name": "T"}}]}',
    expect_reply_contains="Done",
)

# 10. Reply contains "reply" key as part of sentence
test_case("Reply mentions JSON keys naturally",
    'Here is what I built: {"reply": "Tower", "commands": [{"type": "createPart", "params": {"name": "T"}}]}',
    expect_reply_contains="Tower",
    expect_commands=1,
)

# 11. Empty string
test_case("Empty string", "", expect_reply_contains="")

# 12. Just whitespace
test_case("Whitespace", "   \n  ", expect_reply_contains="")

# 13. Unquoted keys (granite 2B style)
test_case("Unquoted keys",
    '{reply: "Built it.", commands: [{type: "createPart", params: {name: "T"}}]}',
    expect_reply_contains="Built it",
    expect_commands=1,
)

# 14. Brain.py safety rejection
test_case("Safety rejection",
    '{"reply": "Not building that. Pick something else.", "commands": [], "_meta": {"model": "Qwen/Qwen3-Coder-480B-A35B-Instruct-Turbo", "latency_s": 1.7}}',
    expect_reply_contains="Not building that",
)

# 15. JSON with nested _meta
test_case("JSON with _meta",
    '{"reply": "Tower is up.", "commands": [{"type": "createPart", "params": {"name": "T"}}], "_meta": {"model": "test", "latency_s": 0.5}}',
    expect_reply_contains="Tower is up",
    expect_commands=1,
)

# 16. Reply with escaped quotes in the text
test_case("Escaped quotes in reply",
    '{"reply": "He said \\"hello\\" and built a wall.", "commands": []}',
    expect_reply_contains="hello",
)

# 17. Very long prose before JSON
test_case("Long prose before JSON",
    'I would be happy to help you build that. Let me think about the best approach for this construction project. You want something sturdy, something that will last. Well, I have just the thing.\n\n{"reply": "Tower is up.", "commands": [{"type": "createPart", "params": {"name": "Tower"}}]}',
    expect_reply_contains="Tower is up",
    expect_commands=1,
)

# 18. _strip_build_json_from_text direct test
print("--- Direct helper tests ---")
stripped = _strip_build_json_from_text('Built it with {"type": "createPart", "params": {"name": "T"}} and done')
check("strip build json: preserves prose", "Built it with" in stripped, f"got: {stripped[:80]}")
check("strip build json: removes JSON", '"createPart"' not in stripped, f"got: {stripped[:80]}")

stripped2 = _strip_build_json_from_text("No JSON here at all")
check("strip build json: passthrough when no JSON", stripped2 == "No JSON here at all")

# ─── Results ────────────────────────────────────────────────────────────────

print(f"\n{'='*50}")
print(f"Results: {passed} passed, {failed} failed")
if failed:
    print("❌ Some tests failed")
    sys.exit(1)
else:
    print("✅ All tests passed")
