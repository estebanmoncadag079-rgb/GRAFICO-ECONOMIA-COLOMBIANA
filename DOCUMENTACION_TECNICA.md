# Documentacion tecnica

## Flujo de datos

`actualizar_todo.py` ejecuta cinco procesos independientes:

1. `actualizar_inflacion.py`: IPC BanRep y tasas publicadas DANE.
2. `actualizar_tes.py`: curvas cero cupon TES BanRep.
3. `actualizar_pib.py`: anexos de PIB real y nominal DANE.
4. `actualizar_colcap.py`: indice COLCAP diario BanRep/BVC.
5. `construir_tablas_experimentales.py`: auditoria mensual de canastas locales.

`validar_datos.py` comprueba estructura, fechas, formulas y valores
anomalos. Escribe `estado_fuentes.csv` y `alertas_datos.csv` despues de
validar. La aplicacion Dash lee las tablas al arrancar; Render debe
desplegar de nuevo cuando el workflow sube un commit de datos.

## Contratos

- Cada archivo conserva la frecuencia de su fuente; no se copian valores
  de PIB o IPC a filas diarias.
- `fecha` es la observacion medida. `fecha_publicacion_vintage` identifica
  la version actual de una publicacion, no un archivo historico de revisiones.
- El dashboard usa `pib_real_yoy` para actividad economica real y
  `pib_nominal_billones_cop` solo como magnitud nominal.
- COLCAP se obtiene exclusivamente de la serie 6 de BanRep/BVC.
  `datos_colombia_clean.csv`, `icolcap_referencia.csv` e
  `indices_colombia.csv` son legados y no alimentan la serie oficial.
- Las canastas equiponderadas son experimentales y solo mensuales. Una
  observacion con cobertura insuficiente o precios atipicos no publica
  retorno.
- Los picos TES aislados se conservan en el CSV y se enumeran en
  `alertas_datos.csv`. Solo el trazo del grafico omite esos puntos.

Las columnas, unidades, formulas, fuentes y limites se detallan en
[DATA_DICTIONARY.md](DATA_DICTIONARY.md). Para horario y despliegue, ver
[OPERACION_DATOS.md](OPERACION_DATOS.md). La auditoria que motivo los
cambios esta en [AUDITORIA_CRITICA_DATOS_DASHBOARD.md](AUDITORIA_CRITICA_DATOS_DASHBOARD.md).

## Verificacion

```bash
python -m pip install -r requirements-update.txt
python actualizar_todo.py
python validar_datos.py
python dashboard_colombia.py
```

El dashboard necesita `colcap_oficial.csv`, `tasas_interes_clean.csv`,
`inflacion_clean.csv`, `pib_colombia.csv` y `estado_fuentes.csv`.
Los CSV deben versionarse juntos para que Render arranque con datos
coherentes.
