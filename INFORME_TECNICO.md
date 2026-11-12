# Informe técnico

## Sistema inteligente de planificación, optimización y toma de decisiones para una red logística 12×12

**Proyecto:** Segundo parcial  
**Modalidad:** individual  
**Tecnologías:** Python, Flask, NumPy, Matplotlib, HTML/CSS/JavaScript  
**Ejecución:** local en Windows  
**Fecha:** noviembre de 2026

---

## Resumen ejecutivo

El presente proyecto implementa un sistema local de planificación logística
sobre una cuadrícula de 12×12. El sistema integra cinco técnicas de
inteligencia artificial sobre un mismo escenario: búsqueda heurística con
Greedy Best-First y A\*, búsqueda local con Hill Climbing, metaheurísticas con
recocido simulado y algoritmo genético, teoría de juegos para modelar un
competidor y Minimax con poda alfa-beta para decisiones adversarias de
asignación de recursos.

Todas las técnicas comparten el mismo mapa, las mismas entregas, los mismos
recursos y la misma matriz de costos mínimos. La aplicación calcula una ruta
final, su costo ajustado por el competidor y una penalización por déficit de
recursos. También genera experimentos reproducibles, archivos CSV y gráficas.

Los resultados permiten observar que A\* obtiene rutas de menor costo que
Greedy, que el recocido simulado fue más estable que el algoritmo genético en
las 20 repeticiones realizadas, que existe un único equilibrio de Nash puro entre
“Ruta rápida” y “Bloqueo de ruta” (ambas son estrategias dominantes
estrictas), y que la poda alfa-beta reduce los nodos visitados por Minimax de
326 a 76, omitiendo 250, sin alterar el valor de la decisión.

---

## 1. Introducción

El problema de distribución de mercancías combina dos decisiones: encontrar
caminos de bajo costo entre puntos y decidir el orden de visita de las
entregas. A esto se añaden restricciones de recursos y la presencia de un
competidor que puede modificar el costo o reducir la disponibilidad de
insumos.

El Proyecto 5 original resolvía una instancia tipo viajante de comercio con un
algoritmo genético y una interfaz web. Este proyecto conserva esa base, pero
la amplía para cumplir el alcance del segundo parcial: un escenario logístico
configurable, cinco módulos de inteligencia artificial, experimentación
reproducible y una planificación final integrada.

La aplicación no pretende sustituir un sistema real de logística. Su valor es
académico: permite comparar algoritmos, justificar decisiones y observar cómo
interactúan técnicas de búsqueda, optimización y teoría de juegos sobre una
misma instancia.

---

## 2. Objetivos

### 2.1 Objetivo general

Diseñar e implementar un sistema inteligente que planifique rutas de
distribución en una red logística 12×12, optimice el orden de las entregas y
apoye la toma de decisiones frente a un competidor mediante búsqueda
heurística, búsqueda local, metaheurísticas, teoría de juegos y Minimax.

### 2.2 Objetivos específicos

1. Modelar un escenario logístico configurable con inicio, destino, entregas,
   obstáculos, costos, recursos y competidor.
2. Implementar búsqueda heurística con Greedy Best-First y A\*.
3. Implementar Hill Climbing para el orden de visita de las entregas.
4. Implementar recocido simulado y un algoritmo genético.
5. Construir una matriz de pagos 3×3 y calcular equilibrios de Nash.
6. Implementar Minimax con y sin poda alfa-beta.
7. Integrar los resultados en una planificación final coherente.
8. Generar experimentos reproducibles con CSV y gráficas.
9. Validar el sistema con pruebas automáticas.

---

## 3. Planteamiento del problema

Se dispone de una cuadrícula de 12 filas por 12 columnas. Cada celda tiene un
costo de entrada. Algunas celdas son obstáculos intransitables. El vehículo
parte de un punto llamado **Inicio**, debe visitar todas las entregas
exactamente una vez y terminar en **Destino**.

Formalmente, sea:

- `P = {Inicio, E1, E2, ..., En, Destino}` el conjunto de puntos.
- `c(i, j)` el costo mínimo de ir del punto `i` al punto `j`.
- `π` una permutación de las entregas.

