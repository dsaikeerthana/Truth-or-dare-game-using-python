from fastapi import FastAPI, Request, Form, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import json
import os
import random
from datetime import datetime
from typing import List

app = FastAPI()
templates = Jinja2Templates(directory="templates")

# Mount static directory
app.mount("/static", StaticFiles(directory="static"), name="static")

# Paths to data files
QUESTIONS_FILE = 'data/questions.json'
SCORES_FILE = 'data/scores.json'
LOG_FILE = 'data/activity_log.json'

# Ensure data directory and files exist
def ensure_data_files():
    os.makedirs('data', exist_ok=True)
    if not os.path.exists(QUESTIONS_FILE):
        with open(QUESTIONS_FILE, 'w') as f:
            json.dump({"truth": [], "dare": []}, f)
    if not os.path.exists(SCORES_FILE):
        with open(SCORES_FILE, 'w') as f:
            json.dump({}, f)
    if not os.path.exists(LOG_FILE):
        with open(LOG_FILE, 'w') as f:
            json.dump([], f)

# Load and save helpers
def load_json(file_path):
    with open(file_path) as f:
        return json.load(f)

def save_json(file_path, data):
    with open(file_path, 'w') as f:
        json.dump(data, f, indent=4)

# Load data
load_questions = lambda: load_json(QUESTIONS_FILE)
load_scores = lambda: load_json(SCORES_FILE)
load_logs = lambda: load_json(LOG_FILE)

# Save data
save_questions = lambda data: save_json(QUESTIONS_FILE, data)
save_scores = lambda data: save_json(SCORES_FILE, data)
save_logs = lambda data: save_json(LOG_FILE, data)

# Log activity
def log_activity(player: str, action: str, detail: str):
    logs = load_logs()
    logs.append({
        "timestamp": datetime.now().isoformat(),
        "player": player,
        "action": action,
        "detail": detail
    })
    save_logs(logs)

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/play", response_class=HTMLResponse)
async def play(request: Request, player: str = Form(...), choice: str = Form(...)):
    questions = load_questions()
    question_list = questions.get(choice, [])
    if not question_list:
        return HTMLResponse(f"No {choice} questions found. Please add some first.")
    question = random.choice(question_list)
    log_activity(player, "play", f"Selected {choice}: {question}")
    return templates.TemplateResponse("play.html", {"request": request, "player": player, "question": question, "choice": choice})

@app.post("/submit")
async def submit(player: str = Form(...), choice: str = Form(...), result: str = Form(...)):
    scores = load_scores()
    scores.setdefault(player, {"completed": 0, "skipped": 0})
    scores[player][result] += 1
    save_scores(scores)
    log_activity(player, "submit", f"{result} a {choice} question")
    return RedirectResponse(url="/leaderboard", status_code=status.HTTP_302_FOUND)

@app.get("/add_question", response_class=HTMLResponse)
async def add_question_form(request: Request):
    return templates.TemplateResponse("add_question.html", {"request": request})

@app.post("/add_question")
async def add_question(choice: str = Form(...), question: str = Form(...)):
    data = load_questions()
    data[choice].append(question)
    save_questions(data)
    log_activity("admin", "add_question", f"Added to {choice}: {question}")
    return RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)

@app.get("/leaderboard", response_class=HTMLResponse)
async def leaderboard(request: Request):
    scores = load_scores()
    sorted_scores = sorted(scores.items(), key=lambda x: x[1]['completed'], reverse=True)
    return templates.TemplateResponse("leaderboard.html", {"request": request, "scores": sorted_scores})

@app.get("/logs", response_class=HTMLResponse)
async def show_logs(request: Request):
    logs = load_logs()
    return templates.TemplateResponse("logs.html", {"request": request, "logs": logs[::-1]})

if __name__ == "__main__":
    ensure_data_files()
    import uvicorn
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)
