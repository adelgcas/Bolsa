"""Configuración: mercados, acciones y relaciones directas/indirectas con noticias.

Para añadir o quitar acciones edita UNIVERSE (ticker de Yahoo Finance):
    "TICKER": ("búsqueda de noticias en inglés", "sector", "mercado", "nombre a mostrar")
"""

MARKETS = ["EE. UU.", "España", "Europa"]

UNIVERSE = {
    # EE. UU.
    "AAPL": ("Apple iPhone", "tecnologia", "EE. UU.", "Apple"),
    "MSFT": ("Microsoft", "tecnologia", "EE. UU.", "Microsoft"),
    "NVDA": ("Nvidia", "tecnologia", "EE. UU.", "Nvidia"),
    "TSLA": ("Tesla", "automocion", "EE. UU.", "Tesla"),
    "JPM": ("JPMorgan", "banca", "EE. UU.", "JPMorgan"),
    "XOM": ("Exxon Mobil", "energia", "EE. UU.", "Exxon Mobil"),
    # España
    "SAN.MC": ("Banco Santander", "banca", "España", "Santander"),
    "BBVA.MC": ("BBVA bank", "banca", "España", "BBVA"),
    "ITX.MC": ("Inditex", "consumo", "España", "Inditex"),
    "IBE.MC": ("Iberdrola", "utilities", "España", "Iberdrola"),
    "TEF.MC": ("Telefonica", "telecom", "España", "Telefónica"),
    "REP.MC": ("Repsol", "energia", "España", "Repsol"),
    # Europa
    "ASML.AS": ("ASML", "tecnologia", "Europa", "ASML"),
    "SAP.DE": ("SAP software", "tecnologia", "Europa", "SAP"),
    "MC.PA": ("LVMH", "consumo", "Europa", "LVMH"),
    "SIE.DE": ("Siemens", "industria", "Europa", "Siemens"),
    "NESN.SW": ("Nestle", "consumo", "Europa", "Nestlé"),
    "SHEL.L": ("Shell oil", "energia", "Europa", "Shell"),
}

# sector -> consulta de noticias indirectas (cadena de suministro, regulación, materias primas...)
SECTOR_QUERIES = {
    "tecnologia": "semiconductors OR chips OR artificial intelligence regulation",
    "automocion": "electric vehicles OR lithium OR car tariffs",
    "energia": "oil price OR OPEC OR natural gas",
    "banca": "interest rates OR bank regulation OR credit defaults",
    "consumo": "consumer spending OR retail sales OR inflation",
    "utilities": "electricity prices OR renewable energy OR utility regulation",
    "telecom": "telecom spectrum OR 5G OR broadband regulation",
    "industria": "manufacturing PMI OR industrial production OR automation",
}

# noticias macro que afectan a todo el mercado
MACRO_QUERY = "Federal Reserve OR ECB OR inflation OR recession OR tariffs OR geopolitical"

YEARS_HISTORY = 3          # años de histórico de precios y noticias
HORIZON_DAYS = 5           # horizonte de la señal (días bursátiles)
BUY_THRESHOLD = 0.01       # retorno esperado > +1 % -> COMPRAR
SELL_THRESHOLD = -0.01     # retorno esperado < -1 % -> VENDER
CACHE_DIR = "cache"
