# Northern New Mexico College Student Hub UI

This React 18 / Vite application is dedicated to Northern New Mexico College.
It includes NNMC program and career exploration, official College Scorecard
details, education-plan building, saved plans, and scheduling.

## Prerequisites

- Node.js 24.x
- npm with the committed `package-lock.json`

## Development

```bash
npm install
npm run dev
```

Configure the backend endpoint in `.env`:

```env
VITE_API_BASE_URL=http://localhost:8000/api
```

## Checks

```bash
npm run lint
npm run build
```

The NNMC identity is centralized in `src/config/institution.js`. Institutional
metrics come from the College Scorecard API, while program and course data are
limited to the Northern New Mexico College catalog by both frontend and backend
filters.
