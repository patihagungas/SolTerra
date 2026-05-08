# SolTerra Drawing Manager

Local drawing management system — no cloud, all data stored on your PC.

## Quick Start

```bash
cd SolTerraDrawing
pip install -r requirements.txt
python main.py
```

## Features

| Feature | Details |
|---|---|
| File types | PDF, DWG, DXF, PNG, JPG, BMP, TIFF |
| Metadata | Drawing #, Title, Part #, Revision, Project, Category, Status, Tags |
| Versions | Upload new versions, view full history, restore any previous version |
| Viewer | PDF + image preview with zoom (Ctrl+scroll) and pan (drag) |
| Search | Live search by number, title, part#, description, tags; filter by project/category/status/type |
| Dashboard | Total counts by status, bar charts by category and file type, recent modified/viewed lists |
| Attachments | Attach any file to a drawing |
| Export | Export selected drawing(s) + metadata to ZIP |
| Backup | Full database + file storage backup to timestamped ZIP |

## File Layout

```
SolTerraDrawing/
├── main.py           # entry point
├── db.py             # database manager
├── ui.py             # all UI panels and dialogs
├── viewer.py         # PDF / image viewer widget
├── search.py         # search helper
├── schema.sql        # SQLite schema (auto-applied on first run)
├── requirements.txt
├── drawings.db       # SQLite database (created on first run)
└── drawings_storage/ # all uploaded files (created on first run)
    ├── 1/            # files for drawing id=1
    │   ├── v1_myfile.pdf
    │   └── v2_myfile_revised.pdf
    └── attachments/
        └── 1/
```

## Dependencies

- **PyQt6** — UI framework
- **PyMuPDF** (`fitz`) — PDF rendering in the viewer

## Usage Notes

- Double-click a drawing row to open it in your system's default viewer.
- Right-click a row for a context menu (Edit, New Version, History, Export, Delete).
- Ctrl+Scroll in the viewer to zoom; drag to pan.
- Projects and Categories are managed from the Settings panel.
