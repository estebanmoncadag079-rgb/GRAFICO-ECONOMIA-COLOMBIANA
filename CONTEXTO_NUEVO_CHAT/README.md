# Traspaso de la investigacion del dashboard colombiano

Fecha del traspaso: 2026-09-24. Este documento esta pensado para una tarea
nueva que no pueda ver la conversacion anterior. Leer tambien `README.md`,
`DATA_DICTIONARY.md`, `AUDITORIA_CRITICA_DATOS_DASHBOARD.md` y
`OPERACION_DATOS.md` en la raiz del proyecto.

## Objetivo del usuario

Construir un dashboard para estudiar la economia colombiana real, con datos
trazables, formulas correctas, visualizacion interpretable y actualizacion
automatica cuando las fuentes publiquen. El usuario pidio una auditoria
critica profunda. **No eliminar lineas ni archivos historicos por defecto**:
primero entender y reconfirmar su metodologia. En particular, mantener la
comparacion bursatil original junto a la nueva serie oficial.

## Git, revision y despliegue

- Repositorio: `estebanmoncadag079-rgb/GRAFICO-ECONOMIA-COLOMBIANA`.
- Rama de trabajo: `codex/datos-economia-colombiana`.
- PR en borrador: https://github.com/estebanmoncadag079-rgb/GRAFICO-ECONOMIA-COLOMBIANA/pull/1
- La rama fue subida; `main` no se fusiono y Render no se desplego.
- El workflow diario solo se ejecutara por horario desde la rama
  predeterminada despues de fusionar. Antes hay que confirmar permisos de
  escritura de GitHub Actions y auto-deploy de Render desde `main`.
- No fusionar ni activar Render sin revisar los limites metodologicos con el
  usuario.

## Cambios hechos en la rama

- `actualizar_pib.py`: PIB trimestral real y nominal desde anexos DANE;
  crecimiento interanual real, trimestral desestacionalizado y nominal
  separados. Ya no interpola un dato anual del Banco Mundial.
- `actualizar_inflacion.py`: serie mensual IPC desde DANE y BanRep,
  privilegiando tasas oficialmente publicadas cuando difieren del calculo
  sobre un indice redondeado. Se registra procedencia por valor.
- `actualizar_tes.py`: historico de tasas cero cupon TES pesos y UVR desde
  BanRep. Siete valores aislados sospechosos se conservan en CSV y se
  ocultan solo en el grafico mediante una alerta reproducible.
- `actualizar_colcap.py`: nivel diario oficial del indice publicado por
  BanRep/BVC, en puntos y normalizado a base 100 el 2009-02-09.
- `construir_tablas_experimentales.py`: retornos mensuales de canastas
  propias, con cobertura, numero de precios validos y alertas. No inventa
  precios diarios.
- `dashboard_colombia.py`: grafico macro con frecuencias diferenciadas,
  grafico TES, grafico bursatil de tres lineas, estado de fuentes,
  selectores y diseno responsive.
- `validar_datos.py`, `estado_fuentes.csv`, `alertas_datos.csv`: controles de
  formulas, fechas, rangos, cobertura, rezagos y anomalias.
- `.github/workflows/actualizar-datos.yml`: consulta diaria a las 19:30
  de Colombia, valida y confirma CSV nuevos si cambiaron. Todavia no se
  probo remotamente porque el workflow no esta en `main`.
- `tests/`: cinco pruebas unitarias aprobadas. El dashboard fue comprobado
  en escritorio y movil, incluido el selector de lineas y ausencia de
  desbordamiento horizontal.

## Lectura correcta del grafico bursatil

1. Verde continua: COLCAP publicado por BanRep, fuente BVC/MSCI segun
   periodo. Es la unica linea del grafico tratada como indice oficial.
2. (Retirada el 2026-09-25) La morada punteada "ICOLCAP empalmado" se
   elimino del grafico por pedido del usuario: `icolcap_referencia.csv`
   parece estar en dolares y se empalmaba con retornos en pesos.
3. Azul punteada: indice equiponderado propio. Promedia retornos mensuales
   entre acciones de la canasta con precio en ambos meses y luego la
   construccion antigua dibujo puntos diarios siguiendo la forma del indice
   empalmado. Es una senal de amplitud, pero NO cuenta literalmente acciones
   al alza menos acciones a la baja.
4. Amarilla punteada: canasta propia llamada "7 Magnificas". El conjunto
   original en `construir_indices.py` es ECOPETROL, PFBCOLOM, GRUPOSURA,
   GRUPOARGOS, PFAVAL, ISA y NUTRESA. En meses recientes solo cinco de esos
   tickers tienen precios validos en el archivo local. La seleccion expresa
   una hipotesis de liderazgo bursatil, no una contribucion al PIB medida
   por DANE. Sus puntos diarios tambien son sintesis visual de retornos
   mensuales, no observaciones diarias de la canasta.

Las tres curvas parten de una base 100 el 2009-02-09, pero eso no iguala
sus fuentes ni metodologias. El selector deja ocultar o mostrar cada una.
No volver a retirar la azul o la amarilla sin discutirlo con el usuario.

## Calidad y rezagos comprobados

