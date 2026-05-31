"""
actualizar_icolcap.py
Descarga automaticamente desde BlackRock usando Playwright (Chrome real):
  - Precios NAV historicos  -> datos_colombia_clean.csv
  - Composicion de canasta  -> icolcap_composicion.csv

Uso:
  python actualizar_icolcap.py                        # Playwright (automatico)
  python actualizar_icolcap.py --reconstruir          # + reconstruye indices
  python actualizar_icolcap.py --composicion ruta.xls # PCF manual descargado
"""

import os, re, sys, argparse, subprocess, datetime
import pandas as pd

BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
CSV_SALIDA = os.path.join(BASE_DIR, "datos_colombia_clean.csv")
CSV_COMPO  = os.path.join(BASE_DIR, "icolcap_composicion.csv")
PCF_TEMP   = os.path.join(BASE_DIR, "_pcf_temp.xls")

BLACKROCK_URL = (
    "https://www.blackrock.com/co/productos/251708/"
    "ishares-fondo-burstil-ishares-colcap-fund"
)
AJAX_NAV_URL = BLACKROCK_URL + "/1497267045722.ajax?tab=chart"

GRANDES = {"ECOPETROL", "PFBCOLOM", "GRUPOSURA", "GRUPOARGOS",
           "PFAVAL", "ISA", "NUTRESA"}


# ══════════════════════════════════════════════════════════
# PLAYWRIGHT — descarga automatica
# ══════════════════════════════════════════════════════════

