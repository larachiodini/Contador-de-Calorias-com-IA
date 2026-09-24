"""
Rodar com: uvicorn app:app --reload
Depois abra http://localhost:8000 no navegador.
"""
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Any

import vision_analyzer
import excel_client
from config import META_CALORIAS, META_PROTEINA, META_CARBOIDRATO, META_GORDURA, META_AGUA_ML

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")


class AguaPayload(BaseModel):
    quantidade_ml: float


class RefeicaoPayload(BaseModel):
    alimentos: list[dict[str, Any]]


class ExcluirRefeicaoPayload(BaseModel):
    id: int


@app.get("/")
async def index():
    return FileResponse("static/index.html")


@app.get("/api/metas")
async def metas():
    return {
        "calorias": META_CALORIAS,
        "proteina": META_PROTEINA,
        "carboidrato": META_CARBOIDRATO,
        "gordura": META_GORDURA,
        "agua_ml": META_AGUA_ML,
    }


@app.get("/api/resumo")
async def resumo():
    return excel_client.totais_do_dia()


@app.post("/api/analisar-refeicao")
async def analisar_refeicao(foto: UploadFile = File(...)):
    """Analisa a foto, mas NÃO salva nada no Excel."""
    image_bytes = await foto.read()
    analise = vision_analyzer.analyze_food_photo(
        image_bytes, media_type=foto.content_type or "image/jpeg"
    )
    return {"analise": analise}


@app.post("/api/recalcular-refeicao")
async def recalcular_refeicao(payload: RefeicaoPayload):
    """Recalcula os valores depois que o usuário altera os alimentos/quantidades."""
    return {"analise": vision_analyzer.recalculate_foods(payload.alimentos)}


@app.post("/api/confirmar-refeicao")
async def confirmar_refeicao(payload: RefeicaoPayload):
    """Só aqui a refeição é efetivamente gravada no Excel."""
    if not payload.alimentos:
        return {"ok": False, "erro": "Nenhum alimento informado."}

    excel_client.log_refeicao(payload.alimentos)
    return {"ok": True, "totais": excel_client.totais_do_dia()}


# Compatibilidade com chamadas antigas: agora não grava automaticamente.
@app.post("/api/refeicao")
async def registrar_refeicao(foto: UploadFile = File(...)):
    image_bytes = await foto.read()
    analise = vision_analyzer.analyze_food_photo(
        image_bytes, media_type=foto.content_type or "image/jpeg"
    )
    return {"analise": analise, "totais": excel_client.totais_do_dia()}


@app.post("/api/excluir-refeicao")
async def excluir_refeicao(payload: ExcluirRefeicaoPayload):
    ok = excel_client.excluir_refeicao(payload.id)
    if not ok:
        return {"ok": False, "erro": "Refeição não encontrada."}
    return {"ok": True, "totais": excel_client.totais_do_dia()}


@app.post("/api/agua")
async def registrar_agua(payload: AguaPayload):
    excel_client.log_agua(payload.quantidade_ml)
    return {"totais": excel_client.totais_do_dia()}
