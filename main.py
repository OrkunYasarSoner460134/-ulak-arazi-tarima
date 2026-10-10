# main.py - Ulak arazi on tarama sunucusu
from __future__ import annotations

import json
import logging
import os
import sys
import time
from datetime import date, timedelta
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("ulak")

BASE_DIR = Path(__file__).resolve().parent
# llm paketi hem ./llm hem ./Ulak/llm altinda olabilir; iki duzeni de destekle
for _candidate in (BASE_DIR / "llm", BASE_DIR / "Ulak" / "llm"):
    if _candidate.is_dir() and str(_candidate.parent) not in sys.path:
        sys.path.insert(0, str(_candidate.parent))

EARTH_ENGINE_PROJECT = os.environ.get("EARTH_ENGINE_PROJECT", "terrakalkan")
CACHE_TTL_SECONDS = int(os.environ.get("ULAK_CACHE_TTL", "3600"))

ee_ready = False
_cache: dict[str, tuple[float, dict]] = {}

try:
    import ee
    from google.oauth2 import service_account
except ImportError:  # eksik bagimlilik acik hata versin
    ee = None  # type: ignore
    service_account = None  # type: ignore


def ensure_earth_engine():
    global ee_ready
    if ee_ready:
        return
    if ee is None:
        raise HTTPException(status_code=503, detail="Earth Engine kutuphanesi sunucuda kurulu degil (earthengine-api).")
    try:
        service_account_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
        if service_account_json:
            if service_account is None:
                raise RuntimeError("google-auth kurulu degil")
            credentials = service_account.Credentials.from_service_account_info(
                json.loads(service_account_json),
                scopes=["https://www.googleapis.com/auth/earthengine"],
            )
            ee.Initialize(credentials=credentials, project=EARTH_ENGINE_PROJECT)
        else:
            ee.Initialize(project=EARTH_ENGINE_PROJECT)
        ee_ready = True
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Earth Engine baslatilamadi")
        raise HTTPException(
            status_code=503,
            detail="Earth Engine kimlik dogrulamasi veya proje erisimi basarisiz. Sunucu loglarini kontrol edin.",
        ) from exc


def _cache_get(key: str):
    item = _cache.get(key)
    if not item:
        return None
    expires_at, value = item
    if expires_at < time.time():
        _cache.pop(key, None)
        return None
    return value


def _cache_set(key: str, value: dict):
    _cache[key] = (time.time() + CACHE_TTL_SECONDS, value)
    if len(_cache) > 2000:  # bellek sismemesi icin en eski kaydi at
        _cache.pop(next(iter(_cache)))


def _cache_key(kind: str, lat: float, lng: float) -> str:
    return f"{kind}:{round(lat, 4)}:{round(lng, 4)}"


app = FastAPI(title="Ulak Arazi On Tarama API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


@app.get("/", include_in_schema=False)
def index():
    return FileResponse(
        BASE_DIR / "index.html",
        headers={"Cache-Control": "no-store, no-cache, must-revalidate, max-age=0"},
    )


@app.get("/health")
def health():
    return {"status": "ok", "earth_engine_project": EARTH_ENGINE_PROJECT}


class CoordinateInput(BaseModel):
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)


class ChatRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=1000)


def classify_soil(clay_value: float, sand_value: float, silt_value: float) -> str:
    if clay_value >= 40:
        return "Agir Killi Zemin (Dusuk Su Gecirgenligi)"
    if sand_value >= 85:
        return "Kumlu Zemin (Yuksek Gecirgenlik)"
    if sand_value >= 70:
        return "Kumlu-Tinli Zemin (Gecirgen)"
    if clay_value >= 27 and sand_value <= 20:
        return "Siltli-Killi Zemin (Kaygan)"
    if silt_value >= 80:
        return "Siltli Zemin (Erozyon Hassas)"
    if 20 <= clay_value < 35 and sand_value >= 20:
        return "Killi-Tinli Zemin (Orta Gecirgenlik)"
    return "Tinli Zemin (Dengeli)"


def soil_risk_score(clay_value: float, sand_value: float, silt_value: float) -> float:
    score = (silt_value * 0.8) + (clay_value * 0.3) - (sand_value * 0.3)
    return round(max(min(score, 100), 5), 1)


def slope_risk_score(slope_deg: float) -> float:
    if slope_deg <= 2:
        risk = slope_deg * 5
    elif slope_deg <= 8:
        risk = 10 + (slope_deg - 2) * 8
    elif slope_deg <= 15:
        risk = 58 + (slope_deg - 8) * 4
    elif slope_deg <= 25:
        risk = 86 + (slope_deg - 15) * 1.4
    else:
        risk = 100
    return round(min(risk, 100), 1)


