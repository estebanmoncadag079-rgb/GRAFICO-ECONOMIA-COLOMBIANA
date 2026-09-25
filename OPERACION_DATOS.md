# Operacion diaria y despliegue

1. En local: `python -m pip install -r requirements-update.txt`.
2. Ejecutar `python actualizar_todo.py`.
3. Comprobar `python validar_datos.py`.
4. Abrir el dashboard con `python dashboard_colombia.py` o Render.

El workflow `.github/workflows/actualizar-datos.yml` consulta las fuentes
todos los dias a las 19:30 hora de Colombia (00:30 UTC), valida las tablas,
y solo hace commit cuando hay cambios. Si una fuente falla, el workflow
marca el run como fallido despues de preservar las actualizaciones de otras
fuentes que pasaron validacion. GitHub Actions ejecuta `schedule` **solo en
la rama predeterminada**. En esta rama de trabajo puede probarse con
`workflow_dispatch`; tras revisar y fusionar a `main`, empezara el
cron diario.

Para desplegar en Render, conectar el servicio web de `render.yaml` con
`main` y habilitar el despliegue automatico al recibir commits. El servicio
Render solo sirve archivos CSV versionados; no actualiza datos por si mismo.
El workflow necesita permiso `contents: write` (definido en YAML y permitido
en la configuracion Actions del repositorio). Render debe reconstruir o
reiniciar al llegar un commit de datos para cargar los CSV nuevos.

La calidad se revisa con `validar_datos.py`: fechas futuras, duplicados,
periodicidad PIB/IPC, formulas, rangos de TES, saltos COLCAP y retornos
experimentales sin cobertura. `estado_fuentes.csv` expone el ultimo periodo
y fecha de publicacion o corte de cada fuente. Un estado `rezagado` indica
que el archivo no se ha actualizado dentro del umbral de vigilancia; no
autoriza inventar o propagar datos.

La serie oficial COLCAP, el IPC, PIB y TES se descargan sin claves y no
requieren archivos manuales del usuario. Para convertir las canastas
experimentales en indicadores de investigacion fiables se necesita una
fuente de precios historicos por accion ajustados por splits, dividendos y
otros eventos corporativos, junto con canastas historicas fechadas y pesos
de cada periodo. Estos insumos pueden tener restricciones de licencia;
deben identificarse antes de automatizar esa parte.
