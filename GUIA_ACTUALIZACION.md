# Guia de actualizacion

La actualizacion de las cuatro fuentes oficiales se ejecuta diariamente
en GitHub Actions a las 19:30 hora de Colombia una vez que el workflow
este fusionado en `main`. El servicio de Render carga los CSV del commit
desplegado.

Para ejecutarla en este equipo:

```bash
python -m pip install -r requirements-update.txt
python actualizar_todo.py
python validar_datos.py
```

Para revisar el dashboard: `python dashboard_colombia.py` y abrir
`http://127.0.0.1:8050`.

El PIB real se descarga automaticamente de los anexos DANE; no hay que
repartir valores anuales ni ingresar crecimientos manualmente. La fuente
oficial COLCAP tampoco requiere descarga manual. La tabla de canastas
accionarias sigue siendo experimental y necesita precios historicos
ajustados y pesos fechados para poder validarse.

Ver [OPERACION_DATOS.md](OPERACION_DATOS.md) para configurar GitHub y
Render, y [DATA_DICTIONARY.md](DATA_DICTIONARY.md) para interpretar las
cifras.
