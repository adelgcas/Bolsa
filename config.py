"""Configuración: universo de acciones y relaciones directas/indirectas con noticias."""

# ticker -> (consulta de noticias directas, sector)
UNIVERSE = {
    "AAPL": ("Apple iPhone", "tecnologia"),
    "MSFT": ("Microsoft", "tecnologia"),
    "NVDA": ("Nvidia", "tecnologia"),
    "GOOGL": ("Google Alphabet", "tecnologia"),
    "AMZN": ("Amazon", "tecnologia"),
    "TSLA": ("Tesla", "automocion"),
    "XOM": ("Exxon Mobil", "energia"),
    "CVX": ("Chevron", "energia"),
    "JPM": ("JPMorgan", "banca"),
    "BAC": ("Bank of America", "banca"),
    "SAN": ("Banco Santander", "banca"),
    "ITX.MC": ("Inditex", "consumo"),
}

# sector -> consulta de noticias indirectas (cadena de suministro, regulación, materias primas...)
SECTOR_QUERIES = {
    "tecnologia": "semiconductors OR chips OR artificial intelligence regulation",
    "automocion": "electric vehicles OR lithium OR car tariffs",
    "energia": "oil price OR OPEC OR natural gas",
    "banca": "interest rates OR bank regulation OR credit defaults",
    "consumo": "consumer spending OR retail sales OR inflation",
}

# noticias macro que afectan a todo el mercado
MACRO_QUERY = "Federal Reserve OR ECB OR inflation OR recession OR tariffs OR geopolitical"

YEARS_HISTORY = 3          # años de histórico de precios y noticias
HORIZON_DAYS = 5           # horizonte de la señal (días bursátiles)
BUY_THRESHOLD = 0.01       # retorno esperado > +1 % -> COMPRAR
SELL_THRESHOLD = -0.01     # retorno esperado < -1 % -> VENDER
CACHE_DIR = "cache"
