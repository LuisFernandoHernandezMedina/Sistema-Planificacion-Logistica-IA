# Sistema inteligente de planificación logística 12×12

Proyecto del segundo parcial: planificación de rutas de distribución con
búsqueda heurística, búsqueda local, metaheurísticas, teoría de juegos y
decisiones adversarias. La aplicación conserva la interfaz web Flask del
Proyecto 5 y amplía su alcance con cinco módulos que comparten un mismo
escenario logístico.

## 1. Objetivo

Construir una aplicación local que:

1. Modele una red logística en una cuadrícula de **12×12** con inicio,
   destino, al menos tres entregas, obstáculos, costos variables, recursos y
   un competidor.
2. Encuentre rutas de mínimo costo mediante **A\*** y **Greedy Best-First**.
3. Optimice el orden de visita con **Hill Climbing**, **recocido simulado** y
   un **algoritmo genético**.
4. Analice la interacción con un competidor mediante **teoría de juegos**
   (matriz de pagos, dominancia y equilibrios de Nash).
5. Modele decisiones adversarias de asignación de recursos con **Minimax** y
   **poda alfa-beta**.
6. Integre todos los resultados en una planificación final y genere
   **experimentos reproducibles** con CSV y gráficas.

La aplicación se ejecuta completamente en local. No utiliza Node.js, React,
Angular, bases de datos, APIs de mapas ni librerías que resuelvan los
algoritmos por nosotros.

## 2. Tecnologías

- Python 3.12
- Flask 3.0.3
- NumPy 1.26.4
- Matplotlib 3.9.2
- Pytest 9.2.0
- HTML, CSS y JavaScript puro
- JSON y CSV para configuración y resultados
- Módulos estándar `random`, `csv`, `json`, `heapq`, `math` e `io`

## 3. Instalación y ejecución

```powershell
pip install -r requirements.txt
python app.py
```

Abrir en el navegador:

```text
http://127.0.0.1:5000
```

Ejecutar los experimentos completos por consola:

```powershell
python experimentos/ejecutar_experimentos.py
```

Ejecutar las pruebas:

```powershell
python -m pytest -q
```

El archivo legado `algoritmo_genetico.py` (Proyecto 5) se conserva y puede
ejecutarse por separado con `python algoritmo_genetico.py`. El módulo C ya no
depende de él: `algoritmos/algoritmo_genetico.py` define sus propios
operadores OX y mutación.

## 4. Estructura del proyecto

```text
Proyecto5_Rutas/
├── app.py                         # Servidor Flask y API
├── algoritmo_genetico.py          # AG legado del Proyecto 5 (independiente del módulo C)
├── requirements.txt
├── README.md
├── INFORME_TECNICO.md
│
├── core/
│   ├── __init__.py
│   ├── escenario.py               # Escenario, validación, JSON y CSV
│   ├── mapa.py                    # Cuadrícula, costos, obstáculos y vecinos
│   ├── costos.py                  # Matriz de costos mínimos con A*
│   └── integracion.py             # Flujo completo y planificación final
│
├── algoritmos/
│   ├── busqueda_heuristica.py     # Módulo A: Greedy y A*
│   ├── busqueda_local.py          # Módulo B: Hill Climbing
│   ├── recocido_simulado.py       # Módulo C: recocido simulado
│   ├── algoritmo_genetico.py      # Módulo C: algoritmo genético
│   ├── teoria_juegos.py           # Módulo D: juego 3×3 y Nash
│   └── minimax.py                 # Módulo E: Minimax y alfa-beta
│
├── config/
│   ├── escenario.json             # Escenario logístico editable
│   └── parametros.json            # Parámetros reproducibles
│
├── experimentos/
│   ├── ejecutar_experimentos.py
│   ├── resultados/                # CSV generados
│   └── graficas/                  # PNG generados
│
├── templates/index.html           # Interfaz web
├── static/style.css
├── static/script.js
└── tests/                         # 57 pruebas automáticas
```

## 5. Modelo del escenario

El escenario se carga desde `config/escenario.json` o desde la interfaz. Sus
elementos son:

- Cuadrícula de 12 filas por 12 columnas.
- `inicio` y `destino` en coordenadas `[x, y]`.
- Al menos tres entregas, cada una con `id`, `nombre`, `x`, `y`, `demanda` y
  recursos requeridos.