El costo de una ruta es:

```text
C(π) = c(Inicio, π1) + Σ c(πk, πk+1) + c(πn, Destino)
```

El objetivo es encontrar `π*` que minimice `C(π)`, sujeto a que todos los
puntos sean alcanzables y a que los recursos disponibles cubran las demandas.

Además, el competidor puede:

- Aumentar el costo de la ruta.
- Reducir la disponibilidad de recursos.
- Cambiar la estrategia óptima de la empresa.

Por ello, el problema no termina en la ruta de menor costo: también incluye
una decisión estratégica y una asignación de recursos.

---

## 4. Marco teórico

### 4.1 Búsqueda heurística

La búsqueda heurística guía la exploración usando una estimación del costo
restante. Greedy Best-First ordena los nodos por `h(n)` y suele ser rápido,
aunque no garantiza optimalidad. A\* ordena por:

```text
f(n) = g(n) + h(n)
```

donde `g(n)` es el costo acumulado y `h(n)` una estimación admisible. Si `h`
es admisible y consistente, A\* encuentra la ruta de mínimo costo.

En este proyecto:

```text
h(n) = (|x_n - x_destino| + |y_n - y_destino|) * costo_mínimo_celda
```

La distancia Manhattan es una cota inferior porque el movimiento es en cuatro
direcciones y cada paso entra a una celda cuyo costo es al menos el mínimo del
mapa.

### 4.2 Búsqueda local

Hill Climbing parte de una solución y se mueve repetidamente al mejor vecino.
Es sencillo y rápido, pero puede quedar atrapado en óptimos locales o en
mesetas. En este proyecto el vecindario consiste en intercambiar dos entregas
de la permutación.

### 4.3 Recocido simulado

El recocido simulado acepta soluciones peores con probabilidad:

```text
P(aceptar) = exp(-ΔC / T)
```

donde `ΔC` es el incremento de costo y `T` la temperatura actual. Al inicio la
temperatura es alta y permite explorar; luego disminuye y el algoritmo se
vuelve más selectivo. Se usa enfriamiento geométrico:

```text
T_{k+1} = T_k * α
```

### 4.4 Algoritmo genético

Un algoritmo genético mantiene una población de soluciones y las combina
mediante selección, cruzamiento y mutación. En este proyecto:

- La selección es por torneo.
- El cruzamiento es Order Crossover (OX), que preserva permutaciones válidas.
- La mutación intercambia dos posiciones.
- El elitismo conserva el mejor individuo.

### 4.5 Teoría de juegos

Un juego simultáneo de dos jugadores se representa con una matriz de pagos. Un
**equilibrio de Nash puro** es una celda en la que ningún jugador mejora
cambiando unilateralmente de estrategia. Una estrategia es **dominante
estricta** si produce un pago mayor que el de *todas* las demás estrategias
del jugador frente a cualquier respuesta del rival (es **débil** si es mayor o
igual en todas y mayor en al menos una). Dominar a una sola estrategia no
convierte a otra en dominante. Si ambos jugadores tienen una estrategia
dominante estricta, la combinación de ambas es el único equilibrio de Nash.

### 4.6 Minimax y poda alfa-beta

Minimax modela un juego por turnos entre un jugador MAX y un jugador MIN. MAX
elige la acción de mayor utilidad y MIN la de menor utilidad. La poda
alfa-beta mantiene dos cotas:

- `α`: mejor valor encontrado para MAX.
- `β`: mejor valor encontrado para MIN.

Si `α ≥ β`, la rama no puede mejorar la decisión y se poda. La poda no cambia
el resultado, solo reduce el número de nodos visitados.

---

## 5. Diseño de la solución

### 5.1 Arquitectura

La aplicación se organiza en capas:

```text
Interfaz web (HTML/CSS/JS)
        ↓ fetch
API Flask (app.py)
        ↓
Integración (core/integracion.py)
        ↓
Algoritmos (algoritmos/)
        ↓
Modelo compartido (core/escenario.py, core/mapa.py, core/costos.py)
```

