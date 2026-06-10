# UI Prototypes

Design mockups — **not part of the running app**. The real frontend lives in
`frontend/src/` (React + TypeScript + Vite, wired to the FastAPI backend).

| Prototype | What it is |
|-----------|-----------|
| `jobhunter_dashboard.html` | Early static HTML/CSS dashboard mock |
| `claude-design/` | Claude Design standalone prototype — open `JobHunter Dashboard.html` in a browser; it loads the `jh-*.jsx` files via in-browser Babel with hardcoded demo data |

Features born here that were ported into the real app:
- Radar-sweep logo (`frontend/src/components/Sidebar.tsx`)
- Log panel minimize/expand + drag-to-resize (`frontend/src/components/LogPanel.tsx`)
