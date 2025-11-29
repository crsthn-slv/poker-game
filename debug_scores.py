
import sys
import os

# Add current directory to path
sys.path.append(os.getcwd())

try:
    from utils.hand_evaluator import HandEvaluator
    from utils.hand_utils import score_to_hand_name
    
    evaluator = HandEvaluator()
    
    scenarios = [
        (['SA', 'SK', 'SQ', 'SJ', 'ST'], "Royal Flush"),
        (['SA', 'SK', 'SQ', 'SJ', 'S9'], "Flush (Ace High)"),
        (['SA', 'HA', 'DA', 'CA', 'SK'], "Four of a Kind (Aces)"),
        (['SA', 'HA', 'DA', 'SK', 'HK'], "Full House (Aces full of Kings)"),
        (['SA', 'HA', 'DA', 'SK', 'SQ'], "Three of a Kind (Aces)"),
        (['SA', 'HA', 'SK', 'HK', 'SQ'], "Two Pair (Aces and Kings)"),
        (['SA', 'HA', 'SK', 'SQ', 'SJ'], "One Pair (Aces)"),
        (['S2', 'H2', 'S3', 'S4', 'S5'], "One Pair (Twos)"),
        (['SA', 'SK', 'SQ', 'SJ', 'H9'], "High Card (Ace)"),
        (['S7', 'S5', 'S4', 'S3', 'H2'], "High Card (7-high - Worst Hand?)"),
    ]
    
    print(f"{'Hand Name':<30} | {'Score':<10} | {'Category'}")
    print("-" * 60)
    
    for cards, name in scenarios:
        # Split into hole and community (2 + 3)
        hole = cards[:2]
        comm = cards[2:]
        
        score = evaluator.evaluate(hole, comm)
        category = score_to_hand_name(score)
        
        print(f"{name:<30} | {score:<10} | {category}")

except ImportError:
    print("PokerKit not installed or utils not found.")
except Exception as e:
    print(f"Error: {e}")