La capa de modelo contiene el escenario y la cuadrícula. La capa de costos
construye la matriz mínima entre puntos. La capa de algoritmos implementa los
cinco módulos. La capa de integración ejecuta el flujo completo. La interfaz
solo consume la API y dibuja resultados.

### 5.2 Escenario compartido

El escenario se define en `core/escenario.py`. Sus atributos principales son:

- `nombre`, `filas`, `columnas`, `semilla`.
- `inicio` y `destino`.
- Lista de entregas con demanda y recursos.
- `Mapa` con costos y obstáculos.
- Recursos globales.
- Datos del competidor.

El escenario se puede crear por defecto, cargar desde JSON, cargar desde CSV,
exportar a JSON y exportar a CSV. La validación es común para todos los
módulos; ningún algoritmo recibe una instancia inválida.

### 5.3 Matriz de costos compartida

`core/costos.py` construye una matriz de tamaño `(n + 2) × (n + 2)`, donde `n`
es el número de entregas. Los índices son:

```text
0 = Inicio
1..n = entregas
n+1 = Destino
```

Cada entrada se calcula con A\* sobre el mapa. Si un par no es alcanzable, se
marca como infinito y se reporta en `inalcanzables`. Esta matriz es usada por
Hill Climbing, recocido, algoritmo genético y la planificación final.

### 5.4 Flujo de integración

`ejecutar_planificacion()` realiza:

1. Validación del escenario.
2. Construcción de la matriz de costos.
3. Ejecución de Greedy y A\* entre Inicio y Destino.
4. Ejecución de Hill Climbing, recocido y AG.
5. Selección del menor costo entre los tres métodos.
6. Análisis del juego con el competidor.
7. Minimax y asignación de recursos.
8. Cálculo del costo final integrado.

---

## 6. Implementación de los módulos

### 6.1 Módulo A: búsqueda heurística

Archivo: `algoritmos/busqueda_heuristica.py`.

Se implementan dos funciones principales:

- `greedy_best_first(mapa, inicio, destino)`.
- `a_estrella(mapa, inicio, destino)`.

Ambas devuelven un diccionario con:

```text
encontrado, camino, costo, longitud, nodos_expandidos, tiempo_ms
```

También se implementa `comparar_greedy_a_estrella()`, que ejecuta ambos sobre
el mismo mapa y calcula la diferencia de costo.

### 6.2 Módulo B: búsqueda local

Archivo: `algoritmos/busqueda_local.py`.

La función `hill_climbing()`:

1. Genera `soluciones_iniciales` permutaciones aleatorias.
2. Evalúa el vecindario de intercambios.
3. Se mueve al mejor vecino si mejora.
4. Registra costo inicial, costo final, iteraciones, mesetas y orden.

El análisis agrega mejor costo, promedio, desviación, peor costo, número de
óptimos locales distintos y porcentaje de corridas con meseta.

### 6.3 Módulo C: recocido simulado

Archivo: `algoritmos/recocido_simulado.py`.

La función `recocido_simulado()` recibe la matriz, el número de entregas y los
parámetros de temperatura. En cada iteración genera un vecino, calcula la
diferencia de costo y decide si lo acepta. Guarda el historial del mejor costo
y cuenta aceptaciones y rechazos.

### 6.4 Módulo C: algoritmo genético

Archivo: `algoritmos/algoritmo_genetico.py`.

La función `algoritmo_genetico()`:

- Genera una población de permutaciones.
- Evalúa cada individuo con la matriz de costos.
- Selecciona padres por torneo.
- Aplica OX y mutación.
- Conserva el mejor individuo si el elitismo está activo.
- Registra el historial y las evaluaciones.

`cruzamiento_ox()` y `mutar()` están definidos en el propio módulo y aceptan un
generador aleatorio para reproducibilidad. La selección por torneo usa los
costos ya calculados de la generación, de modo que cada permutación se evalúa
una sola vez por generación y el contador de evaluaciones coincide con las
llamadas reales a la función objetivo (`tamano_poblacion × (generaciones + 1)`
= 9 060). La versión anterior reevaluaba en cada torneo (62 220 llamadas reales
frente a 9 060 reportadas).