- Matriz de costos de entrada por celda.
- Lista de obstáculos intransitables.
- Recursos globales: combustible, permisos y tiempo.
- Competidor con nombre, efecto sobre el costo, reducción de recursos y
  agresividad.
- Semilla para reproducibilidad.

El movimiento es en **cuatro direcciones** (arriba, abajo, izquierda y
derecha). El costo de un tramo es la suma de los costos de las celdas que se
entran. La ruta es **abierta**:

```text
Inicio -> entrega A -> entrega B -> ... -> Destino
```

No se regresa al inicio. Las entregas se visitan exactamente una vez.

### 5.1 Validaciones

`Escenario.validar()` comprueba:

- Dimensiones y costos válidos.
- Puntos dentro de la cuadrícula.
- Inicio y destino distintos.
- Al menos tres entregas.
- Sin entregas duplicadas ni nombres repetidos.
- Ningún punto sobre un obstáculo.
- Recursos globales suficientes para la suma de demandas de recursos.
- Conectividad de todos los puntos mediante búsqueda en anchura.

### 5.2 Formato JSON

El JSON contiene el nombre, dimensiones, inicio, destino, entregas, recursos,
competidor, semilla y el objeto `mapa` con costos y obstáculos. Se puede
editar desde la interfaz o exportar desde `/api/escenario/exportar/json`.

### 5.3 Formato CSV

El CSV contiene una fila por celda con las columnas:

```text
x,y,costo,obstaculo,tipo,nombre,id,demanda,recursos,
nombre_escenario,semilla,recursos_globales,competidor,orden
```

Los metadatos globales se escriben en la fila `(0, 0)`. La columna `orden`
conserva el orden original de las entregas al exportar e importar. El archivo
se genera con codificación **UTF-8 con BOM** (`utf-8-sig`) para que Excel y
Windows muestren correctamente los acentos.

## 6. Módulo A: búsqueda heurística

Archivo: `algoritmos/busqueda_heuristica.py`.

### 6.1 Greedy Best-First

Usa una cola de prioridad ordenada únicamente por la heurística
`h(n) = |x_n - x_destino| + |y_n - y_destino|`. Es rápido, pero no garantiza el
mínimo costo.

### 6.2 A\*

Evalúa `f(n) = g(n) + h(n)`, donde:

- `g(n)` es el costo acumulado desde el inicio.
- `h(n)` es la distancia Manhattan multiplicada por el costo mínimo de una
  celda transitable.

Esta heurística es **admisible y consistente**, por lo que A\* encuentra la
ruta de menor costo. Se registran nodos expandidos, longitud, camino, costo y
tiempo.

### 6.3 Comparación

La función `comparar_greedy_a_estrella()` ejecuta ambos algoritmos sobre el
mismo mapa y reporta costo, nodos, tiempo y diferencia de costo.

## 7. Módulo B: búsqueda local

Archivo: `algoritmos/busqueda_local.py`.

Se implementa **Hill Climbing** sobre permutaciones de entregas:

1. Genera al menos 10 soluciones iniciales aleatorias.
2. Para cada una, explora el vecindario de intercambiar dos entregas.
3. Se mueve al mejor vecino si mejora el costo.
4. Se detiene en un óptimo local o al alcanzar `max_iteraciones`.

El resultado incluye:

- Mejor orden y costo.
- Costo inicial y final de cada corrida.
- Iteraciones y número de vecinos empatados (mesetas).
- Óptimos locales distintos, porcentaje de mesetas, promedio, desviación y
  variabilidad.

## 8. Módulo C: metaheurísticas

### 8.1 Recocido simulado

Archivo: `algoritmos/recocido_simulado.py`.

- Estado inicial: permutación aleatoria.
- Vecindario: intercambio de dos entregas.
- Acepta una solución peor con probabilidad
  `exp(-(Δcosto) / temperatura)`.
- Enfriamiento geométrico: `T <- T * factor_enfriamiento`.
- Parámetros: temperatura inicial 50, final 0.01, factor 0.97 y 40
  iteraciones por temperatura.
- Registra mejor orden, costo, aceptaciones, rechazos, iteraciones,
  evaluaciones, tiempo e historial.

### 8.2 Algoritmo genético

Archivo: `algoritmos/algoritmo_genetico.py`.

- Población inicial de permutaciones aleatorias.
- Selección por torneo de tamaño 3.
- Cruzamiento **Order Crossover (OX)** definido en el propio módulo.
- Mutación por intercambio con probabilidad 0.15.
- Elitismo: el mejor individuo pasa a la siguiente generación.
- Parámetros por defecto: 60 individuos y 150 generaciones.
- Registra mejor orden, costo, historial, evaluaciones, tiempo y una alerta de
  posible convergencia prematura si no hay mejora durante muchas
  generaciones.

