import sqlite3
import os
import uuid
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "lighthouse_attributes.db")


def _get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_lighthouse_db():
    conn = _get_conn()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS lighthouse_attributes (
            vessel TEXT,
            id TEXT,
            name TEXT,
            template_name TEXT,
            type TEXT,
            id_attribute TEXT,
            name_attribute TEXT,
            value TEXT,
            specification TEXT,
            reference TEXT,
            category TEXT,
            is_leaf INTEGER,
            parent_id TEXT,
            parent_attribute_id TEXT DEFAULT ''
        )
    """)

    for col, default in [
        ("parent_attribute_id", "''"),
        ("unit_of_measurement", "''"),
        ("decimal_places", "''"),
        ("description", "''"),
    ]:
        try:
            conn.execute(f"ALTER TABLE lighthouse_attributes ADD COLUMN {col} TEXT DEFAULT {default}")
            conn.commit()
        except Exception:
            pass

    conn.execute("""
        CREATE TABLE IF NOT EXISTS template_attributes (
            environment TEXT,
            client TEXT,
            template_id TEXT,
            template_name TEXT,
            id TEXT,
            name TEXT,
            description TEXT,
            data_source TEXT,
            data_type TEXT,
            unit_of_measurement TEXT,
            default_value TEXT,
            categories TEXT,
            parent_id TEXT
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS sync_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sync_type TEXT NOT NULL,
            environment TEXT NOT NULL,
            client TEXT NOT NULL,
            vessel TEXT,
            last_updated TEXT NOT NULL
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS dd_projects (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            client TEXT NOT NULL,
            environment TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Rascunho',
            ws_parent_id TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)

    try:
        conn.execute("ALTER TABLE dd_projects ADD COLUMN ws_parent_id TEXT")
        conn.commit()
    except Exception:
        pass

    conn.execute("""
        CREATE TABLE IF NOT EXISTS dd_items (
            id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL,
            name TEXT NOT NULL,
            template_id TEXT,
            template_name TEXT,
            parent_item_id TEXT,
            ws_item_id TEXT,
            sort_order INTEGER DEFAULT 0,
            created_at TEXT NOT NULL,
            FOREIGN KEY (project_id) REFERENCES dd_projects(id),
            FOREIGN KEY (parent_item_id) REFERENCES dd_items(id)
        )
    """)

    try:
        conn.execute("ALTER TABLE dd_items ADD COLUMN ws_item_id TEXT")
        conn.commit()
    except Exception:
        pass

    conn.execute("""
        CREATE TABLE IF NOT EXISTS dd_attributes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_id TEXT NOT NULL,
            template_attribute_id TEXT,
            name TEXT NOT NULL,
            data_source TEXT,
            data_type TEXT,
            reference TEXT DEFAULT '',
            value TEXT DEFAULT '',
            unit_of_measurement TEXT DEFAULT '',
            decimal_places INTEGER DEFAULT 2,
            categories TEXT DEFAULT '',
            parent_attribute_id INTEGER,
            sort_order INTEGER DEFAULT 0,
            FOREIGN KEY (item_id) REFERENCES dd_items(id),
            FOREIGN KEY (parent_attribute_id) REFERENCES dd_attributes(id)
        )
    """)

    conn.commit()
    conn.close()


# --------------- sync_history ---------------

def get_sync_history() -> list[dict]:
    conn = _get_conn()
    rows = conn.execute("""
        SELECT sync_type, environment, client, vessel, last_updated
        FROM sync_history
        ORDER BY last_updated DESC
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def _upsert_sync(sync_type: str, environment: str, client: str, vessel: str = None):
    conn = _get_conn()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if vessel:
        existing = conn.execute(
            "SELECT id FROM sync_history WHERE sync_type = ? AND environment = ? AND client = ? AND vessel = ?",
            (sync_type, environment, client, vessel),
        ).fetchone()
    else:
        existing = conn.execute(
            "SELECT id FROM sync_history WHERE sync_type = ? AND environment = ? AND client = ? AND vessel IS NULL",
            (sync_type, environment, client),
        ).fetchone()

    if existing:
        conn.execute("UPDATE sync_history SET last_updated = ? WHERE id = ?", (now, existing["id"]))
    else:
        conn.execute(
            "INSERT INTO sync_history (sync_type, environment, client, vessel, last_updated) VALUES (?, ?, ?, ?, ?)",
            (sync_type, environment, client, vessel, now),
        )
    conn.commit()
    conn.close()


# --------------- lighthouse_attributes (items) ---------------

def get_vessels() -> list[str]:
    conn = _get_conn()
    rows = conn.execute("SELECT DISTINCT vessel FROM lighthouse_attributes ORDER BY vessel").fetchall()
    conn.close()
    return [r["vessel"] for r in rows]


def get_generators(vessel: str = None, search: str = None) -> list[dict]:
    conn = _get_conn()
    query = "SELECT vessel, id, name, id_attribute, name_attribute, value, specification FROM lighthouse_attributes WHERE type = 'generator'"
    params = []

    if vessel:
        query += " AND vessel = ?"
        params.append(vessel)

    if search:
        query += " AND (name LIKE ? OR value LIKE ? OR name_attribute LIKE ?)"
        term = f"%{search}%"
        params.extend([term, term, term])

    query += " ORDER BY vessel, name, value"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_item_tree(vessel: str) -> list[dict]:
    conn = _get_conn()
    rows = conn.execute("""
        SELECT DISTINCT id, name, template_name, parent_id, is_leaf
        FROM lighthouse_attributes
        WHERE vessel = ?
        ORDER BY name
    """, (vessel,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_item_attributes(item_id: str) -> list[dict]:
    conn = _get_conn()
    rows = conn.execute("""
        SELECT id_attribute, name_attribute, value, specification, reference, category,
               COALESCE(unit_of_measurement, '') AS unit_of_measurement,
               COALESCE(decimal_places, '') AS decimal_places,
               COALESCE(description, '') AS description
        FROM lighthouse_attributes
        WHERE id = ? AND type = 'attribute'
        ORDER BY category, name_attribute
    """, (item_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def update_attribute_value_in_db(item_id: str, attribute_id: str, new_value: str):
    conn = _get_conn()
    conn.execute("""
        UPDATE lighthouse_attributes
        SET value = ?
        WHERE id = ? AND id_attribute = ? AND type = 'attribute'
    """, (new_value, item_id, attribute_id))
    conn.commit()
    conn.close()


def update_attribute_fields_in_db(item_id: str, attribute_id: str, attr_type: str, **fields):
    conn = _get_conn()
    allowed = {"value", "reference", "unit_of_measurement", "decimal_places", "description"}
    updates = {k: v for k, v in fields.items() if k in allowed and v is not None}
    if not updates:
        conn.close()
        return
    set_clause = ", ".join(f"{k} = ?" for k in updates)
    values = list(updates.values())
    values.extend([item_id, attribute_id, attr_type])
    conn.execute(f"""
        UPDATE lighthouse_attributes
        SET {set_clause}
        WHERE id = ? AND id_attribute = ? AND type = ?
    """, values)
    conn.commit()
    conn.close()


def insert_item_in_db(vessel: str, item_id: str, name: str, template_name: str,
                       parent_id: str, attributes: list[dict]):
    conn = _get_conn()
    is_leaf = 1
    for attr in attributes:
        category = ""
        cats = attr.get("categories", [])
        if cats and isinstance(cats, list):
            category = cats[0].get("name", "") if isinstance(cats[0], dict) else ""
        attr_id = attr.get("id", "")
        conn.execute("""
            INSERT INTO lighthouse_attributes
                (vessel, id, name, template_name, type, id_attribute, name_attribute,
                 value, specification, reference, category, is_leaf, parent_id,
                 parent_attribute_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (vessel, item_id, name, template_name, "attribute",
              attr_id, attr.get("name", ""),
              attr.get("value", ""),
              f'{attr.get("data_source", "")}_{attr.get("data_type", "")}',
              attr.get("reference", ""), category, is_leaf, parent_id, ""))

        for sub_attr in attr.get("sub_attributes", []):
            sub_category = ""
            sub_cats = sub_attr.get("categories", [])
            if sub_cats and isinstance(sub_cats, list):
                sub_category = sub_cats[0].get("name", "") if isinstance(sub_cats[0], dict) else ""
            conn.execute("""
                INSERT INTO lighthouse_attributes
                    (vessel, id, name, template_name, type, id_attribute, name_attribute,
                     value, specification, reference, category, is_leaf, parent_id,
                     parent_attribute_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (vessel, item_id, name, template_name, "subattribute",
                  sub_attr.get("id", ""), sub_attr.get("name", ""),
                  sub_attr.get("value", ""),
                  f'{sub_attr.get("data_source", "")}_{sub_attr.get("data_type", "")}',
                  sub_attr.get("reference", ""), sub_category, is_leaf, parent_id,
                  attr_id))

    if not attributes:
        conn.execute("""
            INSERT INTO lighthouse_attributes
                (vessel, id, name, template_name, type, id_attribute, name_attribute,
                 value, specification, reference, category, is_leaf, parent_id,
                 parent_attribute_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (vessel, item_id, name, template_name, "attribute",
              "", "", "", "", "", "", is_leaf, parent_id, ""))
    conn.commit()
    conn.close()


def rename_item_in_db(item_id: str, new_name: str):
    conn = _get_conn()
    conn.execute("UPDATE lighthouse_attributes SET name = ? WHERE id = ?", (new_name, item_id))
    conn.commit()
    conn.close()


def delete_item_from_db(item_id: str):
    conn = _get_conn()
    conn.execute("DELETE FROM lighthouse_attributes WHERE id = ?", (item_id,))
    conn.commit()
    conn.close()


def get_item_generators_from_db(item_id: str) -> list[dict]:
    conn = _get_conn()
    rows = conn.execute("""
        SELECT id_attribute, name_attribute, value, specification
        FROM lighthouse_attributes
        WHERE id = ? AND type = 'generator'
        ORDER BY value
    """, (item_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_item_subattributes(item_id: str) -> list[dict]:
    conn = _get_conn()
    rows = conn.execute("""
        SELECT s.id_attribute, s.name_attribute, s.value, s.specification,
               s.parent_attribute_id, s.category,
               p.name_attribute AS parent_name, p.reference AS parent_reference,
               COALESCE(s.unit_of_measurement, '') AS unit_of_measurement,
               COALESCE(s.decimal_places, '') AS decimal_places,
               COALESCE(s.description, '') AS description
        FROM lighthouse_attributes s
        LEFT JOIN lighthouse_attributes p
            ON s.id = p.id AND s.parent_attribute_id = p.id_attribute AND p.type = 'attribute'
        WHERE s.id = ? AND s.type = 'subattribute'
        ORDER BY p.name_attribute, s.name_attribute
    """, (item_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def update_subattribute_value_in_db(item_id: str, attribute_id: str, new_value: str):
    conn = _get_conn()
    conn.execute("""
        UPDATE lighthouse_attributes
        SET value = ?
        WHERE id = ? AND id_attribute = ? AND type = 'subattribute'
    """, (new_value, item_id, attribute_id))
    conn.commit()
    conn.close()


def get_item_meta(item_id: str) -> dict | None:
    conn = _get_conn()
    row = conn.execute("""
        SELECT DISTINCT id, name, template_name, vessel
        FROM lighthouse_attributes
        WHERE id = ?
        LIMIT 1
    """, (item_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def save_items_to_db(rows: list[list], vessel_name: str, environment: str, client: str):
    conn = _get_conn()

    conn.execute("DELETE FROM lighthouse_attributes WHERE vessel = ?", (vessel_name,))

    for row in rows:
        if len(row) == 13:
            (item_id, item_name, template_name, row_type, obj_id, obj_name,
             value, specification, reference, category, is_leaf, parent_id,
             parent_attribute_id) = row
        else:
            (item_id, item_name, template_name, row_type, obj_id, obj_name,
             value, specification, reference, category, is_leaf, parent_id) = row
            parent_attribute_id = ""

        conn.execute("""
            INSERT INTO lighthouse_attributes
                (vessel, id, name, template_name, type, id_attribute, name_attribute,
                 value, specification, reference, category, is_leaf, parent_id,
                 parent_attribute_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (vessel_name, item_id, item_name, template_name, row_type, obj_id,
              obj_name, value, specification, reference, category, int(bool(is_leaf)),
              parent_id, parent_attribute_id))

    conn.commit()
    conn.close()
    _upsert_sync("items", environment, client, vessel_name)


# --------------- template_attributes ---------------

def get_template_attributes_from_db(environment: str = None, client: str = None) -> list[dict]:
    conn = _get_conn()
    query = "SELECT * FROM template_attributes WHERE 1=1"
    params = []
    if environment:
        query += " AND environment = ?"
        params.append(environment)
    if client:
        query += " AND client = ?"
        params.append(client)
    query += " ORDER BY template_name, name"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_template_list(environment: str, client: str) -> list[dict]:
    conn = _get_conn()
    rows = conn.execute("""
        SELECT DISTINCT template_id, template_name
        FROM template_attributes
        WHERE environment = ? AND client = ?
        ORDER BY template_name
    """, (environment, client)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_template_attr_tree(environment: str, client: str, template_id: str) -> list[dict]:
    conn = _get_conn()
    rows = conn.execute("""
        SELECT id, name, description, data_source, data_type,
               unit_of_measurement, default_value, categories, parent_id
        FROM template_attributes
        WHERE environment = ? AND client = ? AND template_id = ?
        ORDER BY name
    """, (environment, client, template_id)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def save_template_attributes_to_db(rows: list[dict], environment: str, client: str):
    conn = _get_conn()

    conn.execute(
        "DELETE FROM template_attributes WHERE environment = ? AND client = ?",
        (environment, client),
    )

    for r in rows:
        conn.execute("""
            INSERT INTO template_attributes
                (environment, client, template_id, template_name, id, name,
                 description, data_source, data_type, unit_of_measurement,
                 default_value, categories, parent_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            environment, client, r.get("template_id", ""), r.get("template_name", ""),
            r.get("id", ""), r.get("name", ""), r.get("description", ""),
            r.get("data_source", ""), r.get("data_type", ""),
            r.get("unit_of_measurement", ""), r.get("default_value", ""),
            r.get("categories", ""), r.get("parent_id", ""),
        ))

    conn.commit()
    conn.close()
    _upsert_sync("templates", environment, client)


# --------------- dd_projects ---------------

def get_dd_projects(status: str = None) -> list[dict]:
    conn = _get_conn()
    query = "SELECT * FROM dd_projects"
    params = []
    if status:
        query += " WHERE status = ?"
        params.append(status)
    query += " ORDER BY updated_at DESC"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_dd_project(project_id: str) -> dict | None:
    conn = _get_conn()
    row = conn.execute("SELECT * FROM dd_projects WHERE id = ?", (project_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def create_dd_project(name: str, client: str, environment: str) -> str:
    conn = _get_conn()
    project_id = str(uuid.uuid4())
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn.execute(
        "INSERT INTO dd_projects (id, name, client, environment, status, created_at, updated_at) VALUES (?,?,?,?,?,?,?)",
        (project_id, name, client, environment, "Rascunho", now, now),
    )
    conn.commit()
    conn.close()
    return project_id


def update_dd_project(project_id: str, **fields):
    conn = _get_conn()
    fields["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    set_clause = ", ".join(f"{k} = ?" for k in fields)
    conn.execute(f"UPDATE dd_projects SET {set_clause} WHERE id = ?", (*fields.values(), project_id))
    conn.commit()
    conn.close()


def delete_dd_project(project_id: str):
    conn = _get_conn()
    item_ids = [r["id"] for r in conn.execute("SELECT id FROM dd_items WHERE project_id = ?", (project_id,)).fetchall()]
    if item_ids:
        placeholders = ",".join("?" * len(item_ids))
        conn.execute(f"DELETE FROM dd_attributes WHERE item_id IN ({placeholders})", item_ids)
    conn.execute("DELETE FROM dd_items WHERE project_id = ?", (project_id,))
    conn.execute("DELETE FROM dd_projects WHERE id = ?", (project_id,))
    conn.commit()
    conn.close()


# --------------- dd_items ---------------

def get_dd_items(project_id: str) -> list[dict]:
    conn = _get_conn()
    rows = conn.execute("""
        SELECT id, project_id, name, template_id, template_name, parent_item_id, ws_item_id, sort_order, created_at
        FROM dd_items
        WHERE project_id = ?
        ORDER BY sort_order, name
    """, (project_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_dd_item(item_id: str) -> dict | None:
    conn = _get_conn()
    row = conn.execute("SELECT * FROM dd_items WHERE id = ?", (item_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def create_dd_item(project_id: str, name: str, template_id: str = None,
                   template_name: str = None, parent_item_id: str = None) -> str:
    conn = _get_conn()
    item_id = str(uuid.uuid4())
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    max_order = conn.execute(
        "SELECT COALESCE(MAX(sort_order), -1) FROM dd_items WHERE project_id = ? AND parent_item_id IS ?",
        (project_id, parent_item_id),
    ).fetchone()[0]
    conn.execute(
        "INSERT INTO dd_items (id, project_id, name, template_id, template_name, parent_item_id, sort_order, created_at) VALUES (?,?,?,?,?,?,?,?)",
        (item_id, project_id, name, template_id, template_name, parent_item_id, max_order + 1, now),
    )
    conn.commit()
    conn.close()
    return item_id


def rename_dd_item(item_id: str, new_name: str):
    conn = _get_conn()
    conn.execute("UPDATE dd_items SET name = ? WHERE id = ?", (new_name, item_id))
    conn.commit()
    conn.close()


def set_dd_item_ws_id(item_id: str, ws_item_id: str):
    conn = _get_conn()
    conn.execute("UPDATE dd_items SET ws_item_id = ? WHERE id = ?", (ws_item_id, item_id))
    conn.commit()
    conn.close()


def delete_dd_item(item_id: str):
    conn = _get_conn()
    child_ids = [r["id"] for r in conn.execute("SELECT id FROM dd_items WHERE parent_item_id = ?", (item_id,)).fetchall()]
    for child_id in child_ids:
        _delete_dd_item_recursive(conn, child_id)
    conn.execute("DELETE FROM dd_attributes WHERE item_id = ?", (item_id,))
    conn.execute("DELETE FROM dd_items WHERE id = ?", (item_id,))
    conn.commit()
    conn.close()


def _delete_dd_item_recursive(conn, item_id: str):
    child_ids = [r["id"] for r in conn.execute("SELECT id FROM dd_items WHERE parent_item_id = ?", (item_id,)).fetchall()]
    for child_id in child_ids:
        _delete_dd_item_recursive(conn, child_id)
    conn.execute("DELETE FROM dd_attributes WHERE item_id = ?", (item_id,))
    conn.execute("DELETE FROM dd_items WHERE id = ?", (item_id,))


# --------------- dd_attributes ---------------

def get_dd_attributes(item_id: str) -> list[dict]:
    conn = _get_conn()
    rows = conn.execute("""
        SELECT id, item_id, template_attribute_id, name, data_source, data_type,
               reference, value, unit_of_measurement, decimal_places, categories,
               parent_attribute_id, sort_order
        FROM dd_attributes
        WHERE item_id = ? AND parent_attribute_id IS NULL
        ORDER BY sort_order, name
    """, (item_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_dd_subattributes(item_id: str) -> list[dict]:
    conn = _get_conn()
    rows = conn.execute("""
        SELECT s.id, s.item_id, s.template_attribute_id, s.name, s.data_source, s.data_type,
               s.reference, s.value, s.unit_of_measurement, s.decimal_places, s.categories,
               s.parent_attribute_id, s.sort_order,
               p.name AS parent_name
        FROM dd_attributes s
        LEFT JOIN dd_attributes p ON s.parent_attribute_id = p.id
        WHERE s.item_id = ? AND s.parent_attribute_id IS NOT NULL
        ORDER BY s.parent_attribute_id, s.sort_order, s.name
    """, (item_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_all_dd_attributes(item_id: str) -> list[dict]:
    conn = _get_conn()
    rows = conn.execute("""
        SELECT id, item_id, template_attribute_id, name, data_source, data_type,
               reference, value, unit_of_measurement, decimal_places, categories,
               parent_attribute_id, sort_order
        FROM dd_attributes
        WHERE item_id = ?
        ORDER BY sort_order, name
    """, (item_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def populate_dd_attributes_from_template(item_id: str, template_id: str,
                                         environment: str, client: str):
    conn = _get_conn()
    conn.execute("DELETE FROM dd_attributes WHERE item_id = ?", (item_id,))

    rows = conn.execute("""
        SELECT id, name, data_source, data_type, unit_of_measurement, default_value, categories, parent_id
        FROM template_attributes
        WHERE environment = ? AND client = ? AND template_id = ?
        ORDER BY name
    """, (environment, client, template_id)).fetchall()

    root_attrs = [dict(r) for r in rows if not r["parent_id"]]
    sub_attrs = [dict(r) for r in rows if r["parent_id"]]

    parent_map = {}
    for i, attr in enumerate(root_attrs):
        cursor = conn.execute("""
            INSERT INTO dd_attributes
                (item_id, template_attribute_id, name, data_source, data_type,
                 unit_of_measurement, decimal_places, categories, parent_attribute_id, sort_order)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, NULL, ?)
        """, (
            item_id, attr["id"], attr["name"], attr["data_source"], attr["data_type"],
            attr["unit_of_measurement"] or "", 2, attr["categories"] or "", i,
        ))
        parent_map[attr["id"]] = cursor.lastrowid

    for j, sub in enumerate(sub_attrs):
        parent_dd_id = parent_map.get(sub["parent_id"])
        if parent_dd_id is None:
            continue
        conn.execute("""
            INSERT INTO dd_attributes
                (item_id, template_attribute_id, name, data_source, data_type,
                 unit_of_measurement, decimal_places, categories, parent_attribute_id, sort_order)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            item_id, sub["id"], sub["name"], sub["data_source"], sub["data_type"],
            sub["unit_of_measurement"] or "", 2, sub["categories"] or "", parent_dd_id, j,
        ))

    conn.commit()
    conn.close()


def update_dd_attribute(attr_id: int, **fields):
    conn = _get_conn()
    set_clause = ", ".join(f"{k} = ?" for k in fields)
    conn.execute(f"UPDATE dd_attributes SET {set_clause} WHERE id = ?", (*fields.values(), attr_id))
    conn.commit()
    conn.close()


def bulk_update_dd_attributes(updates: list[dict]):
    conn = _get_conn()
    for upd in updates:
        attr_id = upd.pop("id")
        if not upd:
            continue
        set_clause = ", ".join(f"{k} = ?" for k in upd)
        conn.execute(f"UPDATE dd_attributes SET {set_clause} WHERE id = ?", (*upd.values(), attr_id))
    conn.commit()
    conn.close()


def get_dd_project_summary(project_id: str) -> dict:
    conn = _get_conn()
    item_count = conn.execute("SELECT COUNT(*) FROM dd_items WHERE project_id = ?", (project_id,)).fetchone()[0]
    item_with_template = conn.execute(
        "SELECT COUNT(*) FROM dd_items WHERE project_id = ? AND template_id IS NOT NULL", (project_id,)
    ).fetchone()[0]

    item_ids = [r["id"] for r in conn.execute("SELECT id FROM dd_items WHERE project_id = ?", (project_id,)).fetchall()]
    attr_count = 0
    attrs_with_ref = 0
    sub_count = 0
    if item_ids:
        placeholders = ",".join("?" * len(item_ids))
        attr_count = conn.execute(
            f"SELECT COUNT(*) FROM dd_attributes WHERE item_id IN ({placeholders}) AND parent_attribute_id IS NULL",
            item_ids,
        ).fetchone()[0]
        attrs_with_ref = conn.execute(
            f"SELECT COUNT(*) FROM dd_attributes WHERE item_id IN ({placeholders}) AND parent_attribute_id IS NULL AND reference != '' AND reference IS NOT NULL",
            item_ids,
        ).fetchone()[0]
        sub_count = conn.execute(
            f"SELECT COUNT(*) FROM dd_attributes WHERE item_id IN ({placeholders}) AND parent_attribute_id IS NOT NULL",
            item_ids,
        ).fetchone()[0]

    conn.close()
    return {
        "items": item_count,
        "items_with_template": item_with_template,
        "attributes": attr_count,
        "attributes_with_reference": attrs_with_ref,
        "subattributes": sub_count,
    }