**Tratamiento de restricciones.** Todas las permutaciones se evalúan con la
matriz de costos construida por A\*, de modo que solo contienen entregas
alcanzables. La función de aptitud optimiza el costo de la ruta. Las
restricciones de recursos y el efecto del competidor se aplican en la
integración final: si la fracción conservada no cubre la demanda, se calcula
un déficit, se suma su penalización y el plan se marca como no factible sin
adquisición. Esta separación evita que Hill Climbing, el recocido o el AG
descartan soluciones por un costo estratégico que todavía no ha sido
calculado por el módulo de juegos.

### 6.5 Módulo D: teoría de juegos

Archivo: `algoritmos/teoria_juegos.py`.

La matriz de pagos se construye con datos del escenario. Las estrategias son:

```text
Empresa:     Ruta rápida, Ruta económica, Reserva preventiva
Competidor:  Bloqueo de ruta, Presión de costos, No intervención
```

Para cada celda se calcula:

```text
ingreso = suma(demanda) * 10
costo_ruta = costo_base * mult_empresa * mult_competidor
penalizacion = recursos_totales * 0.02 * factor_recursos * captura
pago_empresa = ingreso - costo_ruta - penalizacion
pago_competidor = costo_ruta * captura + costo_base * 0.10
                  - costo_base * costo_competidor
```

El módulo calcula mejores respuestas, dominancia, Nash puro e interpretación.

### 6.6 Módulo E: Minimax y alfa-beta

Archivo: `algoritmos/minimax.py`.

El subproblema es un juego de **suma cero, por turnos y con información
perfecta** entre la empresa (MAX) y el competidor (MIN). Cada entrega se
convierte en un contrato con valor `v = demanda + 5`; la prima de 5
representa la prioridad comercial de atenderla.

| Elemento | Definición |
|---|---|
| Estado | `(R, A_max, A_min, turno)` |
| Estado inicial | `R` = todos los contratos, `A_max = A_min = ∅`, juega MAX |
| Acciones legales | Cualquier contrato de `R` |
| Transición | El jugador en turno mueve el contrato elegido de `R` a su conjunto; el turno pasa al rival |
| Terminal | `R = ∅` (con *n* entregas, profundidad *n*) |
| Utilidad | `U = Σ v(A_max) − Σ v(A_min)` desde el punto de vista de MAX |
| Orden de acciones | Valor descendente, el mismo en ambos algoritmos |

Con profundidad limitada se usa una evaluación aproximada basada en un reparto
voraz alternado de los contratos restantes:

```text
U_aprox = U_actual + signo(turno) * (v1 - v2 + v3 - ...),   v1 >= v2 >= ...
signo(MAX) = +1, signo(MIN) = -1
```

Solo se aplica cuando se alcanza la profundidad máxima sin agotar los
contratos; si el árbol termina completo se usa la utilidad exacta. En este
juego el reparto voraz coincide con el reparto óptimo, así que la evaluación
no introduce error en el escenario base.

Se implementan `minimax()` y `minimax_alfa_beta()`. `nodos_visitados` cuenta
los nodos explorados y `nodos_podados` los nodos de los subárboles omitidos
(conteo exacto), de modo que `visitados(α-β) + podados = visitados(minimax)`.
`cortes_alfa_beta` registra cuántas veces se activó `α ≥ β`. El tiempo es la
mediana de 15 ejecuciones tras una de calentamiento.

### 6.7 Integración

Archivo: `core/integracion.py`.

La integración elige el mejor orden entre Hill Climbing, recocido y AG. Luego
aplica el factor del competidor asociado al equilibrio de Nash y la
penalización por déficit de recursos calculada a partir de Minimax.

La fórmula final es:

```text
costo_ruta_base = costo del mejor orden
costo_ruta_ajustado = costo_ruta_base * factor_competidor
costo_total_integrado = costo_ruta_ajustado + penalización_por_déficit
```

---

## 7. Experimentos

### 7.1 Metodología

Los experimentos se ejecutan con:

```powershell
python experimentos/ejecutar_experimentos.py
```

El script:

1. Carga el escenario base.
2. Ejecuta Greedy y A\* en tres variantes: base, costos altos y más
   obstáculos.