def get_soil_data(lat: float, lng: float):
    key = _cache_key("soil", lat, lng)
    cached = _cache_get(key)
    if cached is not None:
        return cached
    try:
        point = ee.Geometry.Point(lng, lat)
        clay_image = ee.Image("OpenLandMap/SOL/SOL_CLAY-WFRACTION_USDA-3A1A1A_M/v02")
        clay_val = clay_image.select("b0").reduceRegion(
            reducer=ee.Reducer.mean(), geometry=point, scale=250
        ).get("b0").getInfo()

        sand_image = ee.Image("OpenLandMap/SOL/SOL_SAND-WFRACTION_USDA-3A1A1A_M/v02")
        sand_val = sand_image.select("b0").reduceRegion(
            reducer=ee.Reducer.mean(), geometry=point, scale=250
        ).get("b0").getInfo()

        if clay_val is None or sand_val is None:
            raise ValueError("Secilen konumda toprak verisi bulunamadi")
        clay_value = round(float(clay_val), 1)
        sand_value = round(float(sand_val), 1)
        silt_value = round(100 - clay_value - sand_value, 1)

        logger.info("Toprak verisi alindi: kil=%.1f%% kum=%.1f%% silt=%.1f%%", clay_value, sand_value, silt_value)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Earth Engine toprak verisi alinamadi")
        raise HTTPException(status_code=502, detail="Bu konum icin Earth Engine toprak verisi alinamadi.") from exc

    result = {
        "type": classify_soil(clay_value, sand_value, silt_value),
        "risk_score": soil_risk_score(clay_value, sand_value, silt_value),
        "clay_percent": clay_value,
        "sand_percent": sand_value,
        "silt_percent": silt_value,
    }
    _cache_set(key, result)
    return result


def get_gee_data(lat: float, lng: float):
    key = _cache_key("gee", lat, lng)
    cached = _cache_get(key)
    if cached is not None:
        return cached
    try:
        point = ee.Geometry.Point(lng, lat)

        elevation = ee.Image("USGS/SRTMGL1_003")
        slope_image = ee.Terrain.slope(elevation)
        slope_val = slope_image.reduceRegion(
            reducer=ee.Reducer.mean(), geometry=point, scale=30
        ).get("slope").getInfo()

        end_date = date.today() + timedelta(days=1)
        start_date = end_date - timedelta(days=365)

        def mask_clouds(image):
            scl = image.select("SCL")
            clear = scl.neq(3).And(scl.neq(8)).And(scl.neq(9)).And(scl.neq(10)).And(scl.neq(11))
            return image.updateMask(clear)

        s2_image = (
            ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
            .filterBounds(point)
            .filterDate(start_date.isoformat(), end_date.isoformat())
            .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 50))
            .map(mask_clouds)
            .median()
        )

        ndvi_image = s2_image.normalizedDifference(["B8", "B4"])
        ndvi_val = ndvi_image.reduceRegion(
            reducer=ee.Reducer.mean(), geometry=point, scale=10
        ).get("nd").getInfo()

        if slope_val is None:
            raise ValueError("Secilen konumda egim verisi bulunamadi")
        slope_float = round(float(slope_val), 1)
        ndvi_float = round(float(ndvi_val), 2) if ndvi_val is not None else None
        logger.info("Uydu verisi alindi: egim=%.1f NDVI=%s", slope_float, ndvi_float if ndvi_float is not None else "yok")

        result = {"slope_degrees": slope_float, "ndvi_value": ndvi_float}
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Earth Engine uydu verisi alinamadi")
        raise HTTPException(status_code=502, detail="Bu konum icin Earth Engine uydu verisi alinamadi.") from exc

    _cache_set(key, result)
    return result


@app.post("/analiz-et")
def analyze_location(coords: CoordinateInput):
    logger.info("Konum analizi istendi: lat=%s lng=%s", coords.lat, coords.lng)
    ensure_earth_engine()
    soil_data = get_soil_data(coords.lat, coords.lng)
    gee_data = get_gee_data(coords.lat, coords.lng)

    slope_deg = gee_data["slope_degrees"]
    slope_risk = slope_risk_score(slope_deg)
    final_risk_score = round((slope_risk * 0.55) + (soil_data["risk_score"] * 0.45))

    return {
        "status": "success",
        "coordinates": {"lat": coords.lat, "lng": coords.lng},
        "metrics": {
            "soil": {
                "name": soil_data["type"],
                "risk_percent": round(soil_data["risk_score"]),
                "clay_percent": soil_data["clay_percent"],
                "sand_percent": soil_data["sand_percent"],
                "silt_percent": soil_data["silt_percent"],
            },
            "topography": {
                "slope_degrees": gee_data["slope_degrees"],
                "risk_percent": round(slope_risk),
            },
            "vegetation": {
                "ndvi_index": gee_data["ndvi_value"],
                "info_only": True,
            },
        },
        "final_risk_score": min(final_risk_score, 100),
        "score_method": "heuristic",
    }


@app.post("/yapay-zeka")
def chat(req: ChatRequest):
    prompt = req.prompt.strip()
    if not prompt:
        raise HTTPException(status_code=422, detail="Soru bos olamaz.")
    try:
        try:
            from llm.local_model import ModelNotReady, generate_answer
        except ImportError:
            from Ulak.llm.local_model import ModelNotReady, generate_answer  # type: ignore
        return generate_answer(prompt)
    except HTTPException:
        raise
    except Exception as exc:
        name = type(exc).__name__
        if name == "ModelNotReady":
            logger.warning("Yerel dil modeli hazir degil: %s", exc)
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        logger.exception("Yerel dil modeli yanit uretemedi")
        raise HTTPException(status_code=503, detail="Yerel dil modeli yanit uretemedi; sunucu loglarini kontrol edin.") from exc
