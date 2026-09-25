"""Build and persist the SettingsGraph from the deeplinks catalog."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from troubleir.graph.builder import save_graph, get_screen_index

if __name__ == '__main__':
    print("Building SettingsGraph...")
    save_graph()
    idx = get_screen_index()
    print(f"Graph built: {len(idx)} screen nodes indexed.")
    print("Saved to data/processed/settings_graph.json")
