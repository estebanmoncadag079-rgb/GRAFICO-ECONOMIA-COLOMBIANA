"""
actualizar_pib.py
Actualiza pib_colombia.csv con dos metodos:

  1. AUTOMATICO (World Bank API)
     - Datos anuales hasta ~2 anhos atras
     - Distribuye el valor anual a los 4 trimestres

  2. MANUAL (DANE oficial)
     - Cuando DANE publica un nuevo trimestre (cada ~3 meses)
     - Corres: python actualizar_pib.py --trimestre "T2 2026" --valor 408.3 --crecimiento 3.84
     - Los valores los consigues en dane.gov.co -> Cuentas Nacionales Trimestrales

DANE publica nuevos datos aproximadamente:
  T1 (ene-mar) -> disponible en mayo/junio
  T2 (abr-jun) -> disponible en agosto/septiembre
  T3 (jul-sep) -> disponible en noviembre/diciembre
  T4 (oct-dic) -> disponible en febrero/marzo del anho siguiente
"""

import os, sys, argparse, requests
import pandas as pd

BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
CSV_PIB    = os.path.join(BASE_DIR, "pib_colombia.csv")

# Meses de inicio por trimestre
TRIMESTRE_MES = {"T1": 1, "T2": 4, "T3": 7, "T4": 10}


# ── 1. ACTUALIZACION AUTOMATICA — World Bank ──────────────────

def obtener_pib_worldbank() -> pd.DataFrame:
    """
    Descarga crecimiento PIB anual de Colombia desde World Bank API.
    Retorna DataFrame con columnas: anho, pib_crecimiento_anual
    """
    url = "https://api.worldbank.org/v2/country/COL/indicator/NY.GDP.MKTP.KD.ZG"
    params = {"format": "json", "per_page": 100, "mrv": 60}

    print("Descargando datos World Bank...")
    try:
        r = requests.get(url, params=params, timeout=15)
        r.raise_for_status()
        data = r.json()
        entries = data[1]

        filas = []
        for e in entries:
            if e["value"] is not None:
                filas.append({"anho": int(e["date"]), "crecimiento": round(float(e["value"]), 6)})

        df = pd.DataFrame(filas).sort_values("anho").reset_index(drop=True)
        print(f"OK - World Bank: {len(df)} anhos ({df['anho'].min()}-{df['anho'].max()})")
        return df

    except Exception as e:
        print(f"ERROR World Bank: {e}")
        return pd.DataFrame()


def actualizar_desde_worldbank():
    """
    Compara el CSV existente con los datos de World Bank
    y agrega los anhos que falten (como 4 filas trimestrales cada uno).
    """
    df_wb  = obtener_pib_worldbank()
    if df_wb.empty:
        return

    df_pib = pd.read_csv(CSV_PIB, parse_dates=["fecha"])

    # Solo considerar años desde 2009 (rango del dashboard)
    anhos_existentes = set(df_pib["fecha"].dt.year.unique())
    anhos_wb         = set(df_wb[df_wb["anho"] >= 2009]["anho"].tolist())
    anhos_nuevos     = sorted(anhos_wb - anhos_existentes)

    if not anhos_nuevos:
        print("Sin datos nuevos en World Bank para agregar.")
        return

    print(f"Anhos nuevos a agregar: {anhos_nuevos}")
    filas_nuevas = []

    for anho in anhos_nuevos:
        crecimiento = df_wb[df_wb["anho"] == anho]["crecimiento"].iloc[0]

        # Estimar pib_billones_cop extrapolando desde el ultimo valor conocido
        ultimo = df_pib.dropna(subset=["pib_billones_cop"]).iloc[-1]
        pib_base = float(ultimo["pib_billones_cop"])
        factor   = 1 + crecimiento / 100

        for trim, mes in TRIMESTRE_MES.items():
            pib_estimado = round(pib_base * (factor ** 0.25), 1)
            filas_nuevas.append({
                "fecha":               f"{anho}-{mes:02d}-01",
                "pib_billones_cop":    pib_estimado,
                "trimestre":           f"{trim} {anho}",
                "pib_crecimiento_yoy": crecimiento,
            })
            pib_base = pib_estimado

    df_nuevos = pd.DataFrame(filas_nuevas)
    df_nuevos["fecha"] = pd.to_datetime(df_nuevos["fecha"])

    df_total = (pd.concat([df_pib, df_nuevos])
                  .drop_duplicates("fecha")
                  .sort_values("fecha")
                  .reset_index(drop=True))

    df_total.to_csv(CSV_PIB, index=False)
    print(f"OK - CSV actualizado: {len(df_total)} filas -> {CSV_PIB}")
    print(f"     NOTA: valores World Bank son anuales distribuidos en 4 trimestres (aproximacion).")
    print(f"     Para datos exactos usa --trimestre con cifras de DANE.")


