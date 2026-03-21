@app.get("/", response_class=HTMLResponse)
async def serve_gui():
    # Looks in your new folder
    if not os.path.exists("question_GUI/index.html"):
        return "<h1>Error: question_GUI/index.html not found!</h1>"
    return FileResponse("question_GUI/index.html")