def descargar_con_playwright():
    """
    Abre Chrome, navega a BlackRock y captura:
      - HTML con precios NAV historicos
      - Archivo PCF de composicion de cartera
    Retorna (html_nav: str|None, ruta_pcf: str|None)
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("ERROR: Playwright no instalado.")
        print("       Corre: pip install playwright && python -m playwright install chrome")
        return None, None

    html_nav  = None
    ruta_pcf  = None

    print("Abriendo Chrome...")
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            channel="chrome",
        )
        context = browser.new_context(
            accept_downloads=True,
            locale="es-CO",
        )
        page = context.new_page()

        # Interceptar la respuesta AJAX del chart de NAV
        nav_responses = []
        page.on("response", lambda r: nav_responses.append(r)
                if "1497267045722.ajax" in r.url and "tab=chart" in r.url else None)

        print("Navegando a BlackRock (puede tardar unos segundos)...")
        try:
            page.goto(BLACKROCK_URL, wait_until="networkidle", timeout=60000)
        except Exception:
            page.wait_for_timeout(15000)

        # Obtener NAV desde respuesta interceptada
        if nav_responses:
            try:
                html_nav = nav_responses[0].text()
                print(f"   NAV capturado ({len(html_nav)//1024} KB)")
            except Exception as e:
                print(f"   Error leyendo NAV: {e}")

        # Si no se capturó, hacer request directo con las cookies del browser
        if not html_nav:
            print("   Haciendo request directo al endpoint NAV...")
            try:
                resp = page.request.get(AJAX_NAV_URL)
                if resp.ok:
                    html_nav = resp.text()
                    print(f"   NAV descargado ({len(html_nav)//1024} KB)")
                else:
                    print(f"   Error HTTP {resp.status} en endpoint NAV")
            except Exception as e:
                print(f"   Error en request directo: {e}")

        # Descargar PCF (composicion de cartera) via request directo con cookies del browser
        print("   Descargando composicion de cartera...")
        try:
            href = page.locator("a.icon-xls").first.get_attribute("href", timeout=10000)
            pcf_url = f"https://www.blackrock.com{href}"
            resp = page.request.get(pcf_url)
            if resp.ok:
                with open(PCF_TEMP, "wb") as f:
                    f.write(resp.body())
                ruta_pcf = PCF_TEMP
                print(f"   PCF descargado ({len(resp.body())//1024} KB)")
            else:
                print(f"   Error HTTP {resp.status} al descargar PCF")
        except Exception as e:
            print(f"   No se pudo descargar PCF: {e}")

        browser.close()

    return html_nav, ruta_pcf


# ══════════════════════════════════════════════════════════
# PROCESAR NAV
# ══════════════════════════════════════════════════════════

def extraer_precios_nav(html: str) -> pd.DataFrame | None:
    idx = html.find('id="subTabNav"')
    if idx == -1:
        print("ERROR: Seccion 'subTabNav' no encontrada en el HTML.")
        return None

    patron = r'Date\.UTC\((\d+),(\d+),(\d+)\),y:Number\(\(([0-9.]+)\)'
    puntos = re.findall(patron, html[idx:])

    if not puntos:
        print("ERROR: No se encontraron datos de precios en el HTML.")
        return None

    filas = []
    for year, mes0, dia, valor in puntos:
        fecha = datetime.date(int(year), int(mes0) + 1, int(dia))
        filas.append({"fecha": fecha, "close": float(valor)})

    df = (pd.DataFrame(filas)
            .assign(fecha=lambda d: pd.to_datetime(d["fecha"]))
            .sort_values("fecha").reset_index(drop=True))

    print(f"   Precios extraidos: {len(df)} filas")
    print(f"   Periodo: {df['fecha'].min().date()} -> {df['fecha'].max().date()}")
    print(f"   Ultimo precio: {df['close'].iloc[-1]:,.2f} COP")
    return df[["fecha", "close"]]


def actualizar_csv(df_nuevo: pd.DataFrame):
    if os.path.exists(CSV_SALIDA):
        df_exist = pd.read_csv(CSV_SALIDA, parse_dates=["fecha"])
        fecha_inicio = df_nuevo["fecha"].min()
        df_hist  = df_exist[df_exist["fecha"] < fecha_inicio][["fecha", "close"]]
        df_total = (pd.concat([df_hist, df_nuevo])
                      .drop_duplicates("fecha")
                      .sort_values("fecha")
                      .reset_index(drop=True))
        print(f"   Historico conservado: {len(df_hist)} filas")
        print(f"   BlackRock: {len(df_nuevo)} filas")
    else:
        df_total = df_nuevo

    df_total["sma20"] = df_total["close"].rolling(20).mean()
    df_total["sma50"] = df_total["close"].rolling(50).mean()
    df_total.to_csv(CSV_SALIDA, index=False)
    print(f"OK - {len(df_total)} filas -> {CSV_SALIDA}")


# ══════════════════════════════════════════════════════════
# PROCESAR COMPOSICION (PCF)
# ══════════════════════════════════════════════════════════

def actualizar_composicion(ruta_excel: str) -> bool:
    print(f"Leyendo composicion: {ruta_excel}")
    xls = pd.read_excel(ruta_excel, header=None, dtype=str)

    fila_header = None
    for i, row in xls.iterrows():
        vals = [str(v).strip() for v in row]
        if any("Emisora" in v for v in vals) and any("Nemot" in v for v in vals):
            fila_header = i
            break

    if fila_header is None:
        print("ERROR: No se encontro la fila de encabezados en el Excel.")
        return False

    headers    = [str(v).strip() for v in xls.iloc[fila_header]]
    col_emisora = next((i for i, h in enumerate(headers) if "Emisora" in h), None)
    col_ticker  = next((i for i, h in enumerate(headers) if "Nemot"   in h), None)

    if col_ticker is None:
        print("ERROR: No se encontro la columna 'Nemotecnico'.")
        return False

    tickers_nuevos, nombres_nuevos = [], []
    for i in range(fila_header + 1, len(xls)):
        fila   = xls.iloc[i]
        celda0 = str(fila.iloc[0]).strip()
        if "Activos" in celda0 and "xcluidos" in celda0:
            break
        ticker = str(fila.iloc[col_ticker]).strip()
        nombre = str(fila.iloc[col_emisora]).strip() if col_emisora is not None else ""
        if ticker and ticker != "nan":
            tickers_nuevos.append(ticker.upper())
            nombres_nuevos.append(nombre)

    if not tickers_nuevos:
        print("ERROR: No se encontraron tickers.")
        return False

    print(f"   Tickers encontrados ({len(tickers_nuevos)}): {', '.join(tickers_nuevos)}")

    df_exist = pd.read_csv(CSV_COMPO) if os.path.exists(CSV_COMPO) else pd.DataFrame()
    grandes_existentes = (set(df_exist[df_exist["es_grande"] == True]["ticker"].tolist())
                          if not df_exist.empty else GRANDES)

    n = len(tickers_nuevos)
    filas = [{"ticker": t, "nombre": nom,
               "peso_icolcap": 0.0,
               "es_grande": t in grandes_existentes or t in GRANDES,
               "peso_sintetico": round(100 / n, 4)}
             for t, nom in zip(tickers_nuevos, nombres_nuevos)]

    tickers_antes = set(df_exist["ticker"].tolist()) if not df_exist.empty else set()
    agregados  = set(tickers_nuevos) - tickers_antes
    eliminados = tickers_antes - set(tickers_nuevos)
    if agregados:  print(f"   + Agregados : {', '.join(sorted(agregados))}")
    if eliminados: print(f"   - Eliminados: {', '.join(sorted(eliminados))}")
    if not agregados and not eliminados: print("   Sin cambios en la canasta.")

    pd.DataFrame(filas).to_csv(CSV_COMPO, index=False)
    print(f"OK - icolcap_composicion.csv actualizado ({n} empresas)")
    return True


# ══════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Actualiza datos ICOLCAP desde BlackRock (Playwright)",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="""
Ejemplos:
  Automatico (Playwright):
    python actualizar_icolcap.py
    python actualizar_icolcap.py --reconstruir

  PCF descargado manualmente:
    python actualizar_icolcap.py --composicion "C:/Users/USUARIO/Downloads/pcf-icolcap-es_co.xls"
        """
    )
    parser.add_argument("--composicion", type=str,
                        help="Ruta al Excel PCF descargado manualmente de BlackRock")
    parser.add_argument("--reconstruir", action="store_true",
                        help="Reconstruir indices_colombia.csv al finalizar")
    args = parser.parse_args()

    sep = "=" * 55

    # ── Modo PCF manual ───────────────────────────────────
    if args.composicion:
        print(f"\n{sep}\n  Actualizador Composicion ICOLCAP\n{sep}")
        ok = actualizar_composicion(args.composicion)
        if ok and args.reconstruir:
            print("\nReconstruyendo indices...")
            subprocess.run([sys.executable,
                            os.path.join(BASE_DIR, "construir_indices.py")], check=True)
        print(f"{sep}\n")
        sys.exit(0)

    # ── Modo Playwright (por defecto) ─────────────────────
    print(f"\n{sep}\n  Actualizador ICOLCAP — BlackRock (Playwright)\n{sep}")

    html_nav, ruta_pcf = descargar_con_playwright()

    nav_ok  = False
    comp_ok = False

    if html_nav:
        print(f"\n{sep}\n  Procesando NAV\n{sep}")
        df = extraer_precios_nav(html_nav)
        if df is not None:
            actualizar_csv(df)
            nav_ok = True
    else:
        print("AVISO: No se obtuvieron datos NAV.")

    if ruta_pcf and os.path.exists(ruta_pcf):
        print(f"\n{sep}\n  Procesando Composicion\n{sep}")
        comp_ok = actualizar_composicion(ruta_pcf)
        try:
            os.remove(ruta_pcf)
        except Exception:
            pass
    else:
        print("AVISO: No se descargo el archivo de composicion.")

    if args.reconstruir and (nav_ok or comp_ok):
        print(f"\n{sep}\n  Reconstruyendo indices\n{sep}")
        subprocess.run([sys.executable,
                        os.path.join(BASE_DIR, "construir_indices.py")], check=True)

    print(f"\n{sep}")
    print(f"  NAV actualizado  : {'SI' if nav_ok  else 'NO'}")
    print(f"  Canasta actualizada: {'SI' if comp_ok else 'NO'}")
    print(f"{sep}\n")
