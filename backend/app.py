from __future__ import annotations

import re
import threading
import time
from functools import lru_cache
from pathlib import Path
from subprocess import CalledProcessError
from typing import Dict, Iterable, List, Literal, Optional, cast
from uuid import uuid4

import requests
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from starlette.responses import JSONResponse
from starlette.status import HTTP_404_NOT_FOUND

from allthatstax.card_store import CardFaceRecord, CardRecord, load_card_store
from allthatstax.config import load_config
from allthatstax.latex_text import generate_latex_text
from allthatstax.legalities import extract_legalities
from allthatstax.workflow import (
    DEFAULT_COMMAND,
    MoxfieldError,
    get_cards_information,
    run_latex,
    save_deck_to_file,
)

BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = BASE_DIR / "config.json"
CARD_TYPE_ORDER = ["生物", "神器", "结界", "其他"]
_mana_pattern = re.compile(r"\{([^}]+)\}")
_cache_lock = threading.Lock()
_cached_payload: Optional[Dict[str, object]] = None
_cached_mtime: Optional[float] = None
CONFIG = load_config(CONFIG_PATH)


class CardFace(BaseModel):
    englishName: str
    chineseName: str
    image: str
    manaCost: List[str]
    cardType: str
    description: str


class StaxType(BaseModel):
    key: str
    label: str


class Card(BaseModel):
    id: str
    kind: Literal["single", "multiface"]
    faces: List[CardFace]
    staxType: Optional[StaxType]
    isRestricted: bool
    legalities: Dict[str, str]
    manaValue: int
    sortCardType: str


class Metadata(BaseModel):
    staxTypes: List[StaxType]
    cardTypeOrder: List[str]


class LatexSettings(BaseModel):
    dataFileName: str
    latexTextName: str
    latexFileName: str
    latexCommand: List[str]


class LatexGenerationRequest(BaseModel):
    dataFileName: str
    latexTextName: str
    latexFileName: str
    latexCommand: Optional[List[str]] = None
    fetchCards: bool = False
    fetchFromScratch: bool = False
    downloadImages: bool = True
    skipCompile: bool = False


class CardFetchSettings(BaseModel):
    cardListName: str
    dataFileName: str
    imageFolderName: str
    downloadImages: bool
    moxfieldDeckUrl: Optional[str] = None


class CardFetchRequest(BaseModel):
    cardListName: str
    dataFileName: str
    imageFolderName: str
    fromScratch: bool = False
    downloadImages: bool = True


class CardFetchResponse(BaseModel):
    cardsProcessed: int
    cardsUpdated: int
    imagesDownloaded: int
    errors: List[str]
    dataFile: str
    duration: float


class FetchLogEntry(BaseModel):
    id: int
    timestamp: float
    level: Literal["info", "warning", "error"]
    message: str
    processed: int
    total: int
    updated: int
    imagesDownloaded: int
    cardName: Optional[str] = None
    setCode: Optional[str] = None


class CardFetchJobStatus(BaseModel):
    jobId: Optional[str]
    status: Literal["idle", "running", "success", "error"]
    logs: List[FetchLogEntry]
    processed: int
    total: int
    updated: int
    imagesDownloaded: int
    result: Optional[CardFetchResponse] = None
    error: Optional[str] = None


class MoxfieldFetchRequest(BaseModel):
    deckUrl: str
    cardListName: Optional[str] = None


class MoxfieldFetchResponse(BaseModel):
    cardsWritten: int
    cardListPath: str


class LatexGenerationResponse(BaseModel):
    latexTextPath: str
    pdfPath: Optional[str]
    command: List[str]
    stdout: Optional[str]
    stderr: Optional[str]


app = FastAPI(title="AllThatStax API", version="1.0.0")