Ambos algoritmos aceptan una semilla para que los resultados sean
reproducibles.

Todas las permutaciones se evalúan con la matriz de costos de A\*, por lo que
solo contienen entregas alcanzables. La aptitud optimiza el costo de la ruta;
las restricciones de recursos y el efecto del competidor se aplican en la
integración final, donde un déficit genera una penalización y puede marcar el
plan como no factible sin adquisición.

## 9. Módulo D: teoría de juegos

Archivo: `algoritmos/teoria_juegos.py`.

Juego simultáneo de dos jugadores con tres estrategias cada uno:

| Empresa | Competidor |
|---|---|
| Ruta rápida | Bloqueo de ruta |
| Ruta económica | Presión de costos |
| Reserva preventiva | No intervención |

La matriz de pagos es de 3×3 y se calcula con datos reales del escenario:

```text
ingreso = suma(demanda de entregas) * 10
costo_ruta = costo_base_A* * multiplicador_empresa * multiplicador_competidor
penalizacion = recursos_totales * 0.02 * factor_recursos * captura
pago_empresa = ingreso - costo_ruta - penalizacion
pago_competidor = costo_ruta * captura + costo_base * 0.10
                  - costo_base * costo_competidor
```

El módulo calcula:

- Mejores respuestas de cada jugador.
- Estrategias dominantes y dominadas.
- Equilibrios de Nash puros.
- Interpretación textual del resultado.

En el escenario base la matriz tiene un único equilibrio de Nash puro:
**(Ruta rápida, Bloqueo de ruta)**. Ambos jugadores tienen una estrategia
**dominante estricta** (Ruta rápida para la empresa y Bloqueo de ruta para el
competidor), por lo que el equilibrio se alcanza por dominancia. El código lo
verifica comprobando que ninguna desviación unilateral mejora el pago, y
reporta si el equilibrio es estricto y eficiente en el sentido de Pareto. El
juego **no es de suma cero**: los pagos de ambos jugadores se calculan con
fórmulas distintas.

## 10. Módulo E: Minimax y poda alfa-beta

Archivo: `algoritmos/minimax.py`.

El subproblema es un juego **de suma cero, por turnos y con información
perfecta**. Cada entrega se convierte en un *contrato* con valor
`v = demanda + 5` (la prima de 5 representa la prioridad comercial).

| Elemento | Definición |
|---|---|
| Estado | `(R, A_max, A_min, turno)`: contratos disponibles, contratos asignados a cada jugador y de quién es el turno |
| Estado inicial | Todos los contratos disponibles y juega MAX (la empresa) |
| Acciones legales | Cualquier contrato aún disponible |
| Transición | El jugador en turno toma el contrato elegido; el turno pasa al rival |
| Estado terminal | No quedan contratos disponibles (profundidad = número de entregas) |
| Utilidad | `U = suma(v de A_max) - suma(v de A_min)`; MAX la maximiza, MIN la minimiza |
| Orden de acciones | Por valor descendente, igual en minimax y alfa-beta |

Con profundidad limitada, el nodo no terminal se valora con una **evaluación
aproximada**: se supone que los contratos restantes se reparten de forma
voraz y alternada, empezando por quien tiene el turno:
`U_aprox = U_actual + signo(turno) * (v1 - v2 + v3 - ...)`, con
`v1 >= v2 >= ...` los valores restantes. En este juego el reparto voraz
coincide con el óptimo, por lo que la aproximación no introduce error en el
escenario base (limitación: no sirve para mostrar el error de una evaluación
aproximada).

Se implementan dos versiones:

1. **Minimax sin poda**, que visita el árbol completo.
2. **Minimax con poda alfa-beta**, que mantiene el mismo valor y reduce nodos.

Contadores: `nodos_visitados` son los nodos explorados; `nodos_podados` son
los nodos de los subárboles omitidos (conteo exacto), de modo que siempre se
cumple `visitados(alfa-beta) + podados = visitados(minimax)`. `cortes` es el
número de veces que se activó `alfa >= beta`.

## 11. Integración y planificación final

Archivo: `core/integracion.py`.

Flujo de `ejecutar_planificacion()`:

1. Valida el escenario.
2. Construye la matriz de costos mínimos entre inicio, entregas y destino con
   A\*.
3. Ejecuta Greedy y A\* entre inicio y destino.
4. Ejecuta Hill Climbing, recocido simulado y algoritmo genético sobre el
   orden de entregas.
5. Elige el menor costo entre los tres métodos.
6. Analiza el juego con el competidor y selecciona el equilibrio de Nash con
   el peor pago para la empresa.
7. Ejecuta Minimax y traduce su valor en una fracción de recursos conservada.
8. Calcula la planificación final:

```text
costo_ruta_base = costo del mejor orden
costo_ruta_ajustado = costo_ruta_base * factor_competidor
costo_total_integrado = costo_ruta_ajustado + penalización_por_déficit
```

El plan incluye ruta, orden, costo, estrategia de la empresa, estrategia del
competidor, asignación de recursos, advertencias y factibilidad sin
adquisición adicional.

## 12. Interfaz web

La página tiene ocho secciones:

1. **Escenario**: editor de cuadrícula, entregas, costos, obstáculos,
   recursos y competidor; carga y exportación JSON/CSV.
2. **Búsqueda heurística**: Greedy vs A\*, rutas, costos y nodos.
3. **Búsqueda local**: Hill Climbing, corridas, óptimos y mesetas.
4. **Metaheurísticas**: recocido simulado y algoritmo genético con
   convergencia.
5. **Teoría de juegos**: matriz 3×3, dominancia y Nash.
6. **Minimax**: comparación sin poda vs alfa-beta.
7. **Planificación integrada**: ruta final, costos y recursos.
8. **Experimentos**: ejecución, resumen, CSV y gráficas.

La cuadrícula se dibuja en SVG. Los puntos se pueden mover, las entregas se
pueden agregar, editar o eliminar y los obstáculos se activan con clic. Los
resultados se actualizan mediante `fetch` contra la API Flask.

