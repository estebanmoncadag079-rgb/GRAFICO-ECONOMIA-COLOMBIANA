"""
actualizar_todo.py
Actualiza todos los datos del dashboard en secuencia y reconstruye los indices.

Uso:
  python actualizar_todo.py               # Actualiza todo
  python actualizar_todo.py --programar   # Programa ejecucion diaria local
"""

import os, sys, subprocess, datetime, argparse

# Carpeta base del proyecto. Se usa para ejecutar los demas scripts con rutas
# absolutas, aunque el usuario lance este comando desde otra ubicacion.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Orden oficial de actualizacion. Cada entrada define el nombre mostrado en
# consola, el script que se ejecuta y sus argumentos adicionales.
PASOS = [
    ("Inflacion — DANE/BanRep", "actualizar_inflacion.py", []),
    ("TES Pesos — BanRep", "actualizar_tes.py", []),
    ("PIB real y nominal — DANE", "actualizar_pib.py", []),
    ("COLCAP oficial — BanRep/BVC", "actualizar_colcap.py", []),
    ("Canastas mensuales experimentales", "construir_tablas_experimentales.py", []),
]


def correr(nombre, script, args_extra=None):
    """Ejecuta un actualizador individual y devuelve True si finaliza sin error."""
    ruta = os.path.join(BASE_DIR, script)
    cmd  = [sys.executable, ruta] + (args_extra or [])
    print(f"\n{'='*55}\n  {nombre}\n{'='*55}")
    try:
        # Timeout defensivo para que una fuente externa lenta no bloquee todo
        # el proceso de actualizacion.
        result = subprocess.run(cmd, timeout=180)
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        print(f"ERROR: tiempo limite superado (180s)")
        return False
    except Exception as e:
        print(f"ERROR: {e}")
        return False


def programar_tarea():
    """Crea tarea diaria local; GitHub Actions es la opcion del servidor."""
    python = sys.executable
    script = os.path.abspath(__file__)
    nombre_tarea = "Dashboard Colombia - Actualizacion diaria"

    cmd = (
        f'schtasks /create '
        f'/tn "{nombre_tarea}" '
        f'/tr "{python} {script}" '
        f'/sc DAILY /st 19:00 '
        f'/f'
    )
    print(f"Creando tarea en Task Scheduler...")
    ret = os.system(cmd)
    if ret == 0:
        print(f"OK - Tarea creada: todos los dias a las 19:00")
        print(f"     Nombre: {nombre_tarea}")
        print(f"     Para verla: Inicio -> Task Scheduler -> Task Scheduler Library")
        print(f"     Para eliminarla: schtasks /delete /tn \"{nombre_tarea}\" /f")
    else:
        print("ERROR: No se pudo crear la tarea.")
        print("       Intenta correr este script como Administrador.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Actualiza todos los datos del Dashboard Colombia",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument("--programar", action="store_true",
                        help="Crear tarea diaria automatica en Windows Task Scheduler")
    args = parser.parse_args()

    if args.programar:
        programar_tarea()
        sys.exit(0)

    inicio = datetime.datetime.now()
    print(f"\n{'='*55}")
    print(f"  Dashboard Colombia — Actualizacion completa")
    print(f"  {inicio.strftime('%d/%m/%Y %H:%M')}")
    print(f"{'='*55}")

    # Guardamos el estado de cada paso para reportar un resumen consolidado.
    resultados = []
    for nombre, script, extras in PASOS:
        ok = correr(nombre, script, extras)
        resultados.append((nombre, ok))

    fin      = datetime.datetime.now()
    duracion = int((fin - inicio).total_seconds())

    print(f"\n{'='*55}")
    print(f"  RESUMEN — {fin.strftime('%H:%M:%S')}")
    print(f"{'='*55}")
    for nombre, ok in resultados:
        marca = "OK  " if ok else "FALLO"
        print(f"  [{marca}] {nombre}")
    print(f"\n  Tiempo total: {duracion}s")
    print(f"{'='*55}\n")
    if not all(ok for _, ok in resultados):
        sys.exit(1)