class CardFetchJob:
    def __init__(self, payload: CardFetchRequest):
        self.job_id = uuid4().hex
        self.payload = payload
        self.status: Literal["running", "success", "error"] = "running"
        self.error: Optional[str] = None
        self.result: Optional[Dict[str, object]] = None
        self.processed = 0
        self.total = 0
        self.updated = 0
        self.images_downloaded = 0
        self._logs: List[Dict[str, object]] = []
        self._log_sequence = 0
        self._lock = threading.Lock()
        self._max_logs = 500
        self._thread = threading.Thread(target=self._run, daemon=True)

    def start(self) -> None:
        self._thread.start()

    def is_running(self) -> bool:
        return self.status == "running" and self._thread.is_alive()

    def snapshot(self) -> CardFetchJobStatus:
        with self._lock:
            logs = [FetchLogEntry(**entry) for entry in self._logs]
            result = CardFetchResponse(**self.result) if self.result else None
            status: Literal["idle", "running", "success", "error"] = (
                self.status if self.status in {"success", "error"} else "running"
            )
            return CardFetchJobStatus(
                jobId=self.job_id,
                status=status,
                logs=logs,
                processed=self.processed,
                total=self.total,
                updated=self.updated,
                imagesDownloaded=self.images_downloaded,
                result=result,
                error=self.error,
            )

    def _emit(
        self,
        level: Literal["info", "warning", "error"],
        message: str,
        *,
        processed: int,
        total: int,
        updated: int,
        images_downloaded: int,
        entry: Optional[Dict[str, object]] = None,
    ) -> None:
        with self._lock:
            self._log_sequence += 1
            payload: Dict[str, object] = {
                "id": self._log_sequence,
                "timestamp": time.time(),
                "level": level,
                "message": message,
                "processed": processed,
                "total": total,
                "updated": updated,
                "imagesDownloaded": images_downloaded,
            }
            if entry:
                card_name = str(entry.get("name") or "").strip()
                set_code = str(entry.get("set_code") or "").strip()
                if card_name:
                    payload["cardName"] = card_name
                if set_code:
                    payload["setCode"] = set_code
            self._logs.append(payload)
            if len(self._logs) > self._max_logs:
                self._logs = self._logs[-self._max_logs :]

    def _handle_progress(self, event: Dict[str, object]) -> None:
        entry = event.get("entry") if isinstance(event.get("entry"), dict) else None
        processed = int(event.get("processed") or self.processed)
        total = int(event.get("total") or self.total)
        updated = int(event.get("updated") or self.updated)
        images_downloaded = int(
            event.get("imagesDownloaded") or self.images_downloaded
        )
        message = str(event.get("message") or "").strip()
        level_value = str(event.get("level") or "info")
        level: Literal["info", "warning", "error"] = "info"
        if level_value in {"info", "warning", "error"}:
            level = cast(Literal["info", "warning", "error"], level_value)

        with self._lock:
            self.processed = processed
            self.total = max(self.total, total)
            self.updated = updated
            self.images_downloaded = images_downloaded

        event_type = str(event.get("type") or "")
        if not message:
            if event_type == "start":
                message = f"开始抓取，共 {total} 张牌"
            elif event_type == "card:start" and entry:
                card_name = entry.get("name") or "未知卡牌"
                set_code = entry.get("set_code") or ""
                suffix = f" ({set_code})" if set_code else ""
                message = f"正在处理 {card_name}{suffix}"
            elif event_type == "card:success" and entry:
                card_name = entry.get("name") or "未知卡牌"
                set_code = entry.get("set_code") or ""
                suffix = f" ({set_code})" if set_code else ""
                message = f"完成 {card_name}{suffix}"
            elif event_type == "card:error" and entry:
                card_name = entry.get("name") or "未知卡牌"
                message = f"{card_name} 处理失败"
            elif event_type == "complete":
                message = "抓取完成"

        self._emit(
            level,
            message or "",
            processed=processed,
            total=total,
            updated=updated,
            images_downloaded=images_downloaded,
            entry=entry,
        )

    def _initialise_paths(self) -> Dict[str, Path]:
        data_path = _resolve_path_within_base(self.payload.dataFileName)
        card_list_path = _resolve_path_within_base(self.payload.cardListName)
        image_folder_path = _resolve_path_within_base(self.payload.imageFolderName)
        return {
            "data": data_path,
            "card_list": card_list_path,
            "images": image_folder_path,
        }

    def _run(self) -> None:
        try:
            config = load_config(CONFIG_PATH)
            paths = self._initialise_paths()
            result = get_cards_information(
                str(paths["images"]),
                str(paths["data"]),
                str(paths["card_list"]),
                dict(config.get("stax_type", {})),
                from_scratch=self.payload.fromScratch,
                download_images=self.payload.downloadImages,
                progress_callback=self._handle_progress,
            )
        except FileNotFoundError as exc:
            self._handle_failure(str(exc))
            return
        except ValueError as exc:
            self._handle_failure(str(exc))
            return
        except HTTPException as exc:
            detail = str(exc.detail) if hasattr(exc, "detail") else str(exc)
            self._handle_failure(detail)
            return
        except Exception as exc:  # pragma: no cover - unexpected failure
            self._handle_failure(f"抓取过程中出现错误: {exc}")
            return

        _load_cards_payload(force=True)

        with self._lock:
            self.status = "success"
            self.result = result
            self.processed = int(result.get("cardsProcessed", self.processed))
            self.updated = int(result.get("cardsUpdated", self.updated))
            self.images_downloaded = int(
                result.get("imagesDownloaded", self.images_downloaded)
            )
            self.total = int(result.get("cardsProcessed", self.total or self.processed))
            self.error = None

    def _handle_failure(self, message: str) -> None:
        with self._lock:
            self.status = "error"
            self.error = message
        self._emit(
            "error",
            message,
            processed=self.processed,
            total=self.total,
            updated=self.updated,
            images_downloaded=self.images_downloaded,
        )