3. Ejecuta Hill Climbing con 10 semillas.
4. Ejecuta recocido y AG con 20 semillas.
5. Analiza el juego y Minimax.
6. Genera la planificación final.
7. Guarda CSV, un JSON con los parámetros y las gráficas.

El archivo `parametros_experimento.json` registra el escenario, la semilla
base, las repeticiones y los parámetros de cada algoritmo.

Entorno de ejecución:

- Windows.
- Python 3.12.
- Los tiempos son orientativos y pueden variar según el equipo.

### 7.2 Búsqueda heurística

| Escenario | Greedy | A\* | Nodos Greedy | Nodos A\* | Diferencia |
|---|---:|---:|---:|---:|---:|
| Base | 53.0 | 34.0 | 23 | 111 | -19.0 |
| Costos altos | 84.8 | 54.4 | 23 | 111 | -30.4 |
| Más obstáculos | 53.0 | 35.0 | 23 | 111 | -18.0 |

A\* obtiene siempre un costo menor. Greedy expande menos nodos porque no
considera el costo acumulado, pero su ruta es más costosa. Esto ilustra el
compromiso entre velocidad y optimalidad.

### 7.3 Búsqueda local

Con semillas 42 a 51:

- Mejor costo: 66.0.
- Costo inicial promedio: cercano a 101.6.
- Se encontraron tres óptimos locales distintos.
- No se detectaron mesetas.
- La mejora porcentual varió entre 0 % y 55 %.

Hill Climbing converge rápido, pero la calidad depende de la solución inicial.
Por eso se ejecutan varias soluciones iniciales y se reporta la variabilidad.

### 7.4 Metaheurísticas

| Método | Repeticiones | Mejor | Promedio | Desviación | Peor | Evaluaciones |
|---|---:|---:|---:|---:|---:|---:|
| Recocido simulado | 20 | 66.0 | 66.0 | 0.0 | 66.0 | 11 201 |
| Algoritmo genético | 20 | 66.0 | 66.55 | 2.3974 | 77.0 | 9 060 |

El recocido simulado encontró el mismo costo en las 20 repeticiones. El AG
encontró 66 en 19 de 20 corridas y 77 en una. La desviación del AG es mayor,
lo que sugiere una mayor sensibilidad a la población inicial y a la
recombinación.

### 7.5 Teoría de juegos

La matriz 3×3 del escenario base produce:

- Equilibrio de Nash puro: **(Ruta rápida, Bloqueo de ruta)**.
- Ambos jugadores tienen una estrategia dominante estricta: *Ruta rápida*
  (empresa) y *Bloqueo de ruta* (competidor). Por eso el equilibrio es único y
  se alcanza por dominancia.
- Verificación de Nash: frente a *Bloqueo de ruta*, la empresa obtiene 554.89
  con *Ruta rápida*, 554.15 con *Ruta económica* y 551.70 con *Reserva
  preventiva*; frente a *Ruta rápida*, el competidor obtiene 17.48 con
  *Bloqueo*, 13.37 con *Presión de costos* y 6.13 con *No intervención*.
  Ninguna desviación unilateral mejora el pago (equilibrio estricto) y ninguna
  otra celda mejora a un jugador sin empeorar al otro (eficiente en el sentido
  de Pareto).
- Los pagos son parámetros de diseño y la diferencia entre las estrategias de
  la empresa es pequeña (554.89 frente a 554.15 en la columna *Bloqueo*), por
  lo que el equilibrio es sensible a los pesos de la matriz.

### 7.6 Minimax y alfa-beta

| Método | Valor | Nodos visitados | Nodos podados | Tiempo (mediana) |
|---|---:|---:|---:|---:|
| Sin poda | 17 | 326 | 0 | 0.339 ms |
| Alfa-beta | 17 | 76 | 250 | 0.094 ms |

La poda omite 250 de los 326 nodos (76.69 %), con 28 cortes, y mantiene el
mismo valor y la misma decisión; 76 + 250 = 326. Se verificó la igualdad del
valor y el invariante de conteo con profundidades de 1 a 5. La mejor decisión es atender primero la entrega de mayor
valor.

### 7.7 Planificación final