- PIB DANE: ultimo trimestre 2026-T2, publicado el 2026-08-18.
- IPC DANE/BanRep: ultimo mes 2026-08, publicado el 2026-09-07.
- TES BanRep: ultima observacion del archivo 2026-09-18.
- COLCAP BanRep: ultima observacion del archivo 2026-09-24.
- Canastas: ultimo retorno mensual con cobertura suficiente 2026-04.
  El archivo original `indices_colombia.csv` llega al 2026-05-27,
  pero esa extension no implica cobertura suficiente ni validacion.
- `precios_icolcap_limpios.csv` tiene valores poblados hasta mayo de 2026;
  los meses posteriores contienen filas vacias o futuras. Mayo solo tiene
  dos pares de precio validos frente a 22 tickers de canasta.
- Siete observaciones TES son sospechosas por picos de un dia. Se avisan,
  no se reescriben. El validador alerta sobre filas futuras legadas.

## Brecha principal descubierta al investigar fuentes oficiales

- `Canasta_Historica_ICAP.xls` contiene hojas anuales 2008-2020 y una hoja
  `COLCAP` que el codigo atribuye a algunos meses de 2021. No contiene
  una historia completa de composiciones posteriores a 2021.
- Para periodos posteriores, `cargar_canastas()` repite una composicion
  local actual de 22 tickers. `icolcap_composicion.csv` tiene todas las
  columnas `peso_icolcap` en cero. No usarlo para afirmar pesos oficiales.
- El 28 de mayo de 2021, MSCI COLCAP reemplazo la metodologia bvc COLCAP,
  manteniendo niveles historicos. La serie larga oficial debe anotar ese
  cambio de metodologia al interpretarse.
- BanRep publica el nivel oficial diario. MSCI publica metodologia y parte
  de la composicion actual, pero su API de componentes, eventos corporativos
  y dividendos depende de derechos de acceso. Un factsheet publico no es
  una licencia para reutilizar toda la historia como base de otro indice.
- La Superfinanciera ofrece una consulta diaria de negociaciones con
  acciones, pero la pagina observada usa captcha; no se comprobo un canal
  automatizable ni una cobertura historica completa. No eludir captcha.

Fuentes primarias verificadas:

- BanRep COLCAP: https://www.banrep.gov.co/en/node/50428
- DANE PIB: https://www.dane.gov.co/index.php/estadisticas-por-tema/cuentas-nacionales/cuentas-nacionales-trimestrales/pib-informacion-tecnica
- DANE IPC: https://www.dane.gov.co/index.php/estadisticas-por-tema/precios-y-costos/indice-de-precios-al-consumidor-ipc/ipc-informacion-tecnica
- MSCI transicion 2021: https://www.msci.com/eqb/methodology/meth_docs/MSCI_COLCAP_Index_Methodology_March2021.pdf
- MSCI indice actual: https://www.msci.com/indexes/index/737809/msci-colcap-index
- MSCI API: https://developer.msci.com/apis/index-api
- MSCI condiciones: https://www.msci.com/legal/index-terms
- Superfinanciera consulta: https://www.superfinanciera.gov.co/InformacionMercadoValores/reporteRBVC/index.xhtml

## Pendiente, en orden recomendado

1. Encontrar un canal oficial y legalmente reutilizable para componentes
   historicos fechados desde 2021 y para precios por accion ajustados por
   splits, dividendos y eventos corporativos. Verificar cobertura, licencia
   y posibilidad de automatizacion; no afirmar que ya se encontro.
2. Reconstruir una tabla larga por fecha/ticker con fuente, version,
   composicion, precio, ajuste, cobertura y estado. Evitar look-ahead:
   aplicar cada canasta solo desde su fecha efectiva.
3. Definir con el usuario si las "7 Magnificas" permanecen como lista fija
   original o cambian mediante una regla economica explicita. Mantener la
   curva vieja visible mientras se revisa; una nueva version debe tener
   nombre y version propios.
4. Calcular los dos indices propios a la frecuencia que soporte la fuente
   real (mensual o diaria) y comparar mes a mes con la reconstruccion vieja.
   No distribuir retornos mensuales en dias como si fueran observaciones.
5. Anotar en el dashboard el cambio metodologico COLCAP de 2021 y mostrar
   fecha real de ultimo dato de cada canasta. No interpretar la bolsa como
   sinonimo de PIB o de toda la economia colombiana.
6. Revisar con el usuario el PR en borrador y los hallazgos antes de
   fusionar, probar GitHub Actions en la rama predeterminada y confirmar
   el auto-deploy de Render.

## Insumos que podrian requerir ayuda del usuario

No hacen falta archivos manuales para actualizar PIB, IPC, TES y COLCAP.
Si no aparecen publicamente con derechos de reutilizacion, pedir acceso o
archivos de componentes historicos completos y precios ajustados por accion
(con condiciones de licencia), especialmente desde la transicion de 2021.
Pedir tambien su criterio exacto para las "7 Magnificas" antes de cambiar
esa canasta. No pedir descargas indiscriminadas.

## Estado al traspasar

No hay cambios de codigo ni CSV sin confirmar al iniciar este documento.
La busqueda de precios y componentes oficiales estaba en investigacion;
el ultimo hallazgo firme fue la brecha 2021-presente y la restriccion de
licencia MSCI. El PR sigue en borrador; no se ha fusionado ni desplegado.