class FetchJobManager:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._job: Optional[CardFetchJob] = None

    def start(self, payload: CardFetchRequest) -> CardFetchJobStatus:
        with self._lock:
            if self._job and self._job.is_running():
                raise RuntimeError("已有抓取任务正在运行")
            job = CardFetchJob(payload)
            self._job = job
            job.start()
            return job.snapshot()

    def get_status(self, job_id: Optional[str] = None) -> CardFetchJobStatus:
        with self._lock:
            if not self._job:
                return CardFetchJobStatus(
                    jobId=None,
                    status="idle",
                    logs=[],
                    processed=0,
                    total=0,
                    updated=0,
                    imagesDownloaded=0,
                    result=None,
                    error=None,
                )

            status = self._job.snapshot()
            if job_id and status.jobId != job_id and status.status in {"success", "error"}:
                return CardFetchJobStatus(
                    jobId=None,
                    status="idle",
                    logs=[],
                    processed=0,
                    total=0,
                    updated=0,
                    imagesDownloaded=0,
                    result=None,
                    error=None,
                )
            return status


fetch_job_manager = FetchJobManager()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

images_dir = BASE_DIR / str(CONFIG["image_folder_name"])
symbols_dir = BASE_DIR / "Symbols"

if images_dir.exists():
    app.mount("/images", StaticFiles(directory=images_dir), name="images")

if symbols_dir.exists():
    app.mount("/symbols", StaticFiles(directory=symbols_dir), name="symbols")


def _parse_mana_cost(raw_cost: Optional[str]) -> List[str]:
    if not raw_cost:
        return []
    text = str(raw_cost).strip()
    if not text:
        return []
    if "{" not in text:
        return [text.upper()]
    return [token.upper() for token in _mana_pattern.findall(text)]


def _face_to_api(face: CardFaceRecord) -> CardFace:
    image_name = face.image_file.strip()
    image_path = f"/images/{image_name}" if image_name else ""
    mana_cost = _parse_mana_cost(face.mana_cost)
    chinese_name = face.chinese_name.strip() if face.chinese_name else ""
    english_name = face.english_name.strip()
    return CardFace(
        englishName=english_name,
        chineseName=chinese_name or english_name,
        image=image_path,
        manaCost=mana_cost,
        cardType=face.card_type,
        description=face.description,
    )


def _build_stax_type_entry(key: Optional[str]) -> Optional[StaxType]:
    if not key:
        return None
    label = str(CONFIG.get("stax_type", {}).get(key, key))
    return StaxType(key=key, label=label)
def _record_to_card(record: CardRecord) -> Optional[Card]:
    if not record.faces:
        return None
    faces = [_face_to_api(face) for face in record.faces]
    stax_type = _build_stax_type_entry(record.stax_type)
    legalities = extract_legalities(record.legalities)
    kind = record.kind if record.kind in {"single", "multiface"} else "single"
    return Card(
        id=record.id or f"card-{faces[0].englishName}",
        kind=kind,
        faces=faces,
        staxType=stax_type,
        isRestricted=bool(record.is_restricted),
        legalities=legalities,
        manaValue=int(record.mana_value),
        sortCardType=record.sort_card_type or "其他",
    )


def _card_sort_key(card: Card) -> tuple[str, str]:
    primary = card.faces[0] if card.faces else None
    name = primary.englishName if primary else card.id
    return (name.lower(), card.id)


