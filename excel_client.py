"""
Armazena tudo em um único arquivo .xlsx, com duas abas: "Refeicoes" e "Agua".

Como o arquivo é aberto/salvo a cada operação (em vez de manter em memória),
você pode abrir ele no Excel ou conectar o Power BI direto nele a qualquer
momento sem se preocupar com concorrência de um servidor rodando.

Estrutura:
  Aba "Refeicoes": data | hora | alimento | gramas | calorias | proteina | carboidrato | gordura
  Aba "Agua":      data | hora | quantidade_ml
"""
from datetime import datetime
from pathlib import Path

from openpyxl import Workbook, load_workbook
from openpyxl.worksheet.worksheet import Worksheet

from config import EXCEL_FILE

REFEICOES_HEADERS = ["data", "hora", "alimento", "gramas", "calorias", "proteina", "carboidrato", "gordura"]
AGUA_HEADERS = ["data", "hora", "quantidade_ml"]


def _load_workbook() -> Workbook:
    if Path(EXCEL_FILE).exists():
        return load_workbook(EXCEL_FILE)

    wb = Workbook()
    # a aba padrão criada pelo openpyxl vira "Refeicoes"
    ws_ref = wb.active
    ws_ref.title = "Refeicoes"
    ws_ref.append(REFEICOES_HEADERS)

    ws_agua = wb.create_sheet("Agua")
    ws_agua.append(AGUA_HEADERS)

    wb.save(EXCEL_FILE)
    return wb


def _get_sheet(wb: Workbook, name: str, headers: list[str]) -> Worksheet:
    if name not in wb.sheetnames:
        ws = wb.create_sheet(name)
        ws.append(headers)
        return ws
    return wb[name]


def log_refeicao(alimentos: list[dict]) -> None:
    wb = _load_workbook()
    ws = _get_sheet(wb, "Refeicoes", REFEICOES_HEADERS)

    agora = datetime.now()
    data_str = agora.strftime("%Y-%m-%d")
    hora_str = agora.strftime("%H:%M:%S")

    for item in alimentos:
        ws.append([
            data_str, hora_str, item["nome"], item.get("gramas", ""),
            item["calorias"], item["proteina"], item["carboidrato"], item["gordura"],
        ])

    wb.save(EXCEL_FILE)


def excluir_refeicao(linha: int) -> bool:
    """Exclui uma linha específica da aba Refeicoes pelo número da linha do Excel."""
    wb = _load_workbook()
    ws = _get_sheet(wb, "Refeicoes", REFEICOES_HEADERS)

    if linha < 2 or linha > ws.max_row:
        return False

    ws.delete_rows(linha, 1)
    wb.save(EXCEL_FILE)
    return True


def log_agua(quantidade_ml: float) -> None:
    wb = _load_workbook()
    ws = _get_sheet(wb, "Agua", AGUA_HEADERS)

    agora = datetime.now()
    ws.append([agora.strftime("%Y-%m-%d"), agora.strftime("%H:%M:%S"), quantidade_ml])

    wb.save(EXCEL_FILE)


def totais_do_dia() -> dict:
    wb = _load_workbook()
    hoje = datetime.now().strftime("%Y-%m-%d")

    ws_ref = _get_sheet(wb, "Refeicoes", REFEICOES_HEADERS)
    totais = {"calorias": 0.0, "proteina": 0.0, "carboidrato": 0.0, "gordura": 0.0}
    refeicoes_hoje = []
    for row_idx, row in enumerate(ws_ref.iter_rows(min_row=2, values_only=True), start=2):
        data, hora, alimento, gramas, calorias, proteina, carboidrato, gordura = row
        if data == hoje:
            totais["calorias"] += float(calorias or 0)
            totais["proteina"] += float(proteina or 0)
            totais["carboidrato"] += float(carboidrato or 0)
            totais["gordura"] += float(gordura or 0)
            refeicoes_hoje.append({
                "id": row_idx,
                "hora": hora, "alimento": alimento, "gramas": gramas, "calorias": calorias,
            })

    ws_agua = _get_sheet(wb, "Agua", AGUA_HEADERS)
    agua_total = 0.0
    for row in ws_agua.iter_rows(min_row=2, values_only=True):
        data, hora, quantidade = row
        if data == hoje:
            agua_total += float(quantidade or 0)

    totais["agua_ml"] = agua_total
    totais["refeicoes"] = refeicoes_hoje
    return totais
