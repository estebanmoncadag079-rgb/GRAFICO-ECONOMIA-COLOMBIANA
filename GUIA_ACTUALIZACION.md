# Guía de Actualización — Dashboard Financiero Colombia

## Actualización automática

Todos los datos se actualizan solos **cada lunes a las 7:00 AM** (Task Scheduler).
No se requiere ninguna acción.

Para forzar una actualización manual en cualquier momento:
```
python actualizar_todo.py
```

---

## Lo único verdaderamente manual

### PIB Colombia — datos exactos de DANE (opcional, trimestral)

El PIB se actualiza automáticamente desde World Bank (aproximado).
Si quieres los datos exactos de DANE:

1. Entra a **dane.gov.co** → Estadísticas → Cuentas Nacionales Trimestrales
2. Busca el PIB a precios corrientes (billones COP) y el crecimiento YoY (%)
3. Corre:
```
python actualizar_pib.py --trimestre "T2 2026" --valor 408.3 --crecimiento 3.84
```

---

## Ver el dashboard

```
python dashboard_colombia.py
```

Abre: **http://127.0.0.1:8050** — para cerrar: `Ctrl+C`
