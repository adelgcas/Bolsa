# Recomendaciones de compra y venta + cartera personal

Panel que relaciona el tono de las noticias (de la empresa, su sector y macro) con los movimientos de precio de los últimos años y aplica lo aprendido a la actualidad.

## Pestañas
- **Resumen**: mejores compras y ventas de todos los mercados.
- **Mi cartera**: registra tus compras (ticker, fecha, importe). Calcula tu beneficio y muestra alertas de VENDER o VIGILAR con los motivos (modelo, noticias de la empresa, del sector o macro, límite de pérdida, objetivo de beneficio).
- **EE. UU., España, Europa**: recomendaciones por mercado.

## Archivos
- `app.py`: el panel. `portfolio.py`: análisis de la cartera.
- `config.py`: mercados y acciones. Para añadir una acción, copia una línea de `UNIVERSE`.
- `pipeline.py`, `data.py`, `sentiment.py`: cálculo.

## Cartera
- Tu cartera no se guarda en el servidor. Descárgala en CSV y súbela la próxima vez.
- Los alertas se calculan al pulsar "Analizar mi cartera"; la app no envía correos.
- Para acciones que no están en el panel, el análisis tarda un poco más porque descarga sus noticias.

## Despliegue
Sube todos los archivos a tu repositorio de GitHub sobre los anteriores; Streamlit se actualiza solo.

## Limitaciones
- No es asesoramiento financiero. Un buen resultado histórico no garantiza beneficios futuros.
- El tono de GDELT es una medida general de las noticias.
- Sin comisiones ni conversión de divisas. Datos diarios.
