# Auditoria critica de datos - Dashboard ColombiaMacro

Nota de seguimiento (2026-09-24): este documento registra el diagnostico de
la version anterior. La rama `codex/datos-economia-colombiana` sustituyo el
PIB nominal mal etiquetado por PIB real DANE, la serie bursatil empalmada por
COLCAP oficial BanRep para la linea y tarjeta oficiales. Las canastas
reconstruidas permanecen como comparaciones historicas punteadas, con
advertencias visibles de metodologia y cobertura. El estado vigente esta en
`DATA_DICTIONARY.md`.

Fecha de auditoria: 2026-09-24

## Objetivo del dashboard

El dashboard quiere estudiar la economia colombiana combinando mercado accionario, inflacion, PIB y tasas TES. Esa ambicion es buena, pero exige separar con mucha claridad tres cosas:

1. Indicadores macro reales: actividad economica, inflacion, tasas de politica/mercado.
2. Indicadores financieros: TES, bolsa, NAV de ETF, curvas de rendimiento.
3. Indicadores reconstruidos: indices sinteticos calculados localmente con supuestos propios.

Hoy el dashboard mezcla esas tres familias, pero algunas etiquetas hacen parecer que todos los datos son oficiales y directamente comparables. No lo son.

## Fuentes y captura de datos

### Inflacion

Archivo de captura: `actualizar_inflacion.py`

Fuente declarada: Banco de la Republica, API del graficador de series, serie IPC total `ID_IPC = 15000`.

Archivo final: `inflacion_clean.csv`

Columnas:

- `fecha`: primer dia del mes.
- `inflacion_mensual`: variacion porcentual frente al mes anterior.
- `inflacion_anual`: variacion porcentual frente al mismo mes del ano anterior.

Formula usada:

```text
inflacion_mensual_t = (IPC_t / IPC_{t-1} - 1) * 100
inflacion_anual_t   = (IPC_t / IPC_{t-12} - 1) * 100
```

Diagnostico:

- La formula es correcta si el IPC descargado es el indice oficial total.
- La frecuencia mensual esta bien.
- El CSV llega hasta abril de 2026.
- El dashboard asigna el dato mensual a todos los dias de mercado del mismo mes, lo cual sirve para visualizacion, pero no significa que la inflacion sea diaria.

Riesgo:

- El grafico debe dejar claro que la inflacion es mensual, no diaria.
- La zona 2%-4% y la linea 3% se interpretan como meta BanRep, pero la meta formal es puntual 3% con rango de tolerancia. Conviene etiquetarlo como "Meta 3% +-1 pp".

### TES

Archivo de captura: `actualizar_tes.py`

Fuente declarada: Banco de la Republica, API del graficador.

Series usadas:

- `tes_pesos_1y`: TES pesos 1 ano.
- `tes_pesos_5y`: TES pesos 5 anos.
- `tes_pesos_10y`: TES pesos 10 anos.
- `tes_uvr_1y`, `tes_uvr_5y`, `tes_uvr_10y`: descargadas, pero no graficadas en el dashboard principal.

Archivo final: `tasas_interes_clean.csv`

Diagnostico:

- Las tasas en pesos no tienen faltantes en el CSV.
- Las UVR tienen 209 faltantes, pero no afectan el dashboard actual porque no se usan.
- Las tasas son porcentajes anuales extraidos de la curva cero cupon de TES. No son rendimientos observados de un bono individual.

Riesgo:

- El grafico dice "bonos soberanos", correcto en terminos generales, pero tecnicamente debe decir "curva cero cupon TES pesos".
- El spread `10A - 1A` es una senal de pendiente de curva, no una prediccion automatica de recesion.

### PIB

Archivo de captura: `actualizar_pib.py`

Fuente automatica: World Bank, indicador `NY.GDP.MKTP.KD.ZG`.

Fuente manual declarada: DANE.

Archivo final: `pib_colombia.csv`

Columnas:

- `fecha`: inicio del trimestre.
- `pib_billones_cop`: valor del PIB en billones de pesos.
- `trimestre`: etiqueta textual.
- `pib_crecimiento_yoy`: crecimiento interanual.

Hallazgo critico:

El CSV actual no representa crecimiento real del PIB. La columna `pib_crecimiento_yoy` coincide exactamente con:

```text
pib_crecimiento_yoy_t = (pib_billones_cop_t / pib_billones_cop_{t-4} - 1) * 100
```

Eso es variacion interanual del valor en pesos corrientes, no crecimiento real de la economia. Por eso aparecen tasas extremas:

- T2 2021: 61.03%
- T1 2022: 38.70%
- T2 2022: 22.66%
- T2 2020: -29.68%

Estas cifras pueden reflejar efectos nominales, rebotes de base, cambios de precios o valores corrientes, pero no deben presentarse como "crecimiento real del PIB".

Riesgo:

- Este es el problema mas importante del dashboard si el objetivo es estudiar la economia colombiana real.
- La barra verde de PIB en el grafico macro puede inducir a una conclusion falsa sobre crecimiento real.

Recomendacion:

- Reemplazar la serie por PIB real DANE: series encadenadas de volumen, variacion anual de la serie original.
- Si se conserva `pib_billones_cop`, renombrarlo como PIB nominal o PIB corriente.
- Separar dos columnas:
  - `pib_real_yoy`
  - `pib_nominal_yoy`

### Bolsa / ICOLCAP / indices reconstruidos

Archivos:

- `actualizar_icolcap.py`
- `construir_indices.py`
- `datos_colombia_clean.csv`
- `indices_colombia.csv`
- `precios_icolcap_limpios.csv`
- `icolcap_composicion.csv`
- `icolcap_referencia.csv`

Fuente declarada:

- BlackRock iShares COLCAP para NAV historico y composicion.
- Canasta historica ICOLCAP local: `Canasta_Historica_ICAP.xls`.
- Precios mensuales limpios: `precios_icolcap_limpios.csv`.
- Serie de referencia ICOLCAP: `icolcap_referencia.csv`.

#### ICOLCAP general

En `construir_indices.py`, `icolcap_real` viene de `icolcap_referencia.csv` y se extiende con retornos del NAV de BlackRock.

Formula de base 100:

```text
icolcap_base100_t = icolcap_real_t / icolcap_real_0 * 100
```

Riesgo:

- En el dashboard, la tarjeta dice `ICOLCAP` pero usa `close` de `datos_colombia_clean.csv`.
- Ese `close` parece ser NAV/precio del fondo o dato BlackRock, no el nivel oficial del ICOLCAP.
- Por tanto, la tarjeta `ICOLCAP 20,736.05 puntos` es potencialmente incorrecta: no debe llamarse "puntos ICOLCAP" si sale del NAV/precio.

#### Indice diversificado Colombia

Formula mensual:

```text
retorno_accion_i,t = (precio_i,t - precio_i,t-1) / precio_i,t-1
retorno_accion_i,t = clip(retorno_accion_i,t, -100%, +100%)
retorno_sintetico_t = promedio simple de retornos disponibles de la canasta
nivel_sintetico_t = nivel_sintetico_t-1 * (1 + retorno_sintetico_t)
```

Interpretacion:

- Es un indice igual ponderado.
- No replica el ICOLCAP oficial.
- Sirve para responder: "como se habria comportado una canasta equiponderada de las acciones disponibles".

Riesgos:

- Excluir acciones sin dato en un mes puede cambiar la composicion efectiva.
- No usar pesos oficiales impide interpretarlo como mercado total.
- La winsorizacion a +/-100% controla outliers, pero tambien altera retornos extremos reales.
- Convertir un indice mensual a diario usando la forma del ICOLCAP crea una serie diaria visual, no una serie diaria realmente observada.

#### 7 lideres colombianas

Formula:

Igual a la del indice diversificado, pero restringida a:

```text
ECOPETROL, PFBCOLOM, GRUPOSURA, GRUPOARGOS, PFAVAL, ISA, NUTRESA
```

