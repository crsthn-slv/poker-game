import unittest
import threading
import time
import urllib.request
import urllib.parse
import json
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class TestServer(unittest.TestCase):
    BASE_URL = "http://localhost:5001"

    def test_concurrency(self):
        """Test concurrent access to game state"""
        def get_state():
            try:
                with urllib.request.urlopen(f"{self.BASE_URL}/api/game_state") as response:
                    return response.status == 200
            except Exception as e:
                print(f"Error: {e}")
                return False

        threads = []
        results = []
        
        # Start 10 threads accessing game state
        for _ in range(10):
            t = threading.Thread(target=lambda: results.append(get_state()))
            threads.append(t)
            t.start()
            
        for t in threads:
            t.join()
            
        self.assertTrue(all(results), "All concurrent requests should succeed")

    def test_reset_memory(self):
        """Test reset memory endpoint"""
        # Create a dummy memory file
        players_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'players')
        dummy_file = os.path.join(players_dir, 'test_memory.json')
        with open(dummy_file, 'w') as f:
            f.write('{}')
            
        self.assertTrue(os.path.exists(dummy_file))
        
        # Call reset endpoint
        req = urllib.request.Request(f"{self.BASE_URL}/api/reset_memory", method='POST')
        with urllib.request.urlopen(req) as response:
            self.assertEqual(response.status, 200)
        
        # Check if file was deleted
        self.assertFalse(os.path.exists(dummy_file))

if __name__ == '__main__':
    print("Note: Ensure server is running on localhost:5000 before running this test")
    unittest.main()
