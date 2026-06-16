# Serenity

A warm, modern mental health support platform built with React and TanStack Start.

## What is Serenity?

Serenity is a safe, calming digital space that combines AI-powered emotional support with a premium user experience designed around growth, nature, and warmth. The platform features:

- **AI-Powered Chat** — Emotionally aware, calming conversations to help you process feelings.
- **Beautiful Landing Page** — Floral design language with warm colors, animated elements, and a sense of hope.
- **Authentication Pages** — Split-screen login and registration with motivational quotes and nature illustrations.
- **Crisis Support** — Built-in detection and guidance for when someone needs immediate help.
- **Responsive Design** — Works beautifully on desktop and mobile.

## Tech Stack

- **Framework:** TanStack Start (React 19, file-based routing, SSR/SSG)
- **Build Tool:** Vite 7
- **Styling:** Tailwind CSS v4
- **UI Components:** shadcn/ui
- **Animations:** Framer Motion
- **Icons:** Lucide React
- **Runtime:** Bun

## Prerequisites

- [Node.js 18+](https://nodejs.org/)
- [Bun](https://bun.sh/) — Install with: `curl -fsSL https://bun.sh/install | bash`

## Getting Started

### 1. Clone the Repository

```bash
git clone <your-repo-url>
cd <repo-folder>
```

### 2. Install Dependencies

```bash
bun install
```

This reads the `bun.lock` file and installs exactly the versions the project was built with.

### 3. Start the Development Server

```bash
bun dev
```

The app will open at **http://localhost:3000**.

### 4. Build for Production

```bash
bun run build
```

The production bundle is generated in `dist/`.

## Syncing Modules After Pulling Updates

Whenever you pull new changes from GitHub, run:

```bash
bun install
```

This keeps `node_modules` perfectly in sync with the lockfile.

## Project Structure

```
src/
  components/
    landing/          # Landing page sections (Hero, Benefits, FAQ, etc.)
    ui/               # shadcn/ui components
  routes/
    index.tsx         # Landing page (home)
    login.tsx         # Login page
    register.tsx      # Registration page
    chat.tsx          # AI chat interface
    __root.tsx        # Root layout (head, fonts, global shell)
  assets/             # Images and illustrations
  styles.css          # Global design tokens and keyframes
```

---

## Running with Docker

You can run Serenity AI using the pre-built Docker image from Docker Hub.

### 1. Pull the Docker Image

```
docker pull alihashish09/serenity-frontend:latest
```


### 2. Run the Container

```
docker run -d --name serenity-frontend -p 3000:3000 alihashish09/serenity-frontend:latest
```

The application will be available at:

```
http://localhost:3000
```


### 3. Stop the Container

```
docker stop serenity-ai
```

Remove the container:

```
docker rm serenity-ai
```


### 4. View Logs

```
docker logs -f serenity-ai
```

---

## Notes

- The authentication and chat pages are currently **UI-only** — no backend or database is connected yet.
- Voice features are not yet implemented.
- The project is designed to be deployed on edge platforms (e.g., Cloudflare Workers) via TanStack Start.