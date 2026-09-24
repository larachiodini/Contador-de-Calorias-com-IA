"""
Análise da foto de comida usando a API da Anthropic.
Mandamos a imagem + um prompt pedindo estimativa nutricional em JSON puro.
"""
import json
import base64
import anthropic

from config import ANTHROPIC_API_KEY

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

PROMPT = """\
Você é um nutricionista analisando uma foto de uma refeição.

Identifique cada alimento visível e estime, em relação à porção mostrada:
- nome do alimento (em português)
- peso estimado em gramas
- calorias (kcal)
- proteína (g)
- carboidrato (g)
- gordura (g)

Responda ESTRITAMENTE em JSON, sem nenhum texto antes ou depois, seguindo
exatamente este formato:

{
  "alimentos": [
    {"nome": "string", "gramas": number, "calorias": number, "proteina": number, "carboidrato": number, "gordura": number}
  ],
  "total": {"calorias": number, "proteina": number, "carboidrato": number, "gordura": number},
  "observacao": "string curta, ex: baixa confiança se a foto não está clara"
}
"""


def _parse_json(raw_text: str) -> dict:
    raw_text = raw_text.strip().replace("```json", "").replace("```", "").strip()
    try:
        return json.loads(raw_text)
    except json.JSONDecodeError:
        return {
            "alimentos": [],
            "total": {"calorias": 0, "proteina": 0, "carboidrato": 0, "gordura": 0},
            "observacao": "Não consegui interpretar a resposta da análise. Tente novamente.",
        }


def analyze_food_photo(image_bytes: bytes, media_type: str = "image/jpeg") -> dict:
    image_b64 = base64.b64encode(image_bytes).decode("utf-8")

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1000,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": image_b64,
                        },
                    },
                    {"type": "text", "text": PROMPT},
                ],
            }
        ],
    )

    return _parse_json(response.content[0].text)


RECALC_PROMPT = """\
Você está recalculando uma refeição depois que o usuário conferiu/alterou os alimentos e suas quantidades.

Para cada alimento informado, estime os valores nutricionais correspondentes à quantidade informada.
Não invente alimentos que não estejam na lista.

Retorne ESTRITAMENTE JSON, sem markdown, neste formato:

{
  "alimentos": [
    {"nome": "string", "gramas": number, "calorias": number, "proteina": number, "carboidrato": number, "gordura": number}
  ],
  "total": {"calorias": number, "proteina": number, "carboidrato": number, "gordura": number},
  "observacao": "string curta"
}

Lista informada pelo usuário:
"""


def recalculate_foods(alimentos: list[dict]) -> dict:
    itens = [
        {"nome": str(a.get("nome", "")).strip(), "gramas": float(a.get("gramas") or 0)}
        for a in alimentos
    ]

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1200,
        messages=[{
            "role": "user",
            "content": RECALC_PROMPT + json.dumps(itens, ensure_ascii=False),
        }],
    )
    return _parse_json(response.content[0].text)