Interpretacion:

- Es un indice tematico reconstruido.
- No es oficial.
- Representa desempeno equiponderado de esas siete acciones cuando hay precios disponibles.

Riesgos:

- La seleccion de "7 lideres" es una decision editorial.
- Puede sobre-representar acciones ganadoras.
- No mide la bolsa colombiana completa.

## Que representa cada grafico

### Grafico "Inflacion Colombia & PIB"

Elementos:

- Barras pequenas naranjas/rojas/verdes: `inflacion_mensual`.
- Linea roja: `inflacion_anual`.
- Area roja suave: relleno visual bajo la inflacion anual.
- Linea gris punteada: meta 3%.
- Banda verde suave entre 2% y 4%: rango de tolerancia visual.
- Barras verdes/rojas grandes: `pib_crecimiento_yoy`.

Critica:

- Mezcla inflacion mensual, inflacion anual y PIB en un solo eje visual.
- El PIB esta en eje secundario sin etiquetas visibles; eso puede hacer que sus barras parezcan comparables directamente con la inflacion.
- La serie de PIB actual no es crecimiento real, por lo que debe corregirse antes de sacar conclusiones macro.

### Grafico "Senales de mercado colombiano"

Elementos:

- Linea naranja: TES pesos 1 ano.
- Linea azul: TES pesos 5 anos.
- Linea morada: TES pesos 10 anos.
- Areas suaves bajo cada linea: relleno visual.

Interpretacion:

- Muestra nivel y pendiente de la curva de tasas soberanas.
- Si corto plazo > largo plazo, la curva se invierte.
- Si largo plazo > corto plazo, la curva es positiva o normal.

Critica:

- El relleno de tres areas puede ensuciar visualmente.
- Falta una linea separada de spread 10A-1A para interpretar pendiente.

### Grafico "Evolucion del ICOLCAP"

Elementos:

- Linea verde: `icolcap_base100`.
- Linea azul: `sintetico_base100`.
- Linea amarilla: `grandes_base100`.
- Linea horizontal base 100: referencia inicial.

Interpretacion:

- Compara tres trayectorias normalizadas a una base comun.
- La linea verde es la aproximacion al ICOLCAP general.
- La azul y amarilla son reconstrucciones propias.

Critica:

- El usuario puede creer que las tres lineas son oficiales. Solo la verde se aproxima al mercado oficial; azul y amarilla son indices internos.
- La linea amarilla domina mucho la narrativa. Debe explicarse como seleccion tematica, no como economia colombiana completa.

### Curva de rendimientos TES

Elementos:

- Tres puntos: TES 1A, 5A y 10A para la fecha activa.
- Linea que conecta los puntos: forma de la curva en esa fecha.
- Tarjetas: tasas, spread, ICOLCAP/NAV, inflacion, PIB.

Critica:

- La curva con solo tres puntos es util pero simplificada.
- El spread 10A-1A esta bien calculado.
- La tarjeta ICOLCAP debe corregirse para usar `icolcap_base100` o `icolcap_real`, no `close` si `close` es NAV/precio.

## Hallazgos de calidad de datos

### 1. PIB mal rotulado para economia real

Severidad: alta.

El dashboard muestra el PIB como crecimiento economico, pero el CSV actual contiene variacion interanual del PIB en pesos corrientes. Debe reemplazarse por crecimiento real DANE.

### 2. `precios_icolcap_limpios.csv` contiene fechas futuras

Severidad: alta.

El archivo tiene filas hasta `2026-12-01`, aunque los datos de mercado llegan hasta mayo de 2026. Las filas futuras estan vacias para la composicion vigente, pero pueden afectar calculos si no se filtran.

Recomendacion:

```text
Eliminar o ignorar meses posteriores al ultimo mes con datos observados reales.
```

### 3. Columnas completamente vacias en precios de acciones

Severidad: media-alta.

Columnas con 0 datos:

```text
BCOLOMBIA, BNA, CHOCOLATES, CLH, CNEC, COLINVERS, INVERARGOS, EEB,
PMGC, PFDAVIGRP, PFAVTA, SURAMINV, PFBCREDITO
```

Esto no rompe el indice porque se excluyen al no tener datos, pero ensucia el modelo y puede ocultar problemas de alias.

### 4. Alias historicos pueden estar distorsionando continuidad

Severidad: media.

Ejemplos:

- `BCOLOMBIA -> PFBCOLOM`
- `SURAMINV -> GRUPOSURA`
- `INVERARGOS -> GRUPOARGOS`
- `CHOCOLATES -> NUTRESA`
- `EEB -> GEB`

Algunos proxies son razonables para continuidad, pero deben documentarse porque no son identicos.

### 5. Indices sinteticos son mensuales, aunque se dibujan diario

Severidad: media-alta.

El indice sintetico y el de 7 lideres se calculan con retornos mensuales y luego se distribuyen a diario con la forma del ICOLCAP. Eso mejora la visualizacion, pero no crea datos diarios reales de esas canastas.

### 6. Merge principal descarta dias sin TES

Severidad: media.

El dashboard parte de `datos_colombia_clean.csv` y luego elimina filas donde falta `tes_pesos_1y`. Se pierden 123 fechas del precio/NAV por no existir TES. Esto hace que la fecha final del dashboard sea `2026-05-22`, aunque `datos_colombia_clean.csv` llega a `2026-05-29`.

### 7. El dashboard combina frecuencias distintas sin suficiente advertencia

Severidad: media.

Frecuencias:

- Bolsa/NAV/TES: diaria de mercado.
- Inflacion: mensual.
- PIB: trimestral.
- Indices sinteticos: calculo mensual distribuido a diario.

Recomendacion:

Mostrar etiquetas de frecuencia o separar vistas macro y mercado.

## Prioridad de correccion

### Prioridad 1: PIB

Crear una tabla limpia con:

```text
fecha
trimestre
pib_real_yoy
pib_real_qoq_sa
pib_nominal_billones_cop
pib_nominal_yoy
fuente
estado_dato
```

Para economia real, graficar `pib_real_yoy`, no `pib_nominal_yoy`.

### Prioridad 2: Bolsa

Separar:

```text
icolcap_oficial_base100
icolcap_nav_extension_base100
indice_equiponderado_base100
indice_7_lideres_base100
```

Y corregir tarjeta:

- Si se muestra `close`, llamarlo `NAV/Precio ETF`.
- Si se quiere mostrar ICOLCAP, usar `icolcap_real` o `icolcap_base100`.

### Prioridad 3: Diccionario de datos

Crear `data_dictionary.csv` o `DATA_DICTIONARY.md` con:

```text
columna
archivo
descripcion
formula
frecuencia
unidad
fuente
oficial/reconstruida
limitaciones
```

### Prioridad 4: Validacion automatica

Crear un script `validar_datos.py` que revise:

- Fechas futuras.
- Duplicados.
- Huecos inesperados.
- Columnas 100% vacias.
- Outliers de retornos.
- Series nominales etiquetadas como reales.
- Ultima fecha por fuente.
- Perdida de filas por merges.

### Prioridad 5: Redisenar narrativa

Separar el dashboard en tres capas:

1. Macro real: PIB real, inflacion, desempleo si se agrega, tasa BanRep si se agrega.
2. Mercado de tasas: TES 1A/5A/10A, spread, UVR si se activa.
3. Mercado accionario: ICOLCAP oficial/NAV, indice equiponderado, 7 lideres.

## Conclusion critica

El dashboard es una buena base visual, pero todavia no esta listo para estudiar la economia colombiana real sin advertencias. La parte de inflacion y TES es razonablemente solida. La parte de bolsa es util si se presenta como reconstruccion financiera con supuestos. La parte de PIB debe corregirse antes de usarla como indicador real de actividad economica.

La prioridad tecnica y conceptual es sanear PIB y etiquetar correctamente las series oficiales versus reconstruidas.
