# -*- coding: utf-8 -*-
import unittest, tempfile
from pathlib import Path
from mysql_schema_manager import split_sql_statements, expected_columns, SchemaPreflightError, ensure_schema


class FakeCursor:
    def __init__(self, existing=None):
        self.existing=existing or {}
        self.last_sql=""
        self.last_params=()
        self.ddl=[]
        self._one=None
        self._all=[]
        self.foreign_keys = {}
    def execute(self, sql, params=None):
        self.last_sql=sql
        self.last_params=params or ()
        self._one=None
        self._all=[]
        if sql=="SELECT DATABASE()":
            self._one=("salah_archive_test",)
        elif "information_schema.tables" in sql:
            name=self.last_params[0]
            if name in self.existing: self._one=(name,)
        elif sql.startswith("SHOW COLUMNS FROM"):
            name=sql.split("`")[1]
            self._all=[]
            for col in self.existing.get(name,[]):
                self._all.append(tuple(col) if isinstance(col, (tuple, list)) else (col, None))
        elif sql.startswith("SHOW INDEX FROM"):
            name=sql.split("`")[1]
            # The legacy fake schema only models columns, so model the common id PRIMARY KEY.
            # Dedicated tests may override this with an explicit index map.
            indexes = getattr(self, "indexes", {}).get(name)
            if indexes is None:
                indexes = [(name, 0, "PRIMARY", 1, "id", "A", 0, None, None, "", "BTREE", "", "", "YES", None)] if any((str(c[0]) if isinstance(c, (tuple,list)) else str(c)).lower() == "id" for c in self.existing.get(name,[])) else []
            self._all = list(indexes)
        elif "information_schema.KEY_COLUMN_USAGE" in sql:
            table = self.last_params[0]
            self._all = list(self.foreign_keys.get(table, []))
        elif sql.lstrip().upper().startswith("CREATE TABLE"):
            self.ddl.append(sql)
    def fetchone(self): return self._one
    def fetchall(self): return self._all
    def close(self): pass

class FakeConnection:
    def __init__(self, existing=None):
        self.cur=FakeCursor(existing)
        self.commits=0
        self.rollbacks=0
    def cursor(self): return self.cur
    def commit(self): self.commits+=1
    def rollback(self): self.rollbacks+=1