def _load_cards_payload(force: bool = False) -> Dict[str, object]:
    global _cached_payload, _cached_mtime

    data_path = BASE_DIR / str(CONFIG["data_file_name"])
    if not data_path.exists():
        raise FileNotFoundError(f"Card data file not found at {data_path}")

    mtime = data_path.stat().st_mtime
    with _cache_lock:
        if not force and _cached_payload is not None and _cached_mtime == mtime:
            return _cached_payload

        store = load_card_store(data_path)
        cards: List[Card] = []
        for record in store.cards.values():
            record.legalities = _clean_legalities(record.legalities)
            card = _record_to_card(record)
            if card is not None:
                cards.append(card)

        cards.sort(key=_card_sort_key)

        payload = {
            "cards": cards,
            "metadata": {
                "staxTypes": _build_stax_types(),
                "cardTypeOrder": CARD_TYPE_ORDER,
            },
        }

        _cached_payload = payload
        _cached_mtime = mtime
        return payload
@lru_cache()
def _build_stax_types() -> List[StaxType]:
    mapping = CONFIG.get("stax_type", {})
    stax_types = [StaxType(key=key, label=str(label)) for key, label in mapping.items()]
    stax_types.sort(key=lambda item: item.label)
    return stax_types


def _resolve_path_within_base(path_value: str | Path) -> Path:
    candidate = Path(path_value)
    if not candidate.is_absolute():
        candidate = BASE_DIR / candidate
    candidate = candidate.resolve()
    try:
        candidate.relative_to(BASE_DIR)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="提供的路径不在项目目录内") from exc
    return candidate


def _relative_to_base(path_value: Path) -> str:
    return str(path_value.relative_to(BASE_DIR))


@app.get("/health")
def health_check() -> Dict[str, str]:
    return {"status": "ok"}


@app.get("/cards", response_model=List[Card])
def list_cards(force_reload: bool = Query(False, alias="reload")) -> List[Card]:
    payload = _load_cards_payload(force=force_reload)
    return payload["cards"]  # type: ignore[return-value]


@app.get("/metadata", response_model=Metadata)
def get_metadata() -> Metadata:
    payload = _load_cards_payload()
    metadata = payload["metadata"]
    return Metadata(**metadata)  # type: ignore[arg-type]


@app.get("/cards/{card_id}", response_model=Card)
def get_card(card_id: str) -> Card:
    payload = _load_cards_payload()
    cards: Iterable[Card] = payload["cards"]  # type: ignore[assignment]
    for card in cards:
        if card.id == card_id:
            return card
    raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Card not found")


@app.get("/latex/settings", response_model=LatexSettings)
def get_latex_settings() -> LatexSettings:
    config = load_config(CONFIG_PATH)
    return LatexSettings(
        dataFileName=str(config.get("data_file_name", "card_data.json")),
        latexTextName=str(config.get("latex_text_name", "latex_text.txt")),
        latexFileName=str(config.get("latex_file_name", "AllThatStax.tex")),
        latexCommand=list(DEFAULT_COMMAND),
    )


