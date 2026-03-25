# SafeZone AI — Multi-Modal Smart Surveillance System

A modern, production-quality frontend for an AI-powered surveillance SaaS platform.

## Tech Stack

- **React 18** + **Vite**
- **Tailwind CSS** (with custom theme)
- **React Router v6**
- **Lucide React** (icons)
- **Custom fonts**: Orbitron (display), Syne (body), JetBrains Mono (mono)

## Project Structure

```
src/
├── assets/
│   └── mockData.js          # Mock alerts, cameras, logs, map zones
├── components/
│   ├── Navbar.jsx            # Landing page navbar
│   ├── Sidebar.jsx           # Dashboard sidebar with collapse
│   ├── DashboardLayout.jsx   # Dashboard wrapper layout
│   ├── Hero.jsx              # Hero section with mock camera card
│   ├── FeatureCard.jsx       # Reusable feature card
│   ├── StatCard.jsx          # Dashboard stat cards
│   ├── AlertCard.jsx         # Alert item with severity styles
│   └── CameraFeed.jsx        # Mock camera feed tile
├── pages/
│   ├── Landing.jsx           # Public landing page
│   ├── Login.jsx             # Auth page (fake login)
│   ├── Dashboard.jsx         # Main control center
│   ├── Alerts.jsx            # Alert center with filtering
│   ├── Logs.jsx              # Event log table
│   └── MapView.jsx           # Facility SVG map
├── routes/
│   └── AppRoutes.jsx         # React Router setup + protected routes
├── App.jsx                   # Auth context provider
├── main.jsx
└── index.css                 # Global styles + Tailwind directives
```

## Getting Started

```bash
npm install
npm run dev
```

Open [http://localhost:5173](http://localhost:5173)

## Login

Use any email + a password of 4+ characters.

**Demo credentials:**

- Email: `demo@safezone.ai`
- Password: `admin1234`

## Features

- **Landing Page** — Hero, Demo, Features, CTA, Footer
- **Login** — Form with validation + fake auth
- **Dashboard** — Stats, live camera grid, alerts panel, event log table
- **Alerts** — Filterable alert list by severity
- **Event Logs** — Filterable, searchable audit log table
- **Map View** — SVG facility floor plan with zone status + camera markers

## Design System

- **Dark theme** — `#030712` base
- **Cyan accents** — `#22d3ee` / `#06b6d4`
- **Glassmorphism cards** — `backdrop-blur` + semi-transparent borders
- **Display font** — Orbitron (tactical/futuristic)
- **Body font** — Syne (clean, modern)
- **Mono font** — JetBrains Mono (terminal aesthetic)

---

Built for College Project
