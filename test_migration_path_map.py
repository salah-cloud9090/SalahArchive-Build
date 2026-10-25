import unittest
from migration_path_map import build_map

class MigrationPathMapTests(unittest.TestCase):
    def test_maps_sqlite_markers_without_executing_source(self):
        source = '''\nimport sqlite3\ndef db():\n    return sqlite3.connect("archive.db")\ndef create_scan():\n    c.execute("INSERT OR IGNORE INTO scan_baskets(name) VALUES (?)")\n    c.execute("PRAGMA table_info(scan_baskets)")\n'''
        report = build_map(source)
        self.assertEqual(report["marker_counts"]["sqlite_connect"], 1)
        self.assertEqual(report["marker_counts"]["insert_or_ignore"], 1)
        self.assertEqual(report["marker_counts"]["pragma"], 1)
        self.assertTrue(any(x["function"] == "create_scan" for x in report["findings"]))

    def test_empty_source_is_valid(self):
        report = build_map("# no markers\n")
        self.assertEqual(report["total_findings"], 0)

if __name__ == "__main__":
    unittest.main(verbosity=2)