@app.post("/latex/generate", response_model=LatexGenerationResponse)
def generate_latex(payload: LatexGenerationRequest) -> LatexGenerationResponse:
    config = load_config(CONFIG_PATH)

    data_path = _resolve_path_within_base(payload.dataFileName)
    latex_text_path = _resolve_path_within_base(payload.latexTextName)
    latex_file_path = _resolve_path_within_base(payload.latexFileName)

    card_list_path = _resolve_path_within_base(str(config.get("card_list_name", "card_list.txt")))
    image_folder_path = _resolve_path_within_base(str(config.get("image_folder_name", "Images")))

    command = payload.latexCommand[:] if payload.latexCommand else list(DEFAULT_COMMAND)

    try:
        if payload.fetchCards or payload.fetchFromScratch:
            get_cards_information(
                str(image_folder_path),
                str(data_path),
                str(card_list_path),
                dict(config.get("stax_type", {})),
                from_scratch=payload.fetchFromScratch,
                download_images=payload.downloadImages,
            )

        latex_text_result = generate_latex_text(
            data_file_name=str(data_path),
            latex_text_name=str(latex_text_path),
            config_path=str(CONFIG_PATH),
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    stdout = None
    stderr = None
    pdf_path: Optional[Path] = None

    if not payload.skipCompile:
        try:
            result = run_latex(
                latex_file_name=str(latex_file_path),
                latex_text_name=str(latex_text_result),
                command=command,
            )
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except RuntimeError as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc
        except CalledProcessError as exc:
            stdout = exc.stdout or None
            stderr = exc.stderr or None
            pdf_candidate = latex_file_path.with_suffix(".pdf")
            if pdf_candidate.exists():
                pdf_path = pdf_candidate
            return LatexGenerationResponse(
                latexTextPath=_relative_to_base(latex_text_path),
                pdfPath=_relative_to_base(pdf_path) if pdf_path else None,
                command=command,
                stdout=stdout,
                stderr=stderr,
            )
        stdout = result.stdout or None
        stderr = result.stderr or None
        pdf_candidate = latex_file_path.with_suffix(".pdf")
        if pdf_candidate.exists():
            pdf_path = pdf_candidate

    response = LatexGenerationResponse(
        latexTextPath=_relative_to_base(latex_text_path),
        pdfPath=_relative_to_base(pdf_path) if pdf_path else None,
        command=command,
        stdout=stdout,
        stderr=stderr,
    )

    return response


@app.get("/cards/fetch/settings", response_model=CardFetchSettings)
def get_fetch_settings() -> CardFetchSettings:
    config = load_config(CONFIG_PATH)
    deck_url = str(config.get("moxfield_deck_url", "")).strip()
    return CardFetchSettings(
        cardListName=str(config.get("card_list_name", "card_list.txt")),
        dataFileName=str(config.get("data_file_name", "card_data.json")),
        imageFolderName=str(config.get("image_folder_name", "Images")),
        downloadImages=True,
        moxfieldDeckUrl=deck_url or None,
    )


@app.post("/cards/fetch/start", response_model=CardFetchJobStatus)
def start_card_fetch(payload: CardFetchRequest) -> CardFetchJobStatus:
    try:
        return fetch_job_manager.start(payload)
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.get("/cards/fetch/status", response_model=CardFetchJobStatus)
def get_card_fetch_status(job_id: Optional[str] = Query(None, alias="jobId")) -> CardFetchJobStatus:
    return fetch_job_manager.get_status(job_id=job_id)


@app.post("/cards/fetch", response_model=CardFetchResponse)
def fetch_cards(payload: CardFetchRequest) -> CardFetchResponse:
    config = load_config(CONFIG_PATH)

    data_path = _resolve_path_within_base(payload.dataFileName)
    card_list_path = _resolve_path_within_base(payload.cardListName)
    image_folder_path = _resolve_path_within_base(payload.imageFolderName)

    result = get_cards_information(
        str(image_folder_path),
        str(data_path),
        str(card_list_path),
        dict(config.get("stax_type", {})),
        from_scratch=payload.fromScratch,
        download_images=payload.downloadImages,
    )

    _load_cards_payload(force=True)
    return CardFetchResponse(**result)


@app.post("/cards/fetch/moxfield", response_model=MoxfieldFetchResponse)
def fetch_moxfield_deck(payload: MoxfieldFetchRequest) -> MoxfieldFetchResponse:
    config = load_config(CONFIG_PATH)

    deck_url = payload.deckUrl.strip()
    if not deck_url:
        raise HTTPException(status_code=400, detail="需要提供 Moxfield 牌表链接")

    card_list_value = (
        payload.cardListName
        if payload.cardListName and payload.cardListName.strip()
        else str(config.get("card_list_name", "card_list.txt"))
    )

    destination = _resolve_path_within_base(card_list_value)

    try:
        count, saved_path = save_deck_to_file(deck_url, destination)
    except MoxfieldError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except requests.RequestException as exc:  # pragma: no cover - network failure
        raise HTTPException(
            status_code=502,
            detail=f"请求 Moxfield 失败: {exc}",
        ) from exc
    except OSError as exc:  # pragma: no cover - filesystem failure
        raise HTTPException(status_code=500, detail=f"写入牌表失败: {exc}") from exc

    return MoxfieldFetchResponse(
        cardsWritten=count,
        cardListPath=_relative_to_base(saved_path),
    )


@app.get("/latex/download")
def download_latex_pdf(path: str = Query(..., description="相对于项目根目录的 PDF 路径")) -> FileResponse:
    file_path = _resolve_path_within_base(path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="指定的文件不存在")
    if file_path.suffix.lower() != ".pdf":
        raise HTTPException(status_code=400, detail="仅支持下载 PDF 文件")
    return FileResponse(file_path, filename=file_path.name, media_type="application/pdf")


@app.exception_handler(FileNotFoundError)
async def _handle_missing_file(_: "FileNotFoundError") -> JSONResponse:
    return JSONResponse(status_code=500, content={"detail": "Required data file is missing."})
