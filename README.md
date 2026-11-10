# Señales bursátiles por noticias

Relaciona el tono de las noticias (de la empresa, de su sector y macro) con los movimientos de precio de los últimos años y aplica lo aprendido a la actualidad.

## Cómo funciona
1. **Precios**: `yfinance` (3 años, ver `config.py`).
2. **Noticias**: GDELT (gratuito). Series diarias de tono y volumen desde 2017 para cada tema: empresa, sector (chips, petróleo, tipos...) y macro.
3. **Modelo**: gradient boosting que predice el retorno a 5 días con sentimiento directo/sector/macro, volumen de noticias, momentum y volatilidad.
4. **Validación**: walk-forward (entrena con el pasado, prueba con el futuro).
5. **Señal**: COMPRAR / VENDER / MANTENER según el retorno esperado, con los titulares recientes bajo demanda.

## Despliegue online (sin instalar nada)
1. Crea un repositorio en GitHub y sube estos archivos (botón "Add file > Upload files").
2. Entra en share.streamlit.io con tu cuenta de GitHub > "Create app" > elige el repo y `app.py` > Deploy.

## Limitaciones
- No es asesoramiento financiero; un buen backtest no garantiza beneficios futuros.
- El tono de GDELT es una medida general de las noticias, no específica de bolsa.
- Sin comisiones ni gestión de riesgo.
- Datos diarios: no sirve para operar intradía.
