# PolEdu

A personalized math tutoring platform that generates adaptive lessons based on each learner's profile. Built for LotusHacks 2026.

## What it does

- **Learner profiling** — onboards users with a quick profile (name, learning style, hobbies) to personalize every lesson
- **AI-generated math lessons** — typed chat message → fully structured lesson with explanations, interactive graphs, and a 10-question mini-test, generated inline in chat
- **Adaptive learning styles** — hands-on learners get slider graphs and guided step-by-step reveals; listening learners get analogy blocks and per-section narration (Web Speech API)
- **IELTS mock test generation** — full mock tests with listening, reading, writing, and speaking sections
- **Demo personas** — two pre-built learner profiles (Alex and Jamie) to showcase the experience difference

## Architecture

```
frontend/          Vue 3 + TypeScript (Vite)
backend/           FastAPI (Python)
docs/              Source PDFs (e.g. IELTS material)
```

**AI services used:**
| Service | Role |
|---------|------|
| Gemma 3 12B (Google Gemini API) | Chat intent routing |
| GPT-5.2 (OpenAI API) | Math lesson & IELTS test generation |
| Exa API | Math topic research (web search) |
| ChromaDB | Local vector DB for IELTS document retrieval |

## Getting started

### Prerequisites

- Node.js >= 20
- Python >= 3.11
- API keys for OpenAI, Google Gemini, and Exa

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Create a `.env` file in `backend/`:

```env
OPENAI_API_KEY=sk-proj-...
GEMINI_API_KEY=...
EXA_API_KEY=...
```

Start the server:

```bash
uvicorn API:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

The app runs at `http://localhost:5173` and expects the backend at `http://localhost:8000`.

### Ingest IELTS documents (optional)

Place PDFs in the `docs/` folder, then run:

```bash
cd backend
python vectorDB_collect.py
```

## Project structure

```
backend/
  API.py              Main FastAPI app — all endpoints
  math_lessons.py     Lesson generation logic (prompt, validation, GPT call)
  ielts.py            IELTS test generation
  chromadb_store.py   Vector DB storage helpers
  retrieve.py         Vector DB retrieval helpers
  parsing.py          PDF parsing
  listening_gen.py    Audio generation for IELTS listening sections
  exa_scrape.py       Exa web search integration

frontend/src/
  pages/
    ChatPage.vue       Main chat interface with inline lesson cards
    LessonPage.vue     Full-page lesson viewer
  components/
    InlineLessonCard.vue     Lesson card rendered in chat
    LessonBlockRenderer.vue  Renders all lesson block types
    SliderGraph.vue          Interactive parametric graph with sliders
    GuidedSteps.vue          Step-by-step reveal component
    AnalogyBlock.vue         Analogy card for listening learners
    GraphBlock.vue           Static canvas graph
    GraphPlayground.vue      Full-screen graph explorer
    MultipleChoice.vue       Quiz question component
    NumberAnswer.vue         Numeric answer question component
    TrueFalseQuestion.vue    True/false question component
    LatexFormula.vue         KaTeX formula renderer
```

## Lesson block types

Lessons are structured JSON with typed content blocks. The block type generated depends on the learner's style:

| Block type | Learning style | Description |
|------------|---------------|-------------|
| `text` | All | Explanation paragraphs |
| `graph` | All | Static rendered graph |
| `graph-playground` | Doing | Interactive graph explorer |
| `slider-graph` | Doing | Parametric graph with A/B sliders |
| `guided-steps` | Doing | Step-by-step problem with reveal |
| `analogy` | Listening | Real-world analogy card |

## API endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Health check |
| `POST` | `/onboard` | Create learner profile |
| `POST` | `/assistant/chat` | Chat message → intent routing + lesson creation |
| `GET` | `/lessons/{code}/status` | Poll lesson generation status |
| `GET` | `/lessons/{code}/payload` | Fetch completed lesson JSON |
| `POST` | `/minibot` | IELTS-only chat bot |
| `POST` | `/create-test` | Directly enqueue IELTS test generation |
| `GET` | `/tests/{code}/status` | Poll test generation status |
