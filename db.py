"""
db.py - Database manager for SolTerra Drawing Manager
All data stored locally in SQLite + drawings_storage/ folder.
"""
import os
import shutil
import sqlite3
import zipfile
import json
from datetime import datetime
from pathlib import Path

DB_PATH = "drawings.db"
STORAGE_PATH = "drawings_storage"


class DatabaseManager:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self.storage = Path(STORAGE_PATH)
        self.storage.mkdir(exist_ok=True)
        (self.storage / "attachments").mkdir(exist_ok=True)
        self._init_db()

    # ------------------------------------------------------------------ #
    #  Connection                                                          #
    # ------------------------------------------------------------------ #
    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def _init_db(self):
        schema = Path("schema.sql")
        if schema.exists():
            with open(schema, encoding="utf-8") as f:
                sql = f.read()
            with self._connect() as conn:
                conn.executescript(sql)

    # ------------------------------------------------------------------ #
    #  Projects                                                            #
    # ------------------------------------------------------------------ #
    def get_projects(self):
        with self._connect() as conn:
            return conn.execute(
                "SELECT * FROM projects ORDER BY name"
            ).fetchall()

    def add_project(self, name: str, description: str = "") -> int:
        with self._connect() as conn:
            cur = conn.execute(
                "INSERT INTO projects (name, description) VALUES (?, ?)",
                (name, description),
            )
            return cur.lastrowid

    def update_project(self, project_id: int, name: str, description: str = ""):
        with self._connect() as conn:
            conn.execute(
                "UPDATE projects SET name=?, description=? WHERE id=?",
                (name, description, project_id),
            )

    def delete_project(self, project_id: int):
        with self._connect() as conn:
            conn.execute("DELETE FROM projects WHERE id=?", (project_id,))

    # ------------------------------------------------------------------ #
    #  Categories                                                          #
    # ------------------------------------------------------------------ #
    def get_categories(self):
        with self._connect() as conn:
            return conn.execute(
                "SELECT * FROM categories ORDER BY name"
            ).fetchall()

    def add_category(self, name: str, description: str = "") -> int:
        with self._connect() as conn:
            cur = conn.execute(
                "INSERT INTO categories (name, description) VALUES (?, ?)",
                (name, description),
            )
            return cur.lastrowid

    def update_category(self, cat_id: int, name: str, description: str = ""):
        with self._connect() as conn:
            conn.execute(
                "UPDATE categories SET name=?, description=? WHERE id=?",
                (name, description, cat_id),
            )

    def delete_category(self, cat_id: int):
        with self._connect() as conn:
            conn.execute("DELETE FROM categories WHERE id=?", (cat_id,))

    # ------------------------------------------------------------------ #
    #  Tags                                                                #
    # ------------------------------------------------------------------ #
    def get_all_tags(self) -> list[str]:
        with self._connect() as conn:
            rows = conn.execute("SELECT name FROM tags ORDER BY name").fetchall()
            return [r["name"] for r in rows]

    def get_tags_for_drawing(self, drawing_id: int) -> list[str]:
        with self._connect() as conn:
            rows = conn.execute(
                """SELECT t.name FROM tags t
                   JOIN drawing_tags dt ON t.id=dt.tag_id
                   WHERE dt.drawing_id=?""",
                (drawing_id,),
            ).fetchall()
            return [r["name"] for r in rows]

    def _sync_tags(self, conn: sqlite3.Connection, drawing_id: int, tags: list[str]):
        conn.execute("DELETE FROM drawing_tags WHERE drawing_id=?", (drawing_id,))
        for name in tags:
            name = name.strip()
            if not name:
                continue
            row = conn.execute("SELECT id FROM tags WHERE name=?", (name,)).fetchone()
            if row:
                tag_id = row["id"]
            else:
                cur = conn.execute("INSERT INTO tags (name) VALUES (?)", (name,))
                tag_id = cur.lastrowid
            conn.execute(
                "INSERT OR IGNORE INTO drawing_tags (drawing_id, tag_id) VALUES (?,?)",
                (drawing_id, tag_id),
            )

    # ------------------------------------------------------------------ #
    #  Drawings – CRUD                                                     #
    # ------------------------------------------------------------------ #
    def add_drawing(
        self,
        drawing_number: str,
        title: str,
        file_path: str,
        revision: str = "A",
        project_id: int | None = None,
        category_id: int | None = None,
        part_number: str = "",
        description: str = "",
        status: str = "Draft",
        tags: list[str] | None = None,
        change_note: str = "Initial upload",
    ) -> int:
        src = Path(file_path)
        file_type = src.suffix.lower().lstrip(".")
        file_size = src.stat().st_size

        with self._connect() as conn:
            cur = conn.execute(
                """INSERT INTO drawings
                   (drawing_number, title, description, project_id, category_id,
                    part_number, status, current_revision, file_type)
                   VALUES (?,?,?,?,?,?,?,?,?)""",
                (
                    drawing_number, title, description, project_id, category_id,
                    part_number, status, revision, file_type,
                ),
            )
            drawing_id = cur.lastrowid

            # copy file to storage
            dest_dir = self.storage / str(drawing_id)
            dest_dir.mkdir(exist_ok=True)
            dest = dest_dir / f"v1_{src.name}"
            shutil.copy2(src, dest)

            cur2 = conn.execute(
                """INSERT INTO drawing_versions
                   (drawing_id, revision, file_path, original_filename,
                    file_size, change_note, version_number)
                   VALUES (?,?,?,?,?,?,1)""",
                (drawing_id, revision, str(dest), src.name, file_size, change_note),
            )
            version_id = cur2.lastrowid

            conn.execute(
                "UPDATE drawings SET current_version_id=? WHERE id=?",
                (version_id, drawing_id),
            )

            if tags:
                self._sync_tags(conn, drawing_id, tags)

        return drawing_id

    def update_drawing(
        self,
        drawing_id: int,
        title: str | None = None,
        description: str | None = None,
        project_id: int | None = None,
        category_id: int | None = None,
        part_number: str | None = None,
        status: str | None = None,
        current_revision: str | None = None,
        tags: list[str] | None = None,
    ):
        fields: dict = {}
        if title         is not None: fields["title"]            = title
        if description   is not None: fields["description"]      = description
        if project_id    is not None: fields["project_id"]       = project_id
        if category_id   is not None: fields["category_id"]      = category_id
        if part_number   is not None: fields["part_number"]      = part_number
        if status        is not None: fields["status"]           = status
        if current_revision is not None: fields["current_revision"] = current_revision

        if fields:
            fields["modified_at"] = datetime.now().isoformat()
            set_clause = ", ".join(f"{k}=?" for k in fields)
            values = list(fields.values()) + [drawing_id]
            with self._connect() as conn:
                conn.execute(
                    f"UPDATE drawings SET {set_clause} WHERE id=?", values
                )
                if tags is not None:
                    self._sync_tags(conn, drawing_id, tags)
        elif tags is not None:
            with self._connect() as conn:
                self._sync_tags(conn, drawing_id, tags)

    def delete_drawing(self, drawing_id: int):
        draw_dir = self.storage / str(drawing_id)
        if draw_dir.exists():
            shutil.rmtree(draw_dir)
        att_dir = self.storage / "attachments" / str(drawing_id)
        if att_dir.exists():
            shutil.rmtree(att_dir)
        with self._connect() as conn:
            conn.execute("DELETE FROM drawings WHERE id=?", (drawing_id,))

    def get_drawing(self, drawing_id: int):
        with self._connect() as conn:
            return conn.execute(
                """SELECT d.*, p.name AS project_name, c.name AS category_name,
                          dv.file_path AS current_file_path,
                          dv.original_filename, dv.version_number AS current_version_num
                   FROM drawings d
                   LEFT JOIN projects p        ON d.project_id      = p.id
                   LEFT JOIN categories c      ON d.category_id     = c.id
                   LEFT JOIN drawing_versions dv ON d.current_version_id = dv.id
                   WHERE d.id=?""",
                (drawing_id,),
            ).fetchone()

    def get_all_drawings(self):
        with self._connect() as conn:
            return conn.execute(
                """SELECT d.*, p.name AS project_name, c.name AS category_name,
                          dv.file_path AS current_file_path, dv.original_filename
                   FROM drawings d
                   LEFT JOIN projects p          ON d.project_id        = p.id
                   LEFT JOIN categories c        ON d.category_id       = c.id
                   LEFT JOIN drawing_versions dv ON d.current_version_id = dv.id
                   ORDER BY d.modified_at DESC"""
            ).fetchall()

    # ------------------------------------------------------------------ #
    #  Versions                                                            #
    # ------------------------------------------------------------------ #
    def add_version(
        self,
        drawing_id: int,
        file_path: str,
        revision: str,
        change_note: str = "",
    ):
        src = Path(file_path)
        file_size = src.stat().st_size

        with self._connect() as conn:
            row = conn.execute(
                "SELECT MAX(version_number) AS mx FROM drawing_versions WHERE drawing_id=?",
                (drawing_id,),
            ).fetchone()
            next_v = (row["mx"] or 0) + 1

            dest_dir = self.storage / str(drawing_id)
            dest_dir.mkdir(exist_ok=True)
            dest = dest_dir / f"v{next_v}_{src.name}"
            shutil.copy2(src, dest)

            cur = conn.execute(
                """INSERT INTO drawing_versions
                   (drawing_id, revision, file_path, original_filename,
                    file_size, change_note, version_number)
                   VALUES (?,?,?,?,?,?,?)""",
                (drawing_id, revision, str(dest), src.name, file_size, change_note, next_v),
            )
            version_id = cur.lastrowid

            conn.execute(
                """UPDATE drawings
                   SET current_version_id=?, current_revision=?,
                       modified_at=CURRENT_TIMESTAMP
                   WHERE id=?""",
                (version_id, revision, drawing_id),
            )

    def get_versions(self, drawing_id: int):
        with self._connect() as conn:
            return conn.execute(
                """SELECT * FROM drawing_versions
                   WHERE drawing_id=?
                   ORDER BY version_number DESC""",
                (drawing_id,),
            ).fetchall()

    def restore_version(self, drawing_id: int, version_id: int) -> bool:
        with self._connect() as conn:
            ver = conn.execute(
                "SELECT * FROM drawing_versions WHERE id=?", (version_id,)
            ).fetchone()
            if not ver:
                return False
            conn.execute(
                """UPDATE drawings
                   SET current_version_id=?, current_revision=?,
                       modified_at=CURRENT_TIMESTAMP
                   WHERE id=?""",
                (version_id, ver["revision"], drawing_id),
            )
        return True

    # ------------------------------------------------------------------ #
    #  Attachments                                                         #
    # ------------------------------------------------------------------ #
    def add_attachment(self, drawing_id: int, file_path: str, description: str = ""):
        src = Path(file_path)
        file_size = src.stat().st_size
        att_dir = self.storage / "attachments" / str(drawing_id)
        att_dir.mkdir(parents=True, exist_ok=True)

        dest = att_dir / src.name
        counter = 1
        while dest.exists():
            dest = att_dir / f"{src.stem}_{counter}{src.suffix}"
            counter += 1
        shutil.copy2(src, dest)

        with self._connect() as conn:
            conn.execute(
                """INSERT INTO attachments (drawing_id, filename, file_path, file_size, description)
                   VALUES (?,?,?,?,?)""",
                (drawing_id, src.name, str(dest), file_size, description),
            )

    def get_attachments(self, drawing_id: int):
        with self._connect() as conn:
            return conn.execute(
                "SELECT * FROM attachments WHERE drawing_id=? ORDER BY uploaded_at DESC",
                (drawing_id,),
            ).fetchall()

    def delete_attachment(self, attachment_id: int):
        with self._connect() as conn:
            row = conn.execute(
                "SELECT file_path FROM attachments WHERE id=?", (attachment_id,)
            ).fetchone()
            if row:
                p = Path(row["file_path"])
                if p.exists():
                    p.unlink()
            conn.execute("DELETE FROM attachments WHERE id=?", (attachment_id,))

    # ------------------------------------------------------------------ #
    #  Recent views                                                        #
    # ------------------------------------------------------------------ #
    def record_view(self, drawing_id: int):
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO recent_views (drawing_id) VALUES (?)", (drawing_id,)
            )
            conn.execute(
                """DELETE FROM recent_views WHERE id NOT IN (
                       SELECT id FROM recent_views ORDER BY viewed_at DESC LIMIT 200
                   )"""
            )

    def get_recent_views(self, limit: int = 10):
        with self._connect() as conn:
            return conn.execute(
                """SELECT DISTINCT d.id, d.drawing_number, d.title, d.status,
                          rv.viewed_at, c.name AS category_name
                   FROM recent_views rv
                   JOIN drawings d   ON rv.drawing_id = d.id
                   LEFT JOIN categories c ON d.category_id = c.id
                   ORDER BY rv.viewed_at DESC
                   LIMIT ?""",
                (limit,),
            ).fetchall()

    def get_recent_modified(self, limit: int = 10):
        with self._connect() as conn:
            return conn.execute(
                """SELECT d.*, c.name AS category_name
                   FROM drawings d
                   LEFT JOIN categories c ON d.category_id=c.id
                   ORDER BY d.modified_at DESC
                   LIMIT ?""",
                (limit,),
            ).fetchall()

    # ------------------------------------------------------------------ #
    #  Dashboard stats                                                     #
    # ------------------------------------------------------------------ #
    def get_stats(self) -> dict:
        with self._connect() as conn:
            total = conn.execute(
                "SELECT COUNT(*) AS cnt FROM drawings"
            ).fetchone()["cnt"]

            by_category = conn.execute(
                """SELECT COALESCE(c.name,'Uncategorized') AS name, COUNT(*) AS cnt
                   FROM drawings d
                   LEFT JOIN categories c ON d.category_id=c.id
                   GROUP BY d.category_id
                   ORDER BY cnt DESC"""
            ).fetchall()

            by_status = conn.execute(
                "SELECT status, COUNT(*) AS cnt FROM drawings GROUP BY status"
            ).fetchall()

            by_type = conn.execute(
                """SELECT UPPER(file_type) AS file_type, COUNT(*) AS cnt
                   FROM drawings GROUP BY file_type ORDER BY cnt DESC"""
            ).fetchall()

        return {
            "total": total,
            "by_category": [(r["name"], r["cnt"]) for r in by_category],
            "by_status":   {r["status"]: r["cnt"] for r in by_status},
            "by_type":     [(r["file_type"], r["cnt"]) for r in by_type],
        }

    # ------------------------------------------------------------------ #
    #  Search                                                              #
    # ------------------------------------------------------------------ #
    def search(
        self,
        query: str = "",
        project_id: int | None = None,
        category_id: int | None = None,
        status: str | None = None,
        file_type: str | None = None,
        tags: list[str] | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
    ):
        sql = """
            SELECT DISTINCT d.*, p.name AS project_name, c.name AS category_name,
                   dv.file_path AS current_file_path, dv.original_filename
            FROM drawings d
            LEFT JOIN projects p          ON d.project_id        = p.id
            LEFT JOIN categories c        ON d.category_id       = c.id
            LEFT JOIN drawing_versions dv ON d.current_version_id = dv.id
            LEFT JOIN drawing_tags dt     ON d.id                 = dt.drawing_id
            LEFT JOIN tags t              ON dt.tag_id            = t.id
            WHERE 1=1
        """
        params: list = []

        if query:
            like = f"%{query}%"
            sql += """ AND (d.drawing_number LIKE ? OR d.title LIKE ?
                            OR d.description LIKE ? OR d.part_number LIKE ?
                            OR t.name LIKE ?)"""
            params.extend([like, like, like, like, like])

        if project_id:
            sql += " AND d.project_id=?"
            params.append(project_id)

        if category_id:
            sql += " AND d.category_id=?"
            params.append(category_id)

        if status:
            sql += " AND d.status=?"
            params.append(status)

        if file_type:
            sql += " AND d.file_type=?"
            params.append(file_type.lower())

        if tags:
            placeholders = ",".join("?" * len(tags))
            sql += f" AND t.name IN ({placeholders})"
            params.extend(tags)

        if date_from:
            sql += " AND d.created_at >= ?"
            params.append(date_from)

        if date_to:
            sql += " AND d.created_at <= ?"
            params.append(date_to)

        sql += " ORDER BY d.modified_at DESC"

        with self._connect() as conn:
            return conn.execute(sql, params).fetchall()

    # ------------------------------------------------------------------ #
    #  Export / Backup                                                     #
    # ------------------------------------------------------------------ #
    def export_to_zip(self, drawing_ids: list[int], dest_path: str) -> str:
        """Export selected drawings + metadata to a ZIP file."""
        metadata = []
        with zipfile.ZipFile(dest_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for did in drawing_ids:
                d = self.get_drawing(did)
                if not d:
                    continue
                row = dict(d)
                row["tags"] = self.get_tags_for_drawing(did)
                src = Path(row.get("current_file_path", "") or "")
                if src.exists():
                    zf.write(src, f"drawings/{row['original_filename']}")
                metadata.append(row)

            zf.writestr(
                "metadata.json",
                json.dumps(metadata, indent=2, default=str),
            )
        return dest_path

    def backup_database(self, dest_folder: str) -> str:
        """Full backup: database + all stored files → timestamped ZIP."""
        dest = Path(dest_folder)
        dest.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        zip_path = dest / f"solterra_backup_{ts}.zip"

        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            db = Path(self.db_path)
            if db.exists():
                zf.write(db, db.name)
            if self.storage.exists():
                for f in self.storage.rglob("*"):
                    if f.is_file():
                        zf.write(f, str(f.relative_to(self.storage.parent)))

        return str(zip_path)
