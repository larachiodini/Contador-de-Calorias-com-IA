"""
Rodar com: uvicorn app:app --reload
Depois abra http://localhost:8000 no navegador.
"""

from datetime import date

from fastapi import FastAPI, UploadFile, File, Request, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Any

import vision_analyzer
import excel_client
from config import (
    META_CALORIAS,
    META_PROTEINA,
    META_CARBOIDRATO,
    META_GORDURA,
    META_AGUA_ML,
)


app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")


# ============================================================
# LIMITE DE USO DA IA
# ============================================================

LIMITE_DIARIO = 3

# Guarda:
# IP -> data + quantidade de usos
LIMITES_IP = {}


def obter_ip(request: Request) -> str:
    """
    Obtém o IP real do usuário quando o app está atrás
    de um proxy como o Render.
    """

    ip = request.headers.get("X-Forwarded-For")

    if ip:
        # O primeiro IP da lista normalmente é o IP original.
        return ip.split(",")[0].strip()

    return request.client.host if request.client else "desconhecido"


def verificar_limite_ip(ip: str):
    """
    Verifica se o IP ainda pode utilizar a IA hoje.
    """

    hoje = date.today().isoformat()

    dados = LIMITES_IP.get(ip)

    # Primeiro acesso ou novo dia
    if not dados or dados["data"] != hoje:
        LIMITES_IP[ip] = {
            "data": hoje,
            "quantidade": 0,
        }
        return

    # Limite atingido
    if dados["quantidade"] >= LIMITE_DIARIO:
        raise HTTPException(
            status_code=429,
            detail=(
                "Você atingiu o limite de 3 análises por dia. "
                "Tente novamente amanhã."
            ),
        )


def registrar_uso_ip(ip: str):
    """
    Registra uma utilização da IA.
    """

    hoje = date.today().isoformat()

    dados = LIMITES_IP.get(ip)

    # Primeiro uso ou novo dia
    if not dados or dados["data"] != hoje:
        LIMITES_IP[ip] = {
            "data": hoje,
            "quantidade": 1,
        }

    else:
        dados["quantidade"] += 1


# ============================================================
# MODELOS
# ============================================================


class AguaPayload(BaseModel):
    quantidade_ml: float


class RefeicaoPayload(BaseModel):
    alimentos: list[dict[str, Any]]


class ExcluirRefeicaoPayload(BaseModel):
    id: int


# ============================================================
# PÁGINA PRINCIPAL
# ============================================================


@app.get("/")
async def index():
    return FileResponse("static/index.html")


# ============================================================
# METAS
# ============================================================


@app.get("/api/metas")
async def metas():
    return {
        "calorias": META_CALORIAS,
        "proteina": META_PROTEINA,
        "carboidrato": META_CARBOIDRATO,
        "gordura": META_GORDURA,
        "agua_ml": META_AGUA_ML,
    }


# ============================================================
# RESUMO
# ============================================================


@app.get("/api/resumo")
async def resumo():
    return excel_client.totais_do_dia()


# ============================================================
# ANALISAR FOTO
# ============================================================


@app.post("/api/analisar-refeicao")
async def analisar_refeicao(
    request: Request,
    foto: UploadFile = File(...),
):
    """
    Analisa a foto usando a IA.

    A análise conta como 1 utilização do limite diário.
    A refeição NÃO é salva automaticamente.
    """

    ip = obter_ip(request)

    # Verifica se ainda pode usar a IA
    verificar_limite_ip(ip)

    # Lê a imagem
    image_bytes = await foto.read()

    # Chama a Anthropic
    analise = vision_analyzer.analyze_food_photo(
        image_bytes,
        media_type=foto.content_type or "image/jpeg",
    )

    # Só contabiliza depois que a chamada à IA foi realizada
    registrar_uso_ip(ip)

    return {
        "analise": analise,
    }


# ============================================================
# RECALCULAR REFEIÇÃO
# ============================================================


@app.post("/api/recalcular-refeicao")
async def recalcular_refeicao(
    request: Request,
    payload: RefeicaoPayload,
):
    """
    Recalcula os valores usando a IA.

    O recálculo também conta como 1 utilização
    do limite diário.
    """

    ip = obter_ip(request)

    # Verifica o limite
    verificar_limite_ip(ip)

    # Chama a IA
    analise = vision_analyzer.recalculate_foods(
        payload.alimentos
    )

    # Registra o uso
    registrar_uso_ip(ip)

    return {
        "analise": analise,
    }


# ============================================================
# CONFIRMAR REFEIÇÃO
# ============================================================


@app.post("/api/confirmar-refeicao")
async def confirmar_refeicao(
    payload: RefeicaoPayload,
):
    """
    Só aqui a refeição é efetivamente gravada no Excel.
    """

    if not payload.alimentos:
        return {
            "ok": False,
            "erro": "Nenhum alimento informado.",
        }

    excel_client.log_refeicao(payload.alimentos)

    return {
        "ok": True,
        "totais": excel_client.totais_do_dia(),
    }


# ============================================================
# COMPATIBILIDADE COM CHAMADAS ANTIGAS
# ============================================================


@app.post("/api/refeicao")
async def registrar_refeicao(
    request: Request,
    foto: UploadFile = File(...),
):
    """
    Compatibilidade com versões antigas do frontend.

    Também respeita o limite da IA.
    """

    ip = obter_ip(request)

    verificar_limite_ip(ip)

    image_bytes = await foto.read()

    analise = vision_analyzer.analyze_food_photo(
        image_bytes,
        media_type=foto.content_type or "image/jpeg",
    )

    registrar_uso_ip(ip)

    return {
        "analise": analise,
        "totais": excel_client.totais_do_dia(),
    }


# ============================================================
# EXCLUIR REFEIÇÃO
# ============================================================


@app.post("/api/excluir-refeicao")
async def excluir_refeicao(
    payload: ExcluirRefeicaoPayload,
):
    ok = excel_client.excluir_refeicao(payload.id)

    if not ok:
        return {
            "ok": False,
            "erro": "Refeição não encontrada.",
        }

    return {
        "ok": True,
        "totais": excel_client.totais_do_dia(),
    }


# ============================================================
# ÁGUA
# ============================================================


@app.post("/api/agua")
async def registrar_agua(
    payload: AguaPayload,
):
    excel_client.log_agua(payload.quantidade_ml)

    return {
        "totais": excel_client.totais_do_dia(),
    }