| Indicador | Valor |
|---|---:|
| Algoritmo de origen | Hill Climbing |
| Costo de ruta base | 66.0 |
| Factor del competidor | 1.2537 |
| Costo de ruta ajustado | 82.7442 |
| Penalización por déficit | 20.0 |
| Costo total integrado | 102.7442 |
| Estrategia de la empresa | Ruta rápida |
| Estrategia del competidor | Bloqueo de ruta |
| Factible sin adquisición | No |

La ruta final es:

```text
Inicio -> Entrega 1 -> Entrega 2 -> Entrega 3 -> Entrega 4 -> Entrega 5 -> Destino
```

El déficit se explica porque el competidor reduce la fracción de recursos
conservada. El sistema no oculta el problema: lo reporta como advertencia y
suma la penalización al costo final.

---

## 8. Análisis y discusión

### 8.1 Comparación de algoritmos

A\* es el único algoritmo que garantiza el mínimo costo entre dos puntos,
gracias a una heurística admisible. Greedy es más rápido en nodos expandidos,
pero puede elegir rutas con costo alto. En un sistema real, Greedy podría
usarse como primera aproximación y A\* como validación.

Hill Climbing es el método más rápido para ordenar entregas, pero su resultado
depende del punto de partida. El recocido simulado y el AG exploran mejor el
espacio de permutaciones. En esta instancia pequeña, los tres métodos
coincidieron en el mejor costo, aunque el AG mostró más variabilidad.

### 8.2 Valor de la integración

La integración no se limita a ejecutar algoritmos en paralelo. Comparte el
escenario, la matriz de costos y las decisiones. El resultado final combina:

- Una ruta óptima o cercana al óptimo.
- Una estrategia de juego.
- Una asignación de recursos.
- Una penalización económica si el competidor reduce insumos.

Esto permite explicar por qué el costo final es mayor que el costo de la ruta
base y qué decisión estratégica lo provoca.

### 8.3 Limitaciones

- La cuadrícula es abstracta y no representa distancias geográficas reales.
- El modelo del competidor es una simplificación académica.
- Minimax crece factorialmente con el número de entregas.
- El recocido (11 201 evaluaciones) y el AG (9 060) no usan el mismo
  presupuesto de evaluaciones, por lo que la comparación de estabilidad es
  indicativa; para una comparación justa habría que igualarlo.
- El reparto voraz de la evaluación aproximada de Minimax es exacto en este
  juego, así que no permite medir el error de una evaluación aproximada.
- Los pesos de la matriz de pagos son parámetros de diseño, no datos de
  mercado.
- La interfaz es local y no incluye autenticación ni despliegue en producción.

---

## 9. Pruebas y validación

Se implementaron 57 pruebas automáticas con Pytest. Las pruebas cubren:

- Validación de escenario: puntos fuera de límites, obstáculos, duplicados,
  nombres repetidos, recursos insuficientes y menos de tres entregas.
- Roundtrip JSON y CSV, incluidos recursos globales, competidor, semilla y
  orden de entregas.
- A\* y Greedy en mapas simples, con costos variables, obstáculos y sin
  solución.
- Hill Climbing: reproducibilidad, no empeoramiento y análisis de mesetas.
- Recocido y AG: reproducibilidad con semilla, historial y evaluaciones; el contador del AG se contrasta con las llamadas reales a la función objetivo; los operadores OX y swap conservan permutaciones válidas.
- Teoría de juegos: matriz 3×3, mejores respuestas, dominancia (por pares y
  sobre todas las estrategias), Nash contrastado por fuerza bruta y un juego
  sin Nash puro.
- Minimax: igualdad con y sin poda en profundidades 1 a 5, invariante
  visitados + podados, un juego pequeño con valor calculado a mano (9, 5, 1 →
  utilidad 5), profundidad limitada y decisión.
- Integración: pipeline completo, ruta válida, obstáculos y efecto del
  competidor.
- API Flask: endpoints principales, errores 400, escenario sin solución y
  exportación.

Resultado:

```text
49 passed
```

Las advertencias de Matplotlib corresponden a la versión de `pyparsing` y no
afectan los resultados.

---