class SchemaManagerTests(unittest.TestCase):
    def test_splits_create_statements(self):
        sql="SET NAMES utf8mb4;\nCREATE TABLE IF NOT EXISTS alpha (id BIGINT PRIMARY KEY) ENGINE=InnoDB;\nCREATE TABLE IF NOT EXISTS beta (name VARCHAR(20)) ENGINE=InnoDB;"
        parts=split_sql_statements(sql)
        self.assertEqual(len(parts),2)
        self.assertIn("CREATE TABLE",parts[0])
    def test_detects_expected_columns(self):
        table, cols=expected_columns("CREATE TABLE IF NOT EXISTS sample (id BIGINT PRIMARY KEY,\n name VARCHAR(20)) ENGINE=InnoDB")
        self.assertEqual(table,"sample")
        self.assertEqual(cols,{"id","name"})
    def test_rejects_drop(self):
        with self.assertRaises(SchemaPreflightError):
            split_sql_statements("DROP TABLE local_documents;")
    def test_rejects_delete(self):
        with self.assertRaises(SchemaPreflightError):
            split_sql_statements("DELETE FROM local_documents;")

    def test_incompatible_existing_table_is_rejected_before_ddl(self):
        schema="""CREATE TABLE IF NOT EXISTS scan_baskets (
 id BIGINT PRIMARY KEY,
 name VARCHAR(190) NOT NULL,
 cabinet_id BIGINT NULL,
 is_active TINYINT NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;"""
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/"schema.sql"
            path.write_text(schema,encoding="utf-8")
            conn=FakeConnection({"scan_baskets":["id","name"]})
            with self.assertRaises(SchemaPreflightError):
                ensure_schema(conn,path)
            self.assertEqual(conn.cur.ddl,[])
            self.assertEqual(conn.commits,0)

    def test_unexpected_existing_columns_are_rejected_before_ddl(self):
        schema="""CREATE TABLE IF NOT EXISTS scan_baskets (id BIGINT PRIMARY KEY, name VARCHAR(190) NOT NULL) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;"""
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/"schema.sql"; path.write_text(schema,encoding="utf-8")
            conn=FakeConnection({"scan_baskets":[("id","bigint"),("name","varchar(190)"),("legacy_required","int")]})
            with self.assertRaises(SchemaPreflightError): ensure_schema(conn,path)
            self.assertEqual(conn.cur.ddl,[])

    def test_ignores_constraints_as_columns(self):
        table, cols=expected_columns("CREATE TABLE IF NOT EXISTS sample (id BIGINT PRIMARY KEY,\n CONSTRAINT fk FOREIGN KEY(id) REFERENCES x(id)) ENGINE=InnoDB")
        self.assertEqual(cols,{"id"})

    def test_detects_type_mismatch_before_ddl(self):
        schema="""CREATE TABLE IF NOT EXISTS scan_baskets (id BIGINT PRIMARY KEY, name VARCHAR(190) NOT NULL) ENGINE=InnoDB;"""
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/"schema.sql"; path.write_text(schema,encoding="utf-8")
            conn=FakeConnection({"scan_baskets":[("id","varchar(10)"),("name","varchar(190)")]})
            with self.assertRaises(SchemaPreflightError): ensure_schema(conn,path)
            self.assertEqual(conn.cur.ddl,[])

    def test_rejects_shorter_varchar_before_any_ddl(self):
        schema="CREATE TABLE IF NOT EXISTS scan_baskets (id BIGINT PRIMARY KEY, name VARCHAR(190) NOT NULL) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;"
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/"schema.sql"; path.write_text(schema,encoding="utf-8")
            conn=FakeConnection({"scan_baskets":[("id","bigint"),("name","varchar(80)")]})
            with self.assertRaisesRegex(SchemaPreflightError, "incompatible column types"):
                ensure_schema(conn,path)
            self.assertEqual(conn.cur.ddl,[])
            self.assertEqual(conn.commits,0)

    def test_accepts_same_varchar_width_and_integer_display_width(self):
        schema="CREATE TABLE IF NOT EXISTS scan_baskets (id BIGINT PRIMARY KEY, name VARCHAR(190) NOT NULL) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;"
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/"schema.sql"; path.write_text(schema,encoding="utf-8")
            conn=FakeConnection({"scan_baskets":[("id","bigint(20)"),("name","varchar(190)")]})
            ensure_schema(conn,path)
            self.assertEqual(len(conn.cur.ddl),1)
            self.assertEqual(conn.commits,1)

    def test_refuses_non_test_database_before_any_ddl(self):
        class WrongDatabaseCursor(FakeCursor):
            def execute(self, sql, params=None):
                super().execute(sql, params)
                if sql == "SELECT DATABASE()": self._one = ("salah_archive",)
        class WrongDatabaseConnection(FakeConnection):
            def __init__(self):
                super().__init__()
                self.cur = WrongDatabaseCursor()
        schema="CREATE TABLE IF NOT EXISTS sample (id BIGINT PRIMARY KEY) ENGINE=InnoDB;"
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/"schema.sql"; path.write_text(schema,encoding="utf-8")
            conn=WrongDatabaseConnection()
            with self.assertRaises(SchemaPreflightError): ensure_schema(conn,path)
            self.assertEqual(conn.cur.ddl,[])
            self.assertEqual(conn.commits,0)

    def test_missing_required_index_is_rejected_before_ddl(self):
        schema="CREATE TABLE IF NOT EXISTS scan_baskets (id BIGINT PRIMARY KEY, name VARCHAR(190) NOT NULL, INDEX idx_name (name)) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;"
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/"schema.sql"; path.write_text(schema,encoding="utf-8")
            conn=FakeConnection({"scan_baskets":[("id","bigint"),("name","varchar(190)")]})
            with self.assertRaisesRegex(SchemaPreflightError, "missing indexes: idx_name"):
                ensure_schema(conn,path)
            self.assertEqual(conn.cur.ddl,[])
            self.assertEqual(conn.commits,0)

    def test_mismatched_index_columns_are_rejected_before_ddl(self):
        schema="CREATE TABLE IF NOT EXISTS scan_baskets (id BIGINT PRIMARY KEY, name VARCHAR(190) NOT NULL, INDEX idx_name (name)) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;"
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/"schema.sql"; path.write_text(schema,encoding="utf-8")
            conn=FakeConnection({"scan_baskets":[("id","bigint"),("name","varchar(190)")]})
            conn.cur.indexes={"scan_baskets":[
                ("scan_baskets",0,"PRIMARY",1,"id","A",0,None,None,"","BTREE","","","YES",None),
                ("scan_baskets",1,"idx_name",1,"id","A",0,None,None,"","BTREE","","","YES",None),
            ]}
            with self.assertRaisesRegex(SchemaPreflightError, "incompatible indexes: idx_name"):
                ensure_schema(conn,path)
            self.assertEqual(conn.cur.ddl,[])

    def test_unexpected_unique_index_is_rejected_before_ddl(self):
        schema="CREATE TABLE IF NOT EXISTS scan_baskets (id BIGINT PRIMARY KEY, name VARCHAR(190) NOT NULL) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;"
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/"schema.sql"; path.write_text(schema,encoding="utf-8")
            conn=FakeConnection({"scan_baskets":[("id","bigint"),("name","varchar(190)")]})
            conn.cur.indexes={"scan_baskets":[
                ("scan_baskets",0,"PRIMARY",1,"id","A",0,None,None,"","BTREE","","","YES",None),
                ("scan_baskets",0,"unexpected_unique",1,"name","A",0,None,None,"","BTREE","","","YES",None),
            ]}
            with self.assertRaisesRegex(SchemaPreflightError, "unexpected unique indexes"):
                ensure_schema(conn,path)
            self.assertEqual(conn.cur.ddl,[])

    def test_missing_foreign_key_is_rejected_before_ddl(self):
        schema="""CREATE TABLE IF NOT EXISTS parent (id BIGINT PRIMARY KEY) ENGINE=InnoDB;
CREATE TABLE IF NOT EXISTS child (id BIGINT PRIMARY KEY, parent_id BIGINT, CONSTRAINT fk_child_parent FOREIGN KEY(parent_id) REFERENCES parent(id)) ENGINE=InnoDB;"""
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/"schema.sql"; path.write_text(schema,encoding="utf-8")
            conn=FakeConnection({"parent":[("id","bigint")],"child":[("id","bigint"),("parent_id","bigint")]})
            with self.assertRaisesRegex(SchemaPreflightError, "missing foreign keys"):
                ensure_schema(conn,path)
            self.assertEqual(conn.cur.ddl,[])
            self.assertEqual(conn.commits,0)

    def test_accepts_semantically_matching_foreign_key(self):
        schema="""CREATE TABLE IF NOT EXISTS parent (id BIGINT PRIMARY KEY) ENGINE=InnoDB;
CREATE TABLE IF NOT EXISTS child (id BIGINT PRIMARY KEY, parent_id BIGINT, CONSTRAINT fk_child_parent FOREIGN KEY(parent_id) REFERENCES parent(id)) ENGINE=InnoDB;"""
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/"schema.sql"; path.write_text(schema,encoding="utf-8")
            conn=FakeConnection({"parent":[("id","bigint")],"child":[("id","bigint"),("parent_id","bigint")]})
            conn.cur.foreign_keys={"child":[("different_constraint_name","parent_id","parent","id",1)]}
            ensure_schema(conn,path)
            self.assertEqual(len(conn.cur.ddl),2)
            self.assertEqual(conn.commits,1)

    def test_unexpected_foreign_key_is_rejected_before_ddl(self):
        schema="CREATE TABLE IF NOT EXISTS child (id BIGINT PRIMARY KEY) ENGINE=InnoDB;"
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/"schema.sql"; path.write_text(schema,encoding="utf-8")
            conn=FakeConnection({"child":[("id","bigint")]})
            conn.cur.foreign_keys={"child":[("unexpected_fk","id","legacy_parent","id",1)]}
            with self.assertRaisesRegex(SchemaPreflightError, "unexpected foreign keys"):
                ensure_schema(conn,path)
            self.assertEqual(conn.cur.ddl,[])
            self.assertEqual(conn.commits,0)

    def test_parses_composite_foreign_key_columns_in_order(self):
        from mysql_schema_manager import expected_foreign_keys
        statement="CREATE TABLE IF NOT EXISTS child (a BIGINT, b BIGINT, CONSTRAINT fk_pair FOREIGN KEY (a,b) REFERENCES parent (x,y)) ENGINE=InnoDB;"
        table, keys=expected_foreign_keys(statement)
        self.assertEqual(table,"child")
        self.assertEqual(keys,{(("a","b"),"parent",("x","y"))})

if __name__=="__main__": unittest.main(verbosity=2)
