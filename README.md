# Dashboard Financiero Colombia

Proyecto en Python/Dash para visualizar indicadores economicos y financieros de Colombia:

- COLCAP oficial diario en puntos y base 100.
- Comparacion con el indice equiponderado y las "7 Magnificas" heredados,
  rotulados como reconstrucciones sinteticas bajo revision.
- Inflacion mensual y anual.
- Crecimiento real trimestral del PIB DANE.
- Curva y series historicas de TES en pesos.

El repositorio combina scripts de actualizacion de datos, archivos CSV/Excel limpios, la aplicacion Dash para uso local/Render y una version independiente para GitHub Pages.

## Como ejecutar el dashboard

1. Instalar dependencias:

```bash
pip install -r requirements.txt
```

2. Ejecutar la aplicacion:

```bash
python dashboard_colombia.py
```

3. Abrir en el navegador:

```text
http://127.0.0.1:8050
```

## Archivos principales

| Archivo | Proposito |
| --- | --- |
| `dashboard_colombia.py` | Aplicacion Dash. Carga los CSV, arma los graficos, define el layout y controla la interaccion por callbacks. |
| `actualizar_todo.py` | Orquestador de fuentes oficiales y tabla experimental mensual. |
| `actualizar_inflacion.py` | Contrasta IPC BanRep con variaciones publicadas por DANE. |
| `actualizar_tes.py` | Descarga tasas TES desde BanRep. |
| `actualizar_pib.py` | Lee anexos trimestrales de volumen y precios corrientes DANE. |
| `actualizar_colcap.py` | Descarga COLCAP diario oficial desde BanRep/BVC. |
| `construir_tablas_experimentales.py` | Audita retornos de canastas mensuales con controles de cobertura. |
| `validar_datos.py` | Verifica formulas, fechas y valores atipicos. |
| `GUIA_ACTUALIZACION.md` | Guia corta de uso operativo. |
| `DOCUMENTACION_TECNICA.md` | Explicacion detallada del flujo de datos, formulas y mantenimiento. |

## Datos generados o consumidos

| Archivo | Descripcion |
| --- | --- |
| `colcap_oficial.csv` | COLCAP publicado por BanRep, en puntos y base 100. |
| `indices_colombia.csv` | Curvas historicas heredadas, visibles como comparacion bajo revision. |
| `tasas_interes_clean.csv` | Series TES pesos y UVR. |
| `inflacion_clean.csv` | Variaciones IPC mensuales y anuales con procedencia por fila. |
| `pib_colombia.csv` | PIB real y nominal trimestral, con formulas separadas. |
| `indices_experimentales_mensuales.csv` | Retornos de canastas de investigacion con cobertura y alertas. |
| `estado_fuentes.csv`, `alertas_datos.csv` | Vigencia y valores bajo revision. |
| `precios_icolcap_limpios.csv`, `Canasta_Historica_ICAP.xls` | Insumos historicos legados; no alimentan la linea oficial. |

## Actualizacion manual

Para actualizar todas las fuentes disponibles:

```bash
python actualizar_todo.py
python validar_datos.py
```

Para ver el estado de una fuente especifica:

```bash
python actualizar_inflacion.py --estado
python actualizar_tes.py --estado
python actualizar_pib.py --estado
```

La actualizacion diaria de GitHub Actions se activa al fusionar el workflow a
`main`. La guia operativa es [OPERACION_DATOS.md](OPERACION_DATOS.md) y el
significado exacto de cada columna esta en [DATA_DICTIONARY.md](DATA_DICTIONARY.md).

## Despliegue

### GitHub Pages

La version publica esta en
<https://estebanmoncadag079-rgb.github.io/GRAFICO-ECONOMIA-COLOMBIANA/>.
`exportar_pages.py` genera HTML, JavaScript, figuras Plotly y datos a partir del
mismo layout y los mismos CSV del dashboard Dash. Las capas, el detalle, la
curva TES y el ciclo funcionan en el navegador, sin servidor Python ni Render.

Para probarla localmente:

```bash
python exportar_pages.py
python -m http.server 8068 --directory site
```

El workflow `publicar-pages.yml` publica el sitio en cada cambio de `main` y
despues de una actualizacion validada de indicadores. GitHub Pages debe tener
como origen **GitHub Actions** en Settings > Pages. El directorio `site/` es
generado y no se sube al repositorio.

### Render (alternativa)

`render.yaml` define un servicio web en Render que instala `requirements.txt` y levanta la app con Gunicorn:

```bash
gunicorn dashboard_colombia:server --workers 1 --timeout 120 --bind 0.0.0.0:$PORT
```

La variable `server` se expone desde `dashboard_colombia.py` para que Gunicorn pueda servir la aplicacion Dash.
Render necesita despliegue automatico desde GitHub para cargar los CSV nuevos;
el proceso web no consulta las fuentes por si mismo.
