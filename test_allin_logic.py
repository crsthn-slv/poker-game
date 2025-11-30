#!/usr/bin/env python3
"""
Test script to verify all-in conversion logic.
This simulates the scenario where a player tries to call with insufficient stack.
"""

# Simulate the scenario from the logs
player_stack = 352
call_amount = 460

print(f"Test Scenario:")
print(f"  Player stack: {player_stack}")
print(f"  Call amount: {call_amount}")
print()

# Test the condition
condition_1 = player_stack > 0
condition_2 = call_amount > 0
condition_3 = player_stack <= call_amount

print(f"Condition checks:")
print(f"  player_stack > 0? {condition_1}")
print(f"  call_amount > 0? {condition_2}")
print(f"  player_stack <= call_amount? {condition_3}")
print()

all_conditions = condition_1 and condition_2 and condition_3
print(f"All conditions met? {all_conditions}")
print()

if all_conditions:
    print(f"✓ Should convert to ALL-IN: ('raise', {player_stack})")
else:
    print(f"✗ Would do normal CALL: ('call', {call_amount})")
    print(f"  This is WRONG - player doesn't have enough chips!")
