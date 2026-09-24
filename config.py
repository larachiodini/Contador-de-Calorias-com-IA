import os
from dotenv import load_dotenv

load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

# Caminho do arquivo Excel onde tudo é gravado.
# Dica: se você apontar isso para uma pasta sincronizada (OneDrive/Google Drive),
# o Power BI consegue ler o arquivo automaticamente sempre que ele mudar.
EXCEL_FILE = os.getenv("EXCEL_FILE", "diario.xlsx")

META_CALORIAS = float(os.getenv("META_CALORIAS", "1650"))
META_PROTEINA = float(os.getenv("META_PROTEINA", "110"))
META_CARBOIDRATO = float(os.getenv("META_CARBOIDRATO", "200"))
META_GORDURA = float(os.getenv("META_GORDURA", "60"))
META_AGUA_ML = float(os.getenv("META_AGUA_ML", "3000"))