# ── 2. ACTUALIZACION MANUAL — DANE ───────────────────────────

def agregar_trimestre_dane(trimestre: str, valor_cop: float, crecimiento: float):
    """
    Agrega un trimestre nuevo con datos exactos de DANE.
    Ejemplo: agregar_trimestre_dane("T2 2026", 408.3, 3.84)

    Como obtener los valores:
      1. Ir a dane.gov.co -> Estadisticas -> Cuentas Nacionales Trimestrales
      2. Descargar el ultimo boletin (Excel o PDF)
      3. Buscar el PIB a precios corrientes (billones COP) y el crecimiento YoY
    """
    try:
        partes = trimestre.strip().split()
        if len(partes) != 2 or partes[0] not in TRIMESTRE_MES:
            print(f"ERROR: Formato incorrecto. Usa 'T1 2026', 'T2 2026', etc.")
            return

        trim_cod = partes[0]
        anho     = int(partes[1])
        mes      = TRIMESTRE_MES[trim_cod]
        fecha    = pd.Timestamp(f"{anho}-{mes:02d}-01")

        df_pib = pd.read_csv(CSV_PIB, parse_dates=["fecha"])

        if fecha in df_pib["fecha"].values:
            # Actualizar fila existente con datos DANE (mas precisos)
            idx = df_pib[df_pib["fecha"] == fecha].index[0]
            df_pib.loc[idx, "pib_billones_cop"]    = valor_cop
            df_pib.loc[idx, "pib_crecimiento_yoy"] = crecimiento
            df_pib.loc[idx, "trimestre"]            = trimestre
            print(f"Fila existente actualizada con datos DANE: {trimestre}")
        else:
            # Agregar fila nueva
            nueva = pd.DataFrame([{
                "fecha":               fecha,
                "pib_billones_cop":    valor_cop,
                "trimestre":           trimestre,
                "pib_crecimiento_yoy": crecimiento,
            }])
            df_pib = (pd.concat([df_pib, nueva])
                        .sort_values("fecha")
                        .reset_index(drop=True))
            print(f"Trimestre nuevo agregado: {trimestre}")

        df_pib.to_csv(CSV_PIB, index=False)
        print(f"OK - Guardado en {CSV_PIB}")
        print(f"     {trimestre}: PIB={valor_cop} billones COP | Crecimiento={crecimiento}% YoY")

    except Exception as e:
        print(f"ERROR: {e}")


# ── 3. MOSTRAR ESTADO ACTUAL ──────────────────────────────────

def mostrar_estado():
    df = pd.read_csv(CSV_PIB, parse_dates=["fecha"])
    print("\n" + "="*55)
    print("  Estado actual del PIB Colombia")
    print("="*55)
    print(f"  Total filas    : {len(df)}")
    print(f"  Primer dato    : {df['trimestre'].iloc[0]}")
    print(f"  Ultimo dato    : {df['trimestre'].iloc[-1]}")
    print(f"  Ultimo PIB     : {df['pib_billones_cop'].iloc[-1]:.1f} billones COP")
    print(f"  Ultimo crec.   : {df['pib_crecimiento_yoy'].iloc[-1]:.2f}% YoY")
    print("="*55)
    print("\nUltimos 6 trimestres:")
    print(df[["trimestre","pib_billones_cop","pib_crecimiento_yoy"]].tail(6).to_string(index=False))


# ── Main ─────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Actualiza pib_colombia.csv",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="""
Ejemplos:
  Actualizacion automatica (World Bank):
    python actualizar_pib.py

  Agregar trimestre con datos exactos de DANE:
    python actualizar_pib.py --trimestre "T2 2026" --valor 408.3 --crecimiento 3.84

  Ver estado actual:
    python actualizar_pib.py --estado
        """
    )
    parser.add_argument("--trimestre",   type=str,   help="Ej: 'T2 2026'")
    parser.add_argument("--valor",       type=float, help="PIB en billones COP (de DANE)")
    parser.add_argument("--crecimiento", type=float, help="Crecimiento YoY en %% (de DANE)")
    parser.add_argument("--estado",      action="store_true", help="Mostrar resumen actual")
    args = parser.parse_args()

    print("\n" + "="*55)
    print("  Actualizador PIB Colombia")
    print("="*55)

    if args.estado:
        mostrar_estado()

    elif args.trimestre:
        if args.valor is None or args.crecimiento is None:
            print("ERROR: Con --trimestre debes proveer tambien --valor y --crecimiento")
            print("Ejemplo: python actualizar_pib.py --trimestre 'T2 2026' --valor 408.3 --crecimiento 3.84")
            sys.exit(1)
        agregar_trimestre_dane(args.trimestre, args.valor, args.crecimiento)
        mostrar_estado()

    else:
        # Modo por defecto: actualizacion automatica con World Bank
        actualizar_desde_worldbank()
        mostrar_estado()

    print()
