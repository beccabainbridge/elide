import sqlite3
from contextlib import closing

def connect_db(db_file):
    return sqlite3.connect(db_file)

def init_db(db_file, schema):
    with closing(connect_db(db_file)) as db:
        with open(schema, mode='r') as f:
            db.cursor().executescript(f.read())
            db.commit()

def select(database, query, items=None):
    with closing(connect_db(database)) as db:
        if items:
            q = db.execute(query, items)
        else:
            q = db.execute(query)
        return q.fetchall()

def insert(database, query, items):
    with closing(connect_db(database)) as db:
        db.execute(query, items)
        db.commit()

def update(database, query, items):
    insert(database, query, items)

def delete(database, query, items):
    with closing(connect_db(database)) as db:
        db.execute(query, items)
        db.commit()

def select_from_db(database, items, table, where=None, get_first=True):
    query = "SELECT {items} FROM {table}".format(items=", ".join(items), table=table)
    if where:
        query += " WHERE " + "and ".join(["{item_name}=?".format(item_name=key) for key in where])
        print query
        entries = select(database, query, tuple(where.values()))
    else:
        entries = select(database, query)
    if get_first:
        return entries[0][0] if entries else None
    else:
        return entries