## 10. Conclusiones

1. El sistema cumple el objetivo de integrar cinco técnicas de inteligencia
   artificial sobre un mismo escenario logístico.
2. A\* demuestra ser superior a Greedy en calidad de ruta, mientras que Greedy
   es más económico en nodos expandidos.
3. Hill Climbing es rápido, pero necesita múltiples soluciones iniciales para
   reducir el riesgo de óptimos locales.
4. El recocido simulado fue más estable que el algoritmo genético en la
   instancia evaluada.
5. La teoría de juegos identifica un único equilibrio de Nash puro, estricto
   y eficiente en el sentido de Pareto, alcanzado porque ambos jugadores
   tienen una estrategia dominante estricta.
6. La poda alfa-beta reduce considerablemente el esfuerzo de búsqueda sin
   cambiar la decisión de Minimax.
7. La planificación final muestra que el costo de la ruta no es suficiente:
   el competidor y los recursos modifican la factibilidad y el costo total.
8. Las pruebas automáticas y los experimentos reproducibles aportan evidencia
   verificable sobre el funcionamiento del sistema.

---

## 11. Recomendaciones

- Ampliar el escenario a más entregas para evaluar el crecimiento de Minimax.
- Incorporar más estrategias y pagos configurables en la matriz de juegos.
- Añadir un modo de comparación estadística con intervalos de confianza.
- Permitir guardar y recuperar escenarios desde la interfaz con nombres.
- Explorar técnicas como búsqueda tabú o colonias de hormigas.
- Validar el modelo con datos logísticos reales si se dispone de ellos.

---

## 12. Referencias

1. Russell, S. y Norvig, P. *Artificial Intelligence: A Modern Approach*.
   Pearson, 4.ª edición, 2021.
2. Hart, P. E., Nilsson, N. J. y Raphael, B. “A Formal Basis for the
   Heuristic Determination of Minimum Cost Paths”. *IEEE Transactions on
   Systems Science and Cybernetics*, 1968.
3. Kirkpatrick, S., Gelatt, C. D. y Vecchi, M. P. “Optimization by Simulated
   Annealing”. *Science*, 1983.
4. Goldberg, D. E. *Genetic Algorithms in Search, Optimization, and Machine
   Learning*. Addison-Wesley, 1989.
5. Nash, J. “Equilibrium Points in n-Person Games”. *Proceedings of the
   National Academy of Sciences*, 1950.
6. Knuth, D. E. y Moore, R. W. “An Analysis of Alpha-Beta Pruning”.
   *Artificial Intelligence*, 1975.
7. Documentación oficial de Flask: https://flask.palletsprojects.com/
8. Documentación oficial de Pytest: https://docs.pytest.org/

---

## 13. Anexos

### Anexo A. Comandos de reproducción

```powershell
pip install -r requirements.txt
python -m pytest -q
python experimentos/ejecutar_experimentos.py
python app.py
```

### Anexo B. Archivos generados

```text
experimentos/resultados/
├── resultados_busqueda_local.csv
├── resultados_heuristicas.csv
├── resultados_metaheuristicas.csv
├── resultados_minimax.csv
├── resultados_planificacion_final.csv
├── resultados_teoria_juegos.csv
├── resumen_heuristicas.csv
├── resumen_metaheuristicas.csv
└── parametros_experimento.json

experimentos/graficas/
├── busqueda_local.png
├── comparacion_heuristicas.png
├── comparacion_metaheuristicas.png
├── convergencia_metaheuristicas.png
└── minimax_alfabeta.png
```

### Anexo C. Parámetros principales

| Parámetro | Valor |
|---|---:|
| Semilla global | 42 |
| Soluciones iniciales de Hill Climbing | 10 |
| Temperatura inicial del recocido | 50.0 |
| Temperatura final del recocido | 0.01 |
| Factor de enfriamiento | 0.97 |
| Iteraciones por temperatura | 40 |
| Población del AG | 60 |
| Generaciones del AG | 150 |
| Probabilidad de mutación | 0.15 |
| Probabilidad de cruce | 0.9 |
| Tamaño del torneo | 3 |
| Profundidad máxima de Minimax | 12 |
