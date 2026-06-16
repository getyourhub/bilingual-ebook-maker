import os
import json
import uuid
import asyncio
from pathlib import Path
from datetime import datetime

from fastapi import FastAPI, UploadFile, File, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from translator import translate_chapter, load_ielts_words, get_all_providers, get_provider
from epub_handler import parse_epub, parse_pdf, build_bilingual_epub, get_book_info
from progress_manager import ProgressManager

app = FastAPI(title="Bilingual Ebook Maker")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

progress_mgr = ProgressManager()
ielts_words = load_ielts_words()

UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "./uploads"))
OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", "./outputs"))
UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/api/providers")
async def list_providers():
    return get_all_providers()


@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    if not file.filename.lower().endswith((".epub", ".pdf")):
        return JSONResponse({"error": "Only .epub and .pdf files are supported"}, status_code=400)

    task_id = str(uuid.uuid4())[:8]
    task_dir = UPLOAD_DIR / task_id
    task_dir.mkdir(parents=True, exist_ok=True)

    file_path = task_dir / file.filename
    with open(file_path, "wb") as f:
        content = await file.read()
        f.write(content)

    info = get_book_info(file_path)
    return {"task_id": task_id, "filename": file.filename, "filepath": str(file_path), "book_info": info}


@app.post("/api/translate")
async def start_translation(request: Request):
    data = await request.json()
    task_id = data["task_id"]
    filepath = data["filepath"]
    filename = data["filename"]
    provider = data.get("provider", "google")
    api_key = data.get("api_key", "")
    model = data.get("model", "")
    custom_url = data.get("custom_url", "")
    custom_model = data.get("custom_model", "")
    fallback_provider = data.get("fallback_provider", "")
    fallback_api_key = data.get("fallback_api_key", "")
    fallback_model = data.get("fallback_model", "")

    progress_mgr.init_task(task_id)
    asyncio.create_task(
        run_translation(
            task_id, filepath, filename, provider, api_key, model,
            custom_url, custom_model, fallback_provider, fallback_api_key, fallback_model
        )
    )
    return {"task_id": task_id, "status": "started"}


async def run_translation(
    task_id: str, filepath: str, filename: str,
    provider: str = "google", api_key: str = "", model: str = "",
    custom_url: str = "", custom_model: str = "",
    fallback_provider: str = "", fallback_api_key: str = "", fallback_model: str = ""
):
    try:
        progress_mgr.update(task_id, "parsing", 0, "Parsing ebook structure...")

        if filepath.lower().endswith(".epub"):
            chapters, metadata = parse_epub(filepath)
        else:
            chapters, metadata = parse_pdf(filepath)

        progress_mgr.update(task_id, "parsing", 100, "Parsing complete")

        prov = get_provider(provider)
        provider_name = prov.display_name if prov else provider
        progress_mgr.update(task_id, "translating", 0, f"Using {provider_name}...")

        total = len(chapters)
        translated_chapters = []
        ielts_stats = {"total": 0, "words": []}
        used_fallback = False

        for i, ch in enumerate(chapters):
            pct = int((i / total) * 100)
            progress_mgr.update(
                task_id, "translating", pct,
                f"[{provider_name}] Chapter {i+1}/{total}: {ch['title'][:35]}..."
            )

            try:
                translated_text, found_ielts = await translate_chapter(
                    ch["text"], ielts_words,
                    provider_name=provider, api_key=api_key, model=model,
                    custom_url=custom_url, custom_model=custom_model
                )
            except Exception as e:
                if fallback_provider and not used_fallback:
                    fallback_prov = get_provider(fallback_provider)
                    fallback_name = fallback_prov.display_name if fallback_prov else fallback_provider
                    progress_mgr.update(
                        task_id, "translating", pct,
                        f"⚠️ {provider_name} failed, switching to {fallback_name}..."
                    )
                    used_fallback = True
                    translated_text, found_ielts = await translate_chapter(
                        ch["text"], ielts_words,
                        provider_name=fallback_provider, api_key=fallback_api_key, model=fallback_model
                    )
                else:
                    raise

            ielts_stats["total"] += len(found_ielts)
            ielts_stats["words"].extend(found_ielts)
            translated_chapters.append({
                "title": ch["title"], "original": ch["text"],
                "translated": translated_text, "ielts_words": found_ielts
            })
            await asyncio.sleep(0.05)

        progress_mgr.update(task_id, "building", 50, "Building bilingual EPUB...")

        output_path = str(OUTPUT_DIR / (filename.rsplit(".", 1)[0] + "_bilingual.epub"))
        build_bilingual_epub(chapters, translated_chapters, metadata, output_path, ielts_stats)

        progress_mgr.update(task_id, "done", 100, "Complete!")

        final_provider = f"{provider_name} → {fallback_name}" if used_fallback else provider_name
        stats = {
            "total_chapters": total,
            "total_ielts_words": ielts_stats["total"],
            "unique_ielts_words": len(set(w["word"] for w in ielts_stats["words"])),
            "output_path": output_path,
            "output_filename": os.path.basename(output_path),
            "original_filename": filename,
            "provider": final_provider,
            "used_fallback": used_fallback,
            "timestamp": datetime.now().isoformat(),
            "ielts_words_sample": ielts_stats["words"][:30]
        }
        progress_mgr.set_result(task_id, stats)

    except Exception as e:
        progress_mgr.update(task_id, "error", 0, str(e))
        import traceback
        traceback.print_exc()


@app.get("/api/progress/{task_id}")
async def get_progress(task_id: str):
    return progress_mgr.get(task_id)


@app.get("/api/download/{task_id}")
async def download(task_id: str):
    result = progress_mgr.get_result(task_id)
    if not result:
        return JSONResponse({"error": "Not ready"}, status_code=404)
    path = result["output_path"]
    if not os.path.exists(path):
        return JSONResponse({"error": "File not found"}, status_code=404)
    return FileResponse(path, filename=result["output_filename"], media_type="application/epub+zip")


@app.websocket("/ws/progress/{task_id}")
async def ws_progress(websocket: WebSocket, task_id: str):
    await websocket.accept()
    try:
        while True:
            data = progress_mgr.get(task_id)
            await websocket.send_json(data)
            if data.get("status") in ("done", "error"):
                break
            await asyncio.sleep(0.3)
    except WebSocketDisconnect:
        pass


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
