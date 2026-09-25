# Diccionario de datos

Esta es la especificacion de las tablas que alimentan el dashboard. La fecha
de una observacion es el periodo medido, no necesariamente el dia en que el
dato se conocio. Cada archivo mantiene su frecuencia propia.

| Tabla | Grano | Fuente | Uso |
| --- | --- | --- | --- |
| `pib_colombia.csv` | Un trimestre, fechado al primer dia | [DANE, anexos PIB produccion](https://www.dane.gov.co/index.php/estadisticas-por-tema/cuentas-nacionales/cuentas-nacionales-trimestrales/pib-informacion-tecnica) | Actividad real y nominal |
| `inflacion_clean.csv` | Un mes, fechado al primer dia | [DANE, IPC](https://www.dane.gov.co/index.php/estadisticas-por-tema/precios-y-costos/indice-de-precios-al-consumidor-ipc/ipc-informacion-tecnica) y BanRep, serie 15000 | Inflacion |
| `tasas_interes_clean.csv` | Dia de observacion | BanRep, series 15272 a 15277 | Curva cero cupon TES |
| `colcap_oficial.csv` | Dia de mercado | [BanRep/BVC, indice COLCAP](https://suameca.banrep.gov.co/estadisticas-economicas/informacionSerie/2500/indice_mercado_accionario_colcap), serie 6 | Mercado accionario oficial |
| `indices_experimentales_mensuales.csv` | Mes, fechado al primer dia | Precios locales y canasta historica local | Auditoria y cobertura de las canastas propias |
| `indices_colombia.csv` | Dia sintetico historico | Construccion heredada con precios mensuales y empalme NAV | Lineas comparativas punteadas, no datos oficiales diarios |
| `estado_fuentes.csv` | Una fila por fuente | `validar_datos.py` | Fecha y estado de las fuentes |
| `alertas_datos.csv` | Una alerta por observacion | `validar_datos.py` | Valores TES aislados bajo revision |

## PIB trimestral

El actualizador lee el ultimo anexo de produccion a precios constantes y el
ultimo a precios corrientes. Usa la fila **Producto Interno Bruto** del
`Cuadro 1` (serie original) y `Cuadro 4` (serie ajustada por estacionalidad).
El DANE puede revisar toda la historia: cada ejecucion guarda una sola
**vintage** de los anexos vigentes.

| Columna | Unidad | Definicion |
| --- | --- | --- |
| `fecha`, `trimestre` | Fecha / Tn AAAA | Periodo de referencia |
| `pib_real_miles_millones_ref2015` | Miles de millones, volumen encadenado ref. 2015 | PIB original, excluye efecto de precios |
| `pib_real_ajustado_miles_millones_ref2015` | Misma unidad | PIB ajustado por estacionalidad y calendario |
| `pib_real_yoy` | % | `100 * (real_original_t / real_original_t-4 - 1)` |
| `pib_real_qoq_sa` | % | `100 * (real_ajustado_t / real_ajustado_t-1 - 1)` |
| `pib_nominal_billones_cop` | Billones COP corrientes | Valor corriente / 1000 |
| `pib_nominal_yoy` | % | `100 * (nominal_t / nominal_t-4 - 1)` |
| `fecha_publicacion_vintage` | Fecha | Fecha del anexo vigente; **no** fecha historica de primera publicacion de cada trimestre |
| `fuente`, `estado_dato` | Texto | URL del anexo real y condicion de revision |

El grafico y la tarjeta muestran solo `pib_real_yoy`. El archivo anterior
`pib_crecimiento_yoy` era crecimiento nominal y ya no se consume. El valor
2026-T2 calculado de la serie real es 3.5234%, coherente con el 3.5% publicado
por el DANE al redondear a un decimal.

## IPC mensual

| Columna | Unidad | Definicion |
| --- | --- | --- |
| `inflacion_mensual` | % | Variacion mensual reportada en la tabla historica DANE cuando esta disponible; en meses anteriores, `100 * (IPC_t / IPC_t-1 - 1)` con indice BanRep |
| `inflacion_anual` | % | `100 * (IPC_t / IPC_t-12 - 1)` con indice BanRep; el ultimo mes se reemplaza con la cifra reportada DANE |
| `fuente_mensual`, `fuente_anual` | Texto | Indican cual de los dos metodos produjo cada valor |
| `fecha_publicacion_vintage` | Fecha / `no_disponible` | Fecha verificable del ultimo mes; no se inventan fechas de publicacion historicas |

El indice BanRep tiene dos decimales; calcular variaciones con el indice
redondeado puede diferir 0.01 puntos de las tasas publicadas por el DANE.
Por ejemplo, agosto de 2026 da 6.25% calculado y 6.24% reportado.

## TES diario

`tes_pesos_1y`, `tes_pesos_5y`, `tes_pesos_10y` son porcentajes anuales
de la curva cero cupon TES en pesos para 1, 5 y 10 anos. Las columnas
`tes_uvr_*` son tasas de la curva TES UVR y no se dibujan. El spread de la
tarjeta se calcula como `tes_pesos_10y - tes_pesos_1y`, en puntos porcentuales.
No representa la tasa de un bono individual ni una prediccion automatica.
La tabla original conserva valores publicados. `alertas_datos.csv` registra
un punto si cambia mas de 2 pp respecto de ambos vecinos y los vecinos
difieren menos de 1 pp. Solo el trazo omite esos puntos; su significado
economico y la fuente deben investigarse antes de corregir la tabla.

## COLCAP diario

`colcap_puntos` es el nivel publicado por BanRep (fuente original BVC).
`colcap_base100 = 100 * colcap_puntos / colcap_puntos(2009-02-09)`.
La tarjeta muestra puntos, la linea muestra la serie normalizada. El indice
paso de la metodologia BVC a la de MSCI COLCAP el 2021-05-28. MSCI tomo como
inicio el ultimo nivel BVC del 2021-05-27 y conservo la historia previa: la
continuidad numerica no implica una canasta o ponderaciones constantes. El
grafico senala esta fecha cuando esta dentro del periodo visible. Se refresca
la historia completa para captar correcciones de la fuente.
La transicion y la continuidad de niveles estan documentadas en la
[metodologia MSCI COLCAP de mayo de 2021](https://www.msci.com/eqb/methodology/meth_docs/MSCI_COLCAP_Index_Methodology_May2021.pdf).

La tabla heredada `indices_colombia.csv` empalma `icolcap_referencia.csv` con
retornos de BlackRock. La antigua `datos_colombia_clean.csv` salta de escala
el 2011-07-06. Ninguna se usa para la linea o tarjeta oficial.
La linea empalmada permanece visible como comparacion diagnostica punteada;
no se interpreta como una segunda serie oficial del COLCAP.

## Canastas experimentales

`retorno_equiponderado_pct` y `retorno_lideres_pct` son promedios simples
de retornos mensuales de tickers de la canasta con precios en ambos meses.
`canasta_tickers`, `pares_precio_validos`, `cobertura_canasta` y las
columnas equivalentes de lideres muestran el denominador real. El retorno
queda vacio si la cobertura es menor de 70%, hay menos de cinco pares
(o menos tickers disponibles), o se detecta un retorno individual absoluto
superior a 80%. Los valores atipicos se cuentan y el mes se marca
`sin_cobertura_o_atipicos`; nunca se reemplazan por cero ni se interpolan
a frecuencia diaria.

Esta tabla es **experimental**: faltan precios ajustados por dividendos,
splits y demas eventos corporativos, hay alias historicos y la composicion
posterior a 2021 utiliza una canasta local actual. No permite afirmar que
replica el COLCAP ni comparar rentabilidad total con el indice de precios.
El archivo de precios legado conserva filas futuras vacias que el constructor
excluye por fecha y cobertura.

El grafico conserva las dos curvas sinteticas originales. La azul representa
un indice de retornos mensuales equiponderados entre los componentes con
precio disponible en ambos meses; no es el indicador clasico de numero de
acciones al alza menos numero de acciones a la baja. La amarilla, llamada
"7 Magnificas", usa la interseccion de una lista fija de siete tickers con
la canasta y los precios disponibles: el numero efectivo puede ser menor.
`indices_colombia.csv` distribuyo esos retornos mensuales a fechas diarias
siguiendo la forma del indice empalmado (o linealmente en saltos), por lo
que sus puntos intramensuales son una visualizacion sintetica. Esa tabla
heredada no se sobreescribe en el actualizador diario; la tabla mensual
experimental muestra la cobertura que debe revisarse antes de atribuir
significado a un tramo.
La canasta de "7 Magnificas" es una hipotesis de liderazgo bursatil elegida
en el proyecto, no una medida de contribucion empresarial al PIB del DANE.

## Interpretacion temporal

- El grafico macro conserva puntos mensuales y barras trimestrales en filas
  separadas. No convierte PIB o IPC a datos diarios.
- El grafico TES usa solo fechas publicadas por BanRep. La linea bursatil
  oficial usa fechas publicadas de COLCAP; las tres lineas punteadas son
  reconstrucciones historicas separadas. Una fuente rezagada no recorta otra.
- Las tarjetas muestran la ultima observacion del periodo seleccionado y
  su propia fecha. Las cifras historicas usan la vintage actual; no son una
  base de datos de lo que se sabia exactamente en cada fecha pasada.