## 13. API principal

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/` | Interfaz web |
| GET | `/api/escenario` | Escenario actual y validación |
| POST | `/api/escenario` | Reemplaza el escenario |
| POST | `/api/escenario/validar` | Valida sin guardar |
| POST | `/api/escenario/restablecer` | Restaura el escenario base |
| POST | `/api/escenario/cargar` | Carga JSON o CSV |
| GET | `/api/escenario/exportar/json` | Exporta JSON |
| GET | `/api/escenario/exportar/csv` | Exporta CSV |
| POST | `/api/busqueda_heuristica` | Módulo A |
| POST | `/api/busqueda_local` | Módulo B |
| POST | `/api/recocido` | Recocido simulado |
| POST | `/api/genetico` | Algoritmo genético |
| POST | `/api/metaheuristicas` | Ambos métodos del módulo C |
| POST | `/api/teoria_juegos` | Módulo D |
| POST | `/api/minimax` | Comparación Minimax/alfa-beta |
| POST | `/api/minimax/solo` | Una sola versión |
| POST | `/api/integracion` | Flujo completo |
| POST/GET | `/api/planificacion`, `/ejecutar` | Alias de integración |
| POST | `/api/experimentos` | Ejecuta experimentos |
| GET | `/api/experimentos/archivos` | Lista CSV y PNG |
| GET | `/puntos` | Compatibilidad con el Proyecto 5 |

Los parámetros de cada módulo se envían en el cuerpo JSON. Por ejemplo:

```json
{
  "soluciones_iniciales": 10,
  "max_iteraciones": 200,
  "semilla": 42
}
```

## 14. Experimentos y resultados

El script `experimentos/ejecutar_experimentos.py` genera:

- `experimentos/resultados/*.csv`
- `experimentos/resultados/parametros_experimento.json`
- `experimentos/graficas/*.png`

El JSON de parámetros conserva el escenario, la semilla base, el número de
repeticiones y todos los parámetros utilizados.

Resultados del escenario base:

### 14.1 Heurísticas

| Escenario | Greedy | A\* | Nodos Greedy | Nodos A\* |
|---|---:|---:|---:|---:|
| Base | 53.0 | 34.0 | 23 | 111 |
| Costos altos | 84.8 | 54.4 | 23 | 111 |
| Más obstáculos | 53.0 | 35.0 | 23 | 111 |

A\* obtiene un costo menor en los tres escenarios. Greedy expande menos nodos,
pero su ruta es más costosa.

### 14.2 Hill Climbing

Diez corridas con semillas 42 a 51:

- Mejor costo: **66**.
- Se detectaron tres óptimos locales distintos.
- No se detectaron mesetas.
- El costo final nunca fue mayor que el inicial.

### 14.3 Metaheurísticas (20 repeticiones)

| Método | Mejor | Promedio | Desviación | Peor | Evaluaciones |
|---|---:|---:|---:|---:|---:|
| Recocido simulado | 66.0 | 66.0 | 0.0 | 66.0 | 11 201 |
| Algoritmo genético | 66.0 | 66.55 | 2.3974 | 77.0 | 9 060 (conteo real de la función objetivo) |

El recocido fue más estable; el AG encontró el óptimo en 19 de 20 corridas.

### 14.4 Teoría de juegos

- Equilibrio de Nash puro: **(Ruta rápida, Bloqueo de ruta)**.
- Ambos jugadores tienen estrategia dominante estricta: Ruta rápida
  (empresa) y Bloqueo de ruta (competidor). El equilibrio es único, estricto
  y eficiente en el sentido de Pareto.

### 14.5 Minimax

| Método | Valor | Nodos visitados | Nodos podados |
|---|---:|---:|---:|
| Sin poda | 17 | 326 | 0 |
| Alfa-beta | 17 | 76 | 250 |

La poda omite 250 de los 326 nodos (76.69 %) sin cambiar el valor ni la
decisión; 76 + 250 = 326. Con profundidades 1 a 5 el valor minimax es 17 en
ambos métodos.

### 14.6 Planificación final

| Indicador | Valor |
|---|---:|
| Algoritmo de origen | Hill Climbing |
| Costo de ruta base | 66.0 |
| Factor del competidor | 1.2537 |
| Costo total integrado | 102.7442 |
| Estrategia de la empresa | Ruta rápida |
| Estrategia del competidor | Bloqueo de ruta |
| Factible sin adquisición | No |

La reducción de recursos del competidor genera un déficit y una penalización
de costo. La planificación final lo reporta como advertencia en lugar de
ocultarlo.

## 15. Pruebas automáticas

`tests/` contiene 57 pruebas:

- Validaciones del escenario y errores controlados.
- Roundtrip JSON y CSV, incluidos recursos y competidor.
- A\* y Greedy, mapa sin solución, obstáculos y heurística admisible.
- Hill Climbing, mesetas y reproducibilidad.
- Recocido y AG con semilla fija.
- Matriz de pagos, mejores respuestas, dominancia y Nash.
- Minimax vs alfa-beta, profundidad limitada y decisión.
- Integración completa y efecto del competidor.
- Endpoints Flask, errores 400 y exportación.

Ejecutar:

```powershell
python -m pytest -q
```

## 16. Reproducibilidad

- Todas las funciones aleatorias reciben una semilla explícita.
- La semilla global por defecto es **42**.
- Los experimentos usan semillas consecutivas para medir variabilidad.
- Los CSV conservan el escenario y los parámetros utilizados.
- Las gráficas se regeneran con el mismo script.

## 17. Limitaciones

- El mapa es una cuadrícula abstracta, no un mapa geográfico real.
- A\* garantiza el mínimo costo entre dos puntos, pero la optimización del
  orden de entregas es aproximada.
- Con cinco entregas el espacio de permutaciones es pequeño; con muchas más,
  el costo de Minimax crece factorialmente.
- La interpretación del competidor es un modelo de decisión, no una predicción
  real de mercado.
- La interfaz usa recursos locales y no está pensada para despliegue en
  internet.

## 18. Relación con los requisitos del segundo parcial

| Requisito | Implementación |
|---|---|
| Cuadrícula configurable 12×12 | `core/mapa.py`, `core/escenario.py` |
| Inicio, destino, ≥3 entregas, obstáculos y costos | `config/escenario.json` y editor web |
| Recursos y competidor | Modelo de escenario y módulos D/E |
| Búsqueda heurística | Módulo A: Greedy y A\* |
| Búsqueda local | Módulo B: Hill Climbing |
| Metaheurísticas | Módulo C: recocido y AG |
| Teoría de juegos | Módulo D: matriz 3×3 y Nash |
| Minimax y poda alfa-beta | Módulo E |
| Integración de módulos | `core/integracion.py` |
| Interfaz web | Flask, HTML, CSS y JS |
| Experimentos y gráficas | `experimentos/` |
| Pruebas | `tests/` con Pytest |
| Informe | `INFORME_TECNICO.md` |
