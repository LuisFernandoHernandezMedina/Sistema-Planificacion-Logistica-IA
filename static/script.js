/* ============================================================
   Sistema logístico inteligente - lógica de la interfaz
   ============================================================ */

const SVG_NS = "http://www.w3.org/2000/svg";

let escenario = null;
let puntosInteres = [];
let parametrosAplicados = false;
let modoEdicion = "mover";
let puntoSeleccionado = null;
let celdaSeleccionada = null;
let entregaEditando = null;
let ultimaSA = null;
let ultimaGA = null;

/* ------------------------------------------------------------
   Utilidades
   ------------------------------------------------------------ */
function qs(id) { return document.getElementById(id); }

function esc(valor) {
    return String(valor === null || valor === undefined ? "" : valor)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#39;");
}

function num(valor, decimales = 2) {
    if (valor === null || valor === undefined || Number.isNaN(Number(valor))) {
        return "—";
    }
    return Number(valor).toFixed(decimales);
}

function entero(valor) {
    if (valor === null || valor === undefined || Number.isNaN(Number(valor))) {
        return "—";
    }
    return String(Math.round(Number(valor)));
}

function mostrarCarga(texto) {
    qs("texto-cargando").textContent = texto || "Procesando...";
    qs("cargando").classList.remove("oculto");
}

function ocultarCarga() {
    qs("cargando").classList.add("oculto");
}

function mostrarMensaje(id, texto, tipo = "") {
    const elemento = qs(id);
    if (!elemento) return;
    elemento.textContent = texto;
    elemento.className = "mensaje";
    if (tipo === "error") elemento.classList.add("error");
    if (tipo === "ok") elemento.classList.add("ok");
    elemento.classList.remove("oculto");
}

function ocultarMensaje(id) {
    const elemento = qs(id);
    if (elemento) elemento.classList.add("oculto");
}

async function leerRespuesta(respuesta) {
    let datos = null;
    try {
        datos = await respuesta.json();
    } catch (error) {
        datos = null;
    }
    if (!respuesta.ok) {
        let mensaje = "Error del servidor (" + respuesta.status + ").";
        if (datos && datos.detalles) {
            mensaje = Array.isArray(datos.detalles)
                ? datos.detalles.join("\n") : String(datos.detalles);
        } else if (datos && datos.error) {
            mensaje = datos.error;
        }
        throw new Error(mensaje);
    }
    return datos;
}

async function apiGet(url) {
    const respuesta = await fetch(url);
    return leerRespuesta(respuesta);
}

async function apiPost(url, cuerpo) {
    const respuesta = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(cuerpo || {})
    });
    return leerRespuesta(respuesta);
}

function tarjetaMetrica(etiqueta, valor, clase = "") {
    return '<div class="metrica"><span class="etiqueta">' + esc(etiqueta) +
        '</span><span class="valor ' + clase + '">' + esc(valor) + '</span></div>';
}

function dibujarMetricas(contenedor, filas) {
    contenedor.innerHTML = filas.map(f => tarjetaMetrica(f[0], f[1], f[2] || "")).join("");
}

/* ------------------------------------------------------------
   Cuadrícula
   ------------------------------------------------------------ */
function crearSvg(tag, atributos = {}) {
    const elemento = document.createElementNS(SVG_NS, tag);
    Object.keys(atributos).forEach(clave => {
        elemento.setAttribute(clave, atributos[clave]);
    });
    return elemento;
}

function claseCosto(costo) {
    const valor = Number(costo);
    if (valor <= 1.5) return "costo-bajo";
    if (valor <= 2.5) return "costo-medio";
    if (valor <= 3.5) return "costo-alto";
    return "costo-muyalto";
}

function dibujarCuadricula(svg, opciones = {}) {
    if (!escenario || !svg) return;
    const rutas = opciones.rutas || [];
    const interactivo = Boolean(opciones.interactivo);
    const mostrarCostos = opciones.mostrarCostos !== false;
    const filas = escenario.filas;
    const columnas = escenario.columnas;

    svg.innerHTML = "";
    svg.setAttribute("viewBox", "0 0 " + columnas + " " + filas);

    const obstaculos = new Set(
        (escenario.mapa.obstaculos || []).map(o => Number(o[0]) + "," + Number(o[1])));

    for (let y = 0; y < filas; y++) {
        for (let x = 0; x < columnas; x++) {
            const esObstaculo = obstaculos.has(x + "," + y);
            const rect = crearSvg("rect", {
                x: x, y: y, width: 1, height: 1,
                class: "celda " + (esObstaculo ? "celda-obstaculo"
                    : claseCosto(escenario.mapa.costos[y][x]))
            });
            if (interactivo) {
                rect.dataset.x = x;
                rect.dataset.y = y;
                rect.style.cursor = "pointer";
            }
            if (celdaSeleccionada && celdaSeleccionada.x === x &&
                celdaSeleccionada.y === y && interactivo) {
                rect.classList.add("celda-seleccionada");
            }
            svg.appendChild(rect);

            if (esObstaculo) {
                const marca = crearSvg("text", {
                    x: x + 0.5, y: y + 0.55, class: "texto-obstaculo"
                });
                marca.textContent = "×";
                svg.appendChild(marca);
            } else if (mostrarCostos) {
                const texto = crearSvg("text", {
                    x: x + 0.5, y: y + 0.55, class: "texto-costo"
                });
                texto.textContent = Number(escenario.mapa.costos[y][x]).toFixed(
                    Number.isInteger(Number(escenario.mapa.costos[y][x])) ? 0 : 1);
                svg.appendChild(texto);
            }
        }
    }

    rutas.forEach(ruta => {
        if (!ruta || !ruta.puntos || ruta.puntos.length < 2) return;
        const poly = crearSvg("polyline", {
            points: ruta.puntos.map(p => (Number(p[0]) + 0.5) + "," +
                (Number(p[1]) + 0.5)).join(" "),
            stroke: ruta.color || "#2563eb",
            "stroke-width": ruta.ancho || "0.09",
            "stroke-dasharray": ruta.dash || "",
            class: "ruta-linea"
        });
        svg.appendChild(poly);
    });

    puntosInteres.forEach((punto, indice) => {
        const ultimo = puntosInteres.length - 1;
        const tipo = indice === 0 ? "inicio" : (indice === ultimo ? "destino" : "entrega");
        const radio = (indice === 0 || indice === ultimo) ? 0.30 : 0.25;
        const circulo = crearSvg("circle", {
            cx: Number(punto.x) + 0.5,
            cy: Number(punto.y) + 0.5,
            r: radio,
            class: "punto-" + tipo +
                (interactivo && puntoSeleccionado === indice ? " punto-seleccionado" : "")
        });
        if (interactivo) {
            circulo.dataset.punto = indice;
            circulo.style.cursor = "pointer";
        }
        svg.appendChild(circulo);

        const etiqueta = crearSvg("text", {
            x: Number(punto.x) + 0.5,
            y: Number(punto.y) + 0.05,
            class: "punto-etiqueta"
        });
        const nombre = String(punto.nombre || "").trim();
        etiqueta.textContent = nombre.length > 10 ? nombre.slice(0, 9) + "…" : nombre;
        svg.appendChild(etiqueta);
    });
}

/* ------------------------------------------------------------
   Estado del escenario
   ------------------------------------------------------------ */
function aplicarPayload(datos) {
    escenario = datos.escenario;
    puntosInteres = datos.puntos_interes.map(p => ({
        nombre: p.nombre, x: Number(p.x), y: Number(p.y)
    }));

    if (puntoSeleccionado !== null && puntoSeleccionado >= puntosInteres.length) {
        puntoSeleccionado = null;
    }
    if (celdaSeleccionada &&
        (celdaSeleccionada.x >= escenario.columnas || celdaSeleccionada.y >= escenario.filas)) {
        celdaSeleccionada = null;
    }

    qs("nombre-escenario").textContent = escenario.nombre;
    const estado = qs("estado-escenario");
    if (datos.validacion && datos.validacion.valido) {
        estado.textContent = "Válido";
        estado.className = "insignia insignia-ok";
        estado.title = "El escenario cumple todas las validaciones.";
    } else {
        estado.textContent = "Con errores";
        estado.className = "insignia insignia-error";
        estado.title = (datos.validacion && datos.validacion.errores || []).join("\n");
    }

    if (!parametrosAplicados && datos.parametros) {
        aplicarParametros(datos.parametros);
        parametrosAplicados = true;
    }

    renderEditor();
    renderRecursos();
    renderCompetidor();
}

function aplicarParametros(parametros) {
    try {
        const local = parametros.busqueda_local || {};
        if (local.soluciones_iniciales) qs("local-iniciales").value = local.soluciones_iniciales;
        if (local.max_iteraciones) qs("local-iteraciones").value = local.max_iteraciones;

        const sa = parametros.recocido_simulado || {};
        if (sa.temperatura_inicial) qs("sa-t0").value = sa.temperatura_inicial;
        if (sa.temperatura_final) qs("sa-tf").value = sa.temperatura_final;
        if (sa.factor_enfriamiento) qs("sa-alpha").value = sa.factor_enfriamiento;
        if (sa.iteraciones_por_temperatura) qs("sa-iter").value = sa.iteraciones_por_temperatura;
        if (parametros.semilla_global) {
            qs("sa-semilla").value = parametros.semilla_global;
            qs("ga-semilla").value = parametros.semilla_global;
            qs("local-semilla").value = parametros.semilla_global;
            qs("exp-semilla").value = parametros.semilla_global;
        }

        const ga = parametros.algoritmo_genetico || {};
        if (ga.tamano_poblacion) qs("ga-pob").value = ga.tamano_poblacion;
        if (ga.generaciones) qs("ga-gen").value = ga.generaciones;
        if (ga.prob_mutacion) qs("ga-mut").value = ga.prob_mutacion;
        if (ga.prob_cruce) qs("ga-cruce").value = ga.prob_cruce;
        if (ga.tamanio_torneo) qs("ga-torneo").value = ga.tamanio_torneo;
    } catch (error) {
        /* La configuración es opcional para la interfaz. */
    }
}

async function cargarEscenario() {
    const datos = await apiGet("/api/escenario");
    aplicarPayload(datos);
}

async function guardarEscenario(invalidar = true) {
    mostrarCarga("Guardando y validando escenario...");
    try {
        const datos = await apiPost("/api/escenario", { escenario: escenario });
        aplicarPayload(datos);
        if (invalidar) invalidarResultados();
        mostrarMensaje("mensajes-escenario",
            "Escenario guardado y validado correctamente.", "ok");
    } catch (error) {
        mostrarMensaje("mensajes-escenario", "Error: " + error.message, "error");
        try { await cargarEscenario(); } catch (e) { /* mantener estado */ }
    } finally {
        ocultarCarga();
    }
}

function invalidarResultados() {
    [
        "resultados-heuristica", "resultados-local", "resultados-sa",
        "resultados-ga", "resultados-juego", "resultados-minimax",
        "resultados-experimentos", "resultados-plan"
    ].forEach(id => {
        const elemento = qs(id);
        if (elemento) elemento.classList.add("oculto");
    });
    ["mensaje-heuristica", "mensaje-local", "mensaje-sa", "mensaje-ga",
        "mensaje-juego", "mensaje-minimax", "mensaje-experimentos",
        "mensaje-plan"].forEach(ocultarMensaje);
    mostrarMensaje("mensajes-escenario",
        "Escenario modificado. Vuelve a ejecutar los módulos para actualizar los resultados.", "");
}

/* ------------------------------------------------------------
   Editor del escenario
   ------------------------------------------------------------ */
function renderEditor() {
    dibujarCuadricula(qs("lienzo-editor"), { interactivo: true });
    renderTablaPuntos();
    actualizarInfoSeleccion();
    if (celdaSeleccionada && modoEdicion === "costo") {
        qs("panel-costo").classList.remove("oculto");
        const costo = escenario.mapa.costos[celdaSeleccionada.y][celdaSeleccionada.x];
        qs("costo-celda").value = costo;
    }
}

function actualizarInfoSeleccion() {
    const elemento = qs("info-seleccion");
    if (puntoSeleccionado === null || !puntosInteres[puntoSeleccionado]) {
        elemento.textContent = "Ningún punto seleccionado.";
        return;
    }
    const punto = puntosInteres[puntoSeleccionado];
    elemento.textContent = "Seleccionado: " + punto.nombre +
        " (" + punto.x + ", " + punto.y + "). Haz clic en una celda libre para moverlo.";
}

function renderTablaPuntos() {
    const cuerpo = qs("tabla-puntos-body");
    cuerpo.innerHTML = "";
    if (!escenario) return;

    puntosInteres.forEach((punto, indice) => {
        const ultimo = puntosInteres.length - 1;
        let tipo = "Entrega";
        let clase = "";
        let demanda = "—";
        let recursos = "—";
        let acciones = "";

        if (indice === 0) {
            tipo = "Inicio";
            clase = "fila-inicio";
        } else if (indice === ultimo) {
            tipo = "Destino";
            clase = "fila-destino";
        } else {
            const entrega = escenario.entregas[indice - 1];
            demanda = entrega.demanda;
            recursos = Object.entries(entrega.recursos || {})
                .map(([k, v]) => k + "=" + v).join(", ") || "—";
        }

        acciones += '<button class="mini-boton" data-seleccionar="' + indice +
            '">Seleccionar</button>';
        if (tipo === "Entrega") {
            acciones += '<button class="mini-boton" data-editar="' + (indice - 1) +
                '">Editar</button>';
            acciones += '<button class="mini-boton peligro" data-eliminar="' +
                (indice - 1) + '">Eliminar</button>';
        }

        const fila = document.createElement("tr");
        fila.className = clase;
        fila.innerHTML =
            "<td>" + esc(tipo) + "</td>" +
            "<td>" + esc(punto.nombre) + "</td>" +
            "<td>" + entero(punto.x) + "</td>" +
            "<td>" + entero(punto.y) + "</td>" +
            "<td>" + esc(demanda) + "</td>" +
            "<td>" + esc(recursos) + "</td>" +
            "<td class=\"acciones-celda\">" + acciones + "</td>";
        cuerpo.appendChild(fila);
    });

    cuerpo.querySelectorAll("[data-seleccionar]").forEach(boton => {
        boton.addEventListener("click", () => {
            puntoSeleccionado = Number(boton.dataset.seleccionar);
            cambiarModo("mover");
            renderEditor();
        });
    });
    cuerpo.querySelectorAll("[data-editar]").forEach(boton => {
        boton.addEventListener("click", () => abrirModalEntrega(Number(boton.dataset.editar)));
    });
    cuerpo.querySelectorAll("[data-eliminar]").forEach(boton => {
        boton.addEventListener("click", () => eliminarEntrega(Number(boton.dataset.eliminar)));
    });
}

function renderRecursos() {
    const contenedor = qs("recursos-editor");
    contenedor.innerHTML = "";
    if (!escenario) return;
    Object.entries(escenario.recursos || {}).forEach(([clave, valor]) => {
        const label = document.createElement("label");
        label.className = "campo-inline";
        label.innerHTML = "<span>" + esc(clave) + "</span>" +
            '<input type="number" min="0" step="1" data-recurso="' + esc(clave) +
            '" value="' + Number(valor) + '">';
        contenedor.appendChild(label);
    });
}

function renderCompetidor() {
    if (!escenario) return;
    const competidor = escenario.competidor || {};
    qs("comp-nombre").value = competidor.nombre || "";
    qs("comp-efecto").value = competidor.efecto_costo !== undefined
        ? competidor.efecto_costo : 1;
    qs("comp-reduccion").value = competidor.reduccion_recurso !== undefined
        ? competidor.reduccion_recurso : 0.15;
    qs("comp-agresividad").value = competidor.agresividad !== undefined
        ? competidor.agresividad : 0.5;
}

function cambiarModo(nuevoModo) {
    modoEdicion = nuevoModo;
    document.querySelectorAll("[data-modo]").forEach(boton => {
        boton.classList.toggle("activo", boton.dataset.modo === nuevoModo);
        boton.classList.toggle("boton-secundario", boton.dataset.modo !== nuevoModo);
    });
    const panel = qs("panel-costo");
    if (nuevoModo === "costo" && celdaSeleccionada) {
        panel.classList.remove("oculto");
    } else {
        panel.classList.add("oculto");
    }
}

function puntoEnCelda(x, y) {
    return puntosInteres.findIndex(p => Number(p.x) === x && Number(p.y) === y);
}

function celdaEsObstaculo(x, y) {
    return (escenario.mapa.obstaculos || []).some(
        o => Number(o[0]) === x && Number(o[1]) === y);
}

async function moverPunto(indice, x, y) {
    if (x < 0 || y < 0 || x >= escenario.columnas || y >= escenario.filas) {
        alert("La celda está fuera de la cuadrícula.");
        return;
    }
    if (celdaEsObstaculo(x, y)) {
        alert("No se puede colocar un punto sobre un obstáculo.");
        return;
    }
    const ocupante = puntoEnCelda(x, y);
    if (ocupante !== -1 && ocupante !== indice) {
        alert("La celda ya está ocupada por " + puntosInteres[ocupante].nombre + ".");
        return;
    }

    const ultimo = puntosInteres.length - 1;
    if (indice === 0) {
        escenario.inicio = [x, y];
    } else if (indice === ultimo) {
        escenario.destino = [x, y];
    } else {
        escenario.entregas[indice - 1].x = x;
        escenario.entregas[indice - 1].y = y;
    }
    await guardarEscenario(true);
}

async function alternarObstaculo(x, y) {
    if (puntoEnCelda(x, y) !== -1) {
        alert("No puedes convertir en obstáculo una celda ocupada por un punto.");
        return;
    }
    const indice = (escenario.mapa.obstaculos || []).findIndex(
        o => Number(o[0]) === x && Number(o[1]) === y);
    if (indice >= 0) {
        escenario.mapa.obstaculos.splice(indice, 1);
    } else {
        escenario.mapa.obstaculos.push([x, y]);
    }
    await guardarEscenario(true);
}

async function aplicarCosto() {
    if (!celdaSeleccionada) {
        alert("Selecciona una celda en modo edición de costo.");
        return;
    }
    const valor = Number(qs("costo-celda").value);
    if (!Number.isFinite(valor) || valor <= 0) {
        alert("El costo debe ser un número mayor que cero.");
        return;
    }
    if (celdaEsObstaculo(celdaSeleccionada.x, celdaSeleccionada.y)) {
        alert("La celda es un obstáculo; primero elimina el obstáculo.");
        return;
    }
    escenario.mapa.costos[celdaSeleccionada.y][celdaSeleccionada.x] = valor;
    await guardarEscenario(true);
}

function buscarCeldaLibre() {
    for (let y = 0; y < escenario.filas; y++) {
        for (let x = 0; x < escenario.columnas; x++) {
            if (!celdaEsObstaculo(x, y) && puntoEnCelda(x, y) === -1) {
                return [x, y];
            }
        }
    }
    return [0, 0];
}

function abrirModalEntrega(indice) {
    entregaEditando = (indice === null || indice === undefined) ? null : indice;
    qs("entrega-error").classList.add("oculto");
    qs("modal-entrega-titulo").textContent = entregaEditando === null
        ? "Agregar entrega" : "Editar entrega";

    const contenedor = qs("entrega-recursos");
    contenedor.innerHTML = "";
    const claves = Object.keys(escenario.recursos || {});
    const valores = entregaEditando === null
        ? {} : (escenario.entregas[entregaEditando].recursos || {});
    claves.forEach(clave => {
        const label = document.createElement("label");
        label.className = "campo-inline";
        label.innerHTML = "<span>" + esc(clave) + "</span>" +
            '<input type="number" min="0" step="1" class="recurso-entrega" data-recurso="' +
            esc(clave) + '" value="' + Number(valores[clave] || 0) + '">';
        contenedor.appendChild(label);
    });

    const libre = buscarCeldaLibre();
    if (entregaEditando === null) {
        qs("entrega-id").value = "E" + (escenario.entregas.length + 1);
        qs("entrega-nombre").value = "Entrega " + (escenario.entregas.length + 1);
        qs("entrega-x").value = libre[0];
        qs("entrega-y").value = libre[1];
        qs("entrega-demanda").value = 1;
    } else {
        const entrega = escenario.entregas[entregaEditando];
        qs("entrega-id").value = entrega.id;
        qs("entrega-nombre").value = entrega.nombre;
        qs("entrega-x").value = entrega.x;
        qs("entrega-y").value = entrega.y;
        qs("entrega-demanda").value = entrega.demanda;
    }
    qs("modal-entrega").classList.remove("oculto");
    qs("entrega-nombre").focus();
}

function cerrarModalEntrega() {
    qs("modal-entrega").classList.add("oculto");
    entregaEditando = null;
}

async function guardarEntrega() {
    const nombre = qs("entrega-nombre").value.trim();
    const x = parseInt(qs("entrega-x").value, 10);
    const y = parseInt(qs("entrega-y").value, 10);
    const demanda = parseInt(qs("entrega-demanda").value, 10);
    const error = qs("entrega-error");

    const fallar = mensaje => {
        error.textContent = mensaje;
        error.classList.remove("oculto");
    };

    if (!nombre) return fallar("El nombre no puede estar vacío.");
    if (!Number.isInteger(x) || !Number.isInteger(y)) {
        return fallar("X e Y deben ser coordenadas enteras.");
    }
    if (x < 0 || y < 0 || x >= escenario.columnas || y >= escenario.filas) {
        return fallar("La entrega está fuera de la cuadrícula.");
    }
    if (celdaEsObstaculo(x, y)) return fallar("La celda es un obstáculo.");
    if (!Number.isInteger(demanda) || demanda <= 0) {
        return fallar("La demanda debe ser un entero positivo.");
    }

    const indiceExistente = puntoEnCelda(x, y);
    const indiceEntrega = entregaEditando;
    const indicePunto = indiceEntrega === null ? -1 : indiceEntrega + 1;
    if (indiceExistente !== -1 && indiceExistente !== indicePunto) {
        return fallar("La celda ya está ocupada por " + puntosInteres[indiceExistente].nombre + ".");
    }

    const nombreRepetido = escenario.entregas.some((e, i) =>
        e.nombre.toLowerCase() === nombre.toLowerCase() && i !== indiceEntrega);
    if (nombreRepetido) return fallar("Ya existe una entrega con ese nombre.");

    const recursos = {};
    document.querySelectorAll(".recurso-entrega").forEach(input => {
        const valor = Number(input.value || 0);
        if (!Number.isFinite(valor) || valor < 0) {
            throw new Error("Los recursos deben ser números no negativos.");
        }
        recursos[input.dataset.recurso] = valor;
    });

    let id = qs("entrega-id").value.trim();
    if (!id) id = "E" + (escenario.entregas.length + 1);
    if (escenario.entregas.some((e, i) => e.id === id && i !== indiceEntrega)) {
        id = id + "_" + Date.now();
    }

    const nueva = { id: id, nombre: nombre, x: x, y: y, demanda: demanda, recursos: recursos };
    if (indiceEntrega === null) {
        escenario.entregas.push(nueva);
    } else {
        escenario.entregas[indiceEntrega] = nueva;
    }
    cerrarModalEntrega();
    await guardarEscenario(true);
}

async function eliminarEntrega(indice) {
    const entrega = escenario.entregas[indice];
    if (!entrega) return;
    if (!confirm("¿Eliminar la entrega '" + entrega.nombre + "'?")) return;
    escenario.entregas.splice(indice, 1);
    if (puntoSeleccionado !== null && puntoSeleccionado > indice) {
        puntoSeleccionado -= 1;
    }
    await guardarEscenario(true);
}

/* ------------------------------------------------------------
   Eventos del editor
   ------------------------------------------------------------ */
function inicializarEditor() {
    document.querySelectorAll("[data-modo]").forEach(boton => {
        boton.addEventListener("click", () => cambiarModo(boton.dataset.modo));
    });

    qs("lienzo-editor").addEventListener("click", async evento => {
        const objetivo = evento.target;
        const x = Number(objetivo.dataset ? objetivo.dataset.x : NaN);
        const y = Number(objetivo.dataset ? objetivo.dataset.y : NaN);

        if (modoEdicion === "mover") {
            if (objetivo.dataset && objetivo.dataset.punto !== undefined) {
                puntoSeleccionado = Number(objetivo.dataset.punto);
                renderEditor();
                return;
            }
            if (!Number.isInteger(x) || !Number.isInteger(y)) return;
            if (puntoSeleccionado === null) {
                mostrarMensaje("mensajes-escenario",
                    "Primero selecciona un punto en la cuadrícula o en la tabla.", "error");
                return;
            }
            await moverPunto(puntoSeleccionado, x, y);
        } else if (modoEdicion === "obstaculo") {
            if (!Number.isInteger(x) || !Number.isInteger(y)) return;
            await alternarObstaculo(x, y);
        } else if (modoEdicion === "costo") {
            if (!Number.isInteger(x) || !Number.isInteger(y)) return;
            celdaSeleccionada = { x: x, y: y };
            qs("panel-costo").classList.remove("oculto");
            if (celdaEsObstaculo(x, y)) {
                qs("costo-celda").value = "";
                mostrarMensaje("mensajes-escenario",
                    "La celda es un obstáculo. Cambia a modo obstáculo para quitarlo.", "error");
            } else {
                qs("costo-celda").value = escenario.mapa.costos[y][x];
                mostrarMensaje("mensajes-escenario",
                    "Celda seleccionada: (" + x + ", " + y + ").", "");
            }
            renderEditor();
        }
    });

    qs("lienzo-editor").addEventListener("contextmenu", async evento => {
        const objetivo = evento.target;
        if (!objetivo.dataset || objetivo.dataset.punto === undefined) return;
        evento.preventDefault();
        const indice = Number(objetivo.dataset.punto);
        const ultimo = puntosInteres.length - 1;
        if (indice === 0 || indice === ultimo) {
            alert("Inicio y Destino no pueden eliminarse. Puedes moverlos.");
            return;
        }
        await eliminarEntrega(indice - 1);
    });

    qs("btn-agregar-entrega").addEventListener("click", () => abrirModalEntrega(null));
    qs("btn-cancelar-entrega").addEventListener("click", cerrarModalEntrega);
    qs("btn-guardar-entrega").addEventListener("click", async () => {
        try {
            await guardarEntrega();
        } catch (error) {
            qs("entrega-error").textContent = error.message;
            qs("entrega-error").classList.remove("oculto");
        }
    });
    qs("modal-entrega").addEventListener("click", evento => {
        if (evento.target === qs("modal-entrega")) cerrarModalEntrega();
    });

    qs("btn-aplicar-costo").addEventListener("click", aplicarCosto);

    qs("btn-validar").addEventListener("click", async () => {
        try {
            const datos = await apiPost("/api/escenario/validar", { escenario: escenario });
            if (datos.valido) {
                mostrarMensaje("mensajes-escenario", "El escenario es válido.", "ok");
            } else {
                mostrarMensaje("mensajes-escenario",
                    "Errores:\n" + datos.errores.join("\n"), "error");
            }
        } catch (error) {
            mostrarMensaje("mensajes-escenario", error.message, "error");
        }
    });

    qs("btn-guardar").addEventListener("click", () => guardarEscenario(true));

    qs("btn-restablecer").addEventListener("click", async () => {
        if (!confirm("¿Restablecer el escenario original 12x12?")) return;
        mostrarCarga("Restableciendo escenario...");
        try {
            const datos = await apiPost("/api/escenario/restablecer", {});
            puntoSeleccionado = null;
            celdaSeleccionada = null;
            aplicarPayload(datos);
            invalidarResultados();
            mostrarMensaje("mensajes-escenario", "Escenario restablecido.", "ok");
        } catch (error) {
            mostrarMensaje("mensajes-escenario", error.message, "error");
        } finally {
            ocultarCarga();
        }
    });

    qs("btn-cargar").addEventListener("click", async () => {
        const entrada = qs("archivo-escenario");
        if (!entrada.files || !entrada.files.length) {
            mostrarMensaje("mensajes-escenario", "Selecciona un archivo JSON o CSV.", "error");
            return;
        }
        const formulario = new FormData();
        formulario.append("archivo", entrada.files[0]);
        mostrarCarga("Cargando escenario...");
        try {
            const respuesta = await fetch("/api/escenario/cargar", {
                method: "POST", body: formulario
            });
            const datos = await leerRespuesta(respuesta);
            puntoSeleccionado = null;
            celdaSeleccionada = null;
            aplicarPayload(datos);
            invalidarResultados();
            mostrarMensaje("mensajes-escenario",
                "Escenario cargado desde el archivo.", "ok");
            entrada.value = "";
        } catch (error) {
            mostrarMensaje("mensajes-escenario", "Error: " + error.message, "error");
        } finally {
            ocultarCarga();
        }
    });

    qs("btn-guardar-recursos").addEventListener("click", async () => {
        const nuevos = {};
        document.querySelectorAll("#recursos-editor [data-recurso]").forEach(input => {
            nuevos[input.dataset.recurso] = Number(input.value);
        });
        escenario.recursos = nuevos;
        await guardarEscenario(true);
    });

    qs("btn-guardar-competidor").addEventListener("click", async () => {
        escenario.competidor = {
            nombre: qs("comp-nombre").value.trim() || "Competidor",
            efecto_costo: Number(qs("comp-efecto").value) || 1,
            reduccion_recurso: Number(qs("comp-reduccion").value) || 0,
            agresividad: Number(qs("comp-agresividad").value) || 0
        };
        await guardarEscenario(true);
    });
}

/* ------------------------------------------------------------
   Pestañas
   ------------------------------------------------------------ */
function inicializarPestanas() {
    document.querySelectorAll(".tab-boton").forEach(boton => {
        boton.addEventListener("click", () => {
            document.querySelectorAll(".tab-boton").forEach(b => b.classList.remove("activo"));
            document.querySelectorAll(".panel").forEach(p => p.classList.remove("activo"));
            boton.classList.add("activo");
            qs("tab-" + boton.dataset.tab).classList.add("activo");
        });
    });
}

/* ------------------------------------------------------------
   Módulo A: búsqueda heurística
   ------------------------------------------------------------ */
async function ejecutarHeuristica() {
    mostrarCarga("Ejecutando Greedy y A*...");
    try {
        const datos = await apiPost("/api/busqueda_heuristica", {});
        renderHeuristica(datos);
        qs("resultados-heuristica").classList.remove("oculto");
        mostrarMensaje("mensaje-heuristica",
            "Comparación ejecutada sobre la cuadrícula actual.", "ok");
    } catch (error) {
        mostrarMensaje("mensaje-heuristica", "Error: " + error.message, "error");
    } finally {
        ocultarCarga();
    }
}

function renderHeuristica(datos) {
    const greedy = datos.greedy;
    const astar = datos.a_estrella;
    dibujarMetricas(qs("met-heuristica"), [
        ["Costo Greedy", num(greedy.costo), ""],
        ["Costo A*", num(astar.costo), "verde"],
        ["Diferencia A* - Greedy", num(datos.diferencia_costo_a_menos_greedy), ""],
        ["Nodos Greedy", entero(greedy.nodos_expandidos), ""],
        ["Nodos A*", entero(astar.nodos_expandidos), ""],
        ["Tiempo Greedy (ms)", num(greedy.tiempo_ms, 3), ""],
        ["Tiempo A* (ms)", num(astar.tiempo_ms, 3), ""],
        ["A* encontrado", astar.encontrado ? "Sí" : "No", astar.encontrado ? "verde" : "rojo"]
    ]);

    qs("tabla-heuristica").innerHTML = [greedy, astar].map((r, i) => {
        const nombre = i === 0 ? "Greedy" : "A*";
        return "<tr><td>" + nombre + "</td><td>" + num(r.costo) + "</td><td>" +
            entero(r.nodos_expandidos) + "</td><td>" + num(r.tiempo_ms, 3) +
            "</td><td>" + entero(r.longitud) + "</td><td>" +
            (r.encontrado ? "Ruta encontrada" : esc(r.mensaje)) + "</td></tr>";
    }).join("");

    const rutas = [];
    if (greedy.encontrado) {
        rutas.push({ puntos: greedy.camino, color: "#f59e0b", ancho: "0.10",
            dash: "0.18 0.12" });
    }
    if (astar.encontrado) {
        rutas.push({ puntos: astar.camino, color: "#2563eb", ancho: "0.10" });
    }
    dibujarCuadricula(qs("lienzo-heuristica"), { rutas: rutas, mostrarCostos: false });
}

/* ------------------------------------------------------------
   Módulo B: búsqueda local
   ------------------------------------------------------------ */
async function ejecutarLocal() {
    mostrarCarga("Ejecutando Hill Climbing...");
    try {
        const datos = await apiPost("/api/busqueda_local", {
            soluciones_iniciales: Number(qs("local-iniciales").value) || 10,
            max_iteraciones: Number(qs("local-iteraciones").value) || 200,
            semilla: Number(qs("local-semilla").value) || 42
        });
        renderLocal(datos);
        qs("resultados-local").classList.remove("oculto");
        mostrarMensaje("mensaje-local",
            "Hill Climbing ejecutado con " + datos.soluciones_iniciales +
            " soluciones iniciales.", "ok");
    } catch (error) {
        mostrarMensaje("mensaje-local", "Error: " + error.message, "error");
    } finally {
        ocultarCarga();
    }
}

function renderLocal(datos) {
    const analisis = datos.analisis;
    dibujarMetricas(qs("met-local"), [
        ["Mejor costo", num(datos.mejor.costo), "verde"],
        ["Costo promedio", num(analisis.costo_promedio), ""],
        ["Desviación estándar", num(analisis.desviacion_estandar), ""],
        ["Óptimos locales distintos", entero(analisis.optimos_locales_distintos), ""],
        ["Corridas con meseta", entero(analisis.corridas_con_meseta), ""],
        ["Evaluaciones", entero(datos.evaluaciones), ""],
        ["Tiempo total (ms)", num(datos.tiempo_total_ms, 3), ""]
    ]);
    qs("ruta-local").textContent = datos.ruta_mejor || "";
    qs("analisis-local").innerHTML =
        "<p><span class='etiqueta-fuerte'>Interpretación:</span> " +
        "se probaron " + datos.soluciones_iniciales +
        " soluciones iniciales. El mejor costo fue " + num(datos.mejor.costo) +
        ", el peor " + num(analisis.peor_costo) + " y la variabilidad fue " +
        num(analisis.variabilidad_costo) + ".</p>" +
        "<ul>" +
        "<li>Óptimos locales distintos: " + analisis.optimos_locales_distintos +
        " (indica cuántas cuencas de atracción diferentes aparecieron).</li>" +
        "<li>Mesetas: " + analisis.corridas_con_meseta + " corridas (" +
        num(analisis.porcentaje_mesetas) + "%) terminaron con vecinos de igual costo.</li>" +
        "<li>La desviación estándar mide la variabilidad entre soluciones iniciales.</li>" +
        "</ul>";

    qs("tabla-local").innerHTML = datos.ejecuciones.map(e =>
        "<tr><td>" + e.corrida + "</td><td>" + num(e.costo_inicial) + "</td><td>" +
        num(e.costo_final) + "</td><td>" + num(e.mejora) + "</td><td>" +
        entero(e.iteraciones) + "</td><td>" + (e.es_meseta ? "Sí (" +
            e.vecinos_meseta + ")" : "No") + "</td><td>" +
        e.orden.join(" → ") + "</td></tr>").join("");

    dibujarCuadricula(qs("lienzo-local"), {
        rutas: [{
            puntos: datos.ruta_coordenadas || [],
            color: "#16a34a", ancho: "0.12"
        }],
        mostrarCostos: false
    });
}

/* ------------------------------------------------------------
   Módulo C: metaheurísticas
   ------------------------------------------------------------ */
async function ejecutarSA() {
    mostrarCarga("Ejecutando recocido simulado...");
    try {
        const datos = await apiPost("/api/recocido", {
            temperatura_inicial: Number(qs("sa-t0").value) || 50,
            temperatura_final: Number(qs("sa-tf").value) || 0.01,
            factor_enfriamiento: Number(qs("sa-alpha").value) || 0.97,
            iteraciones_por_temperatura: Number(qs("sa-iter").value) || 40,
            semilla: Number(qs("sa-semilla").value) || 42
        });
        ultimaSA = datos;
        renderSA(datos);
        qs("resultados-sa").classList.remove("oculto");
        actualizarComparacionMeta();
        mostrarMensaje("mensaje-sa", "Recocido simulado ejecutado.", "ok");
    } catch (error) {
        mostrarMensaje("mensaje-sa", "Error: " + error.message, "error");
    } finally {
        ocultarCarga();
    }
}

function renderSA(datos) {
    dibujarMetricas(qs("met-sa"), [
        ["Mejor costo", num(datos.mejor_costo), "verde"],
        ["Costo inicial", num(datos.costo_inicial), ""],
        ["Iteraciones", entero(datos.iteraciones), ""],
        ["Evaluaciones", entero(datos.evaluaciones), ""],
        ["Aceptaciones", entero(datos.aceptaciones), ""],
        ["Rechazos", entero(datos.rechazos), ""],
        ["Tiempo (ms)", num(datos.tiempo_ms, 3), ""],
        ["Temperatura final", num(datos.temperatura_final_alcanzada, 5), ""]
    ]);
    qs("ruta-sa").textContent = datos.ruta_mejor || "";
    dibujarConvergencia(qs("grafica-sa"), [
        { nombre: "Mejor costo", color: "#7c3aed", datos: datos.historial_mejor },
        { nombre: "Costo actual", color: "#c4b5fd", datos: datos.historial_actual }
    ], "Convergencia del recocido simulado");
}

async function ejecutarGA() {
    mostrarCarga("Ejecutando algoritmo genético...");
    try {
        const datos = await apiPost("/api/genetico", {
            tamano_poblacion: Number(qs("ga-pob").value) || 60,
            generaciones: Number(qs("ga-gen").value) || 150,
            prob_mutacion: Number(qs("ga-mut").value) || 0.15,
            prob_cruce: Number(qs("ga-cruce").value) || 0.9,
            tamanio_torneo: Number(qs("ga-torneo").value) || 3,
            semilla: Number(qs("ga-semilla").value) || 42
        });
        ultimaGA = datos;
        renderGA(datos);
        qs("resultados-ga").classList.remove("oculto");
        actualizarComparacionMeta();
        mostrarMensaje("mensaje-ga", "Algoritmo genético ejecutado.", "ok");
    } catch (error) {
        mostrarMensaje("mensaje-ga", "Error: " + error.message, "error");
    } finally {
        ocultarCarga();
    }
}

function renderGA(datos) {
    dibujarMetricas(qs("met-ga"), [
        ["Mejor costo", num(datos.mejor_costo), "verde"],
        ["Generaciones", entero(datos.generaciones_ejecutadas), ""],
        ["Evaluaciones", entero(datos.evaluaciones), ""],
        ["Tiempo (ms)", num(datos.tiempo_ms, 3), ""],
        ["Sin mejora (gen.)", entero(datos.generaciones_sin_mejora), ""],
        ["Convergencia prematura", datos.posible_convergencia_prematura ? "Posible" : "No",
            datos.posible_convergencia_prematura ? "rojo" : "verde"]
    ]);
    qs("ruta-ga").textContent = datos.ruta_mejor || "";
    dibujarConvergencia(qs("grafica-ga"), [
        { nombre: "Mejor costo", color: "#2563eb", datos: datos.historial_mejor }
    ], "Convergencia del algoritmo genético");
}

function actualizarComparacionMeta() {
    const filas = [];
    if (ultimaSA) {
        filas.push("<tr><td>Recocido simulado</td><td>" + num(ultimaSA.mejor_costo) +
            "</td><td>" + entero(ultimaSA.evaluaciones) + "</td><td>" +
            num(ultimaSA.tiempo_ms, 3) + "</td><td>" + entero(ultimaSA.iteraciones) +
            "</td></tr>");
    }
    if (ultimaGA) {
        filas.push("<tr><td>Algoritmo genético</td><td>" + num(ultimaGA.mejor_costo) +
            "</td><td>" + entero(ultimaGA.evaluaciones) + "</td><td>" +
            num(ultimaGA.tiempo_ms, 3) + "</td><td>" +
            entero(ultimaGA.generaciones_ejecutadas) + "</td></tr>");
    }
    qs("tabla-meta-body").innerHTML = filas.join("") ||
        '<tr><td colspan="5">Sin ejecuciones todavía.</td></tr>';
    if (ultimaSA && ultimaGA) {
        const diferencia = Math.abs(ultimaSA.mejor_costo - ultimaGA.mejor_costo);
        let texto = "Diferencia absoluta de costo: " + num(diferencia) + ". ";
        if (diferencia < 1e-6) {
            texto += "Ambos métodos alcanzaron el mismo costo en esta ejecución.";
        } else if (ultimaSA.mejor_costo < ultimaGA.mejor_costo) {
            texto += "El recocido obtuvo menor costo en esta ejecución.";
        } else {
            texto += "El algoritmo genético obtuvo menor costo en esta ejecución.";
        }
        qs("mensaje-meta").textContent = texto;
    }
}

/* ------------------------------------------------------------
   Gráficas SVG simples
   ------------------------------------------------------------ */
function dibujarConvergencia(contenedor, series, titulo) {
    contenedor.innerHTML = "";
    if (!series.length || !series.some(s => s.datos && s.datos.length)) return;
    const ancho = 620;
    const alto = 230;
    const margen = { izq: 55, der: 15, arriba: 30, abajo: 35 };
    const todos = series.flatMap(s => s.datos || []);
    const maximo = Math.max(...todos);
    const minimo = Math.min(...todos);
    const rango = Math.max(1e-9, maximo - minimo);
    const maxLen = Math.max(...series.map(s => (s.datos || []).length), 2);

    const svg = crearSvg("svg", {
        viewBox: "0 0 " + ancho + " " + alto,
        style: "width:100%;height:auto;display:block"
    });
    const fondo = crearSvg("rect", {
        x: 0, y: 0, width: ancho, height: alto, fill: "#ffffff"
    });
    svg.appendChild(fondo);

    for (let i = 0; i <= 4; i++) {
        const y = margen.arriba + (alto - margen.arriba - margen.abajo) * i / 4;
        svg.appendChild(crearSvg("line", {
            x1: margen.izq, x2: ancho - margen.der, y1: y, y2: y,
            stroke: "#e2e8f0", "stroke-width": 1
        }));
        const valor = maximo - rango * i / 4;
        const texto = crearSvg("text", {
            x: margen.izq - 8, y: y + 4, "text-anchor": "end",
            "font-size": 11, fill: "#64748b"
        });
        texto.textContent = valor.toFixed(1);
        svg.appendChild(texto);
    }

    series.forEach(serie => {
        const datos = serie.datos || [];
        if (!datos.length) return;
        const puntos = datos.map((v, i) => {
            const x = margen.izq + (ancho - margen.izq - margen.der) * i / (maxLen - 1);
            const y = margen.arriba + (alto - margen.arriba - margen.abajo) *
                (1 - (v - minimo) / rango);
            return x + "," + y;
        }).join(" ");
        svg.appendChild(crearSvg("polyline", {
            points: puntos, fill: "none", stroke: serie.color,
            "stroke-width": 2, "stroke-linejoin": "round"
        }));
    });

    const tituloSvg = crearSvg("text", {
        x: margen.izq, y: 18, "font-size": 13, "font-weight": 700, fill: "#1e293b"
    });
    tituloSvg.textContent = titulo;
    svg.appendChild(tituloSvg);

    const leyenda = series.map(s => s.nombre).join(" · ");
    const textoLeyenda = crearSvg("text", {
        x: ancho - margen.der, y: 18, "text-anchor": "end",
        "font-size": 11, fill: "#64748b"
    });
    textoLeyenda.textContent = leyenda;
    svg.appendChild(textoLeyenda);

    contenedor.appendChild(svg);
}

function dibujarBarras(contenedor, datos, titulo) {
    contenedor.innerHTML = "";
    if (!datos.length) return;
    const ancho = 620;
    const alto = 220;
    const margen = { izq: 150, der: 20, arriba: 30, abajo: 25 };
    const maximo = Math.max(...datos.map(d => d.valor), 1);
    const svg = crearSvg("svg", {
        viewBox: "0 0 " + ancho + " " + alto,
        style: "width:100%;height:auto;display:block"
    });
    svg.appendChild(crearSvg("rect", {
        x: 0, y: 0, width: ancho, height: alto, fill: "#ffffff"
    }));
    const tituloSvg = crearSvg("text", {
        x: margen.izq, y: 18, "font-size": 13, "font-weight": 700, fill: "#1e293b"
    });
    tituloSvg.textContent = titulo || "";
    svg.appendChild(tituloSvg);

    const altoBarra = Math.min(30, (alto - margen.arriba - margen.abajo) / datos.length - 8);
    datos.forEach((d, i) => {
        const y = margen.arriba + i * ((alto - margen.arriba - margen.abajo) / datos.length);
        const anchoBarra = (ancho - margen.izq - margen.der) * d.valor / maximo;
        svg.appendChild(crearSvg("rect", {
            x: margen.izq, y: y, width: Math.max(1, anchoBarra), height: altoBarra,
            fill: d.color || "#2563eb", rx: 4
        }));
        const etiqueta = crearSvg("text", {
            x: margen.izq - 8, y: y + altoBarra / 2 + 4,
            "text-anchor": "end", "font-size": 11, fill: "#334155"
        });
        etiqueta.textContent = d.label;
        svg.appendChild(etiqueta);
        const valor = crearSvg("text", {
            x: margen.izq + anchoBarra + 6, y: y + altoBarra / 2 + 4,
            "font-size": 11, fill: "#1e293b", "font-weight": 700
        });
        valor.textContent = d.valor;
        svg.appendChild(valor);
    });
    contenedor.appendChild(svg);
}

/* ------------------------------------------------------------
   Módulo D: teoría de juegos
   ------------------------------------------------------------ */
async function ejecutarJuego() {
    mostrarCarga("Analizando la matriz de pagos...");
    try {
        const datos = await apiPost("/api/teoria_juegos", {});
        renderJuego(datos);
        qs("resultados-juego").classList.remove("oculto");
        mostrarMensaje("mensaje-juego",
            "Análisis estratégico calculado sobre la matriz de pagos.", "ok");
    } catch (error) {
        mostrarMensaje("mensaje-juego", "Error: " + error.message, "error");
    } finally {
        ocultarCarga();
    }
}

function renderJuego(datos) {
    const nash = datos.equilibrios_nash || [];
    const nashClaves = new Set(nash.map(e => e.fila + "-" + e.columna));
    let html = "<table class=\"tabla-juego\"><thead><tr><th>Empresa \\ Competidor</th>";
    datos.estrategias_competidor.forEach(e => {
        html += "<th>" + esc(e) + "</th>";
    });
    html += "</tr></thead><tbody>";
    datos.estrategias_empresa.forEach((empresa, i) => {
        html += "<tr><th>" + esc(empresa) + "</th>";
        datos.estrategias_competidor.forEach((_, j) => {
            const celda = datos.matriz[i][j];
            const esNash = nashClaves.has(i + "-" + j);
            html += "<td class=\"celda-pago" + (esNash ? " celda-nash" : "") + "\">" +
                "E: " + num(celda.empresa) + "<br>C: " + num(celda.competidor) +
                "<br><small>costo ruta: " + num(celda.costo_ruta) + "</small></td>";
        });
        html += "</tr>";
    });
    html += "</tbody></table>";
    qs("matriz-juego").innerHTML = html;

    const respuestas = datos.mejores_respuestas;
    let analisis = "<h3 class='subtitulo-seccion'>Mejores respuestas de la empresa</h3><ul class='lista-limpia'>";
    respuestas.empresa.forEach(r => {
        analisis += "<li>Si el competidor elige <strong>" + esc(r.competidor) +
            "</strong>, la empresa responde con <strong>" +
            esc(r.mejores_empresa.join(" o ")) + "</strong> (pago máx. " +
            num(r.pago_maximo) + ").</li>";
    });
    analisis += "</ul><h3 class='subtitulo-seccion'>Mejores respuestas del competidor</h3><ul class='lista-limpia'>";
    respuestas.competidor.forEach(r => {
        analisis += "<li>Si la empresa elige <strong>" + esc(r.empresa) +
            "</strong>, el competidor responde con <strong>" +
            esc(r.mejores_competidor.join(" o ")) + "</strong> (pago máx. " +
            num(r.pago_maximo) + ").</li>";
    });
    analisis += "</ul>";

    const dominancia = datos.dominancia;
    analisis += "<h3 class='subtitulo-seccion'>Dominancia</h3>";
    const listaDominancia = [];
    ["empresa", "competidor"].forEach(jugador => {
        const info = dominancia[jugador];
        info.dominantes.forEach(d => {
            listaDominancia.push(esc(d.estrategia) + " domina a " +
                esc(d.domina_a) + (d.estricta ? " (estricta)" : " (débil)"));
        });
    });
    analisis += listaDominancia.length
        ? "<ul class='lista-limpia'>" + listaDominancia.map(t => "<li>" + t + "</li>").join("") + "</ul>"
        : "<p>No se encontraron estrategias dominantes.</p>";

    analisis += "<h3 class='subtitulo-seccion'>Equilibrios de Nash puros</h3>";
    if (nash.length) {
        analisis += "<ul class='lista-limpia'>" + nash.map(e =>
            "<li>(" + esc(e.empresa) + ", " + esc(e.competidor) + ") con pagos (" +
            num(e.pago_empresa) + ", " + num(e.pago_competidor) + ")</li>").join("") + "</ul>";
    } else {
        analisis += "<p><strong>No existe equilibrio de Nash puro</strong> en esta matriz. " +
            "No se fuerza un resultado inexistente.</p>";
    }
    qs("analisis-juego").innerHTML = analisis;
    qs("interpretacion-juego").innerHTML = "<ul class='lista-limpia'>" +
        (datos.interpretacion || []).map(t => "<li>" + esc(t) + "</li>").join("") +
        "</ul>";
}

/* ------------------------------------------------------------
   Módulo E: Minimax
   ------------------------------------------------------------ */
async function ejecutarMinimax() {
    mostrarCarga("Comparando Minimax y poda alfa-beta...");
    try {
        const valor = qs("mm-profundidad").value;
        const cuerpo = {};
        if (valor !== "") cuerpo.profundidad = Number(valor);
        const datos = await apiPost("/api/minimax", cuerpo);
        renderMinimax(datos);
        qs("resultados-minimax").classList.remove("oculto");
        mostrarMensaje("mensaje-minimax",
            "Valor minimax verificado: " +
            (datos.valores_iguales ? "ambos métodos coinciden." :
                "los valores no coinciden, revisar implementación."),
            datos.valores_iguales ? "ok" : "error");
    } catch (error) {
        mostrarMensaje("mensaje-minimax", "Error: " + error.message, "error");
    } finally {
        ocultarCarga();
    }
}

function renderMinimax(datos) {
    const sin = datos.sin_poda;
    const con = datos.con_poda;
    dibujarMetricas(qs("mm-sin"), [
        ["Valor minimax", num(sin.valor_minimax), ""],
        ["Nodos visitados", entero(sin.nodos_visitados), ""],
        ["Nodos podados", entero(sin.nodos_podados), ""],
        ["Profundidad", entero(sin.profundidad_utilizada), ""],
        ["Tiempo (ms)", num(sin.tiempo_ms, 3), ""],
        ["Mejor decisión", sin.mejor_decision || "—", ""],
        ["Evaluación", sin.evaluacion || "—", ""]
    ]);
    dibujarMetricas(qs("mm-con"), [
        ["Valor minimax", num(con.valor_minimax), "verde"],
        ["Nodos visitados", entero(con.nodos_visitados), ""],
        ["Nodos podados", entero(con.nodos_podados), ""],
        ["Profundidad", entero(con.profundidad_utilizada), ""],
        ["Tiempo (ms)", num(con.tiempo_ms, 3), ""],
        ["Mejor decisión", con.mejor_decision || "—", ""],
        ["Evaluación", con.evaluacion || "—", ""]
    ]);

    qs("mm-comparacion").innerHTML =
        "<p><span class='etiqueta-fuerte'>¿Mismo valor minimax?</span> " +
        (datos.valores_iguales ? "Sí. La poda alfa-beta conserva el valor." :
            "No. Hay una discrepancia que debe corregirse.") + "</p>" +
        "<p>Nodos ahorrados: <strong>" + entero(datos.nodos_ahorrados) +
        "</strong> · Porcentaje podado: <strong>" + num(datos.porcentaje_podado) +
        "%</strong>.</p>" +
        "<p>La diferencia de nodos se debe a que alfa-beta descarta ramas que no " +
        "pueden cambiar la decisión del jugador.</p>";

    qs("mm-linea").textContent = "Línea principal: " +
        (con.linea_principal || []).join(" → ") +
        " · MAX asegura: " + (con.contratos_max || []).join(", ") +
        " · MIN niega: " + (con.contratos_min || []).join(", ");

    dibujarBarras(qs("grafica-minimax"), [
        { label: "Minimax", valor: sin.nodos_visitados, color: "#2563eb" },
        { label: "Alfa-beta", valor: con.nodos_visitados, color: "#16a34a" },
        { label: "Podados", valor: con.nodos_podados, color: "#f59e0b" }
    ], "Nodos visitados y podados");
}

/* ------------------------------------------------------------
   Experimentos
   ------------------------------------------------------------ */
async function ejecutarExperimentos() {
    mostrarCarga("Ejecutando experimentos: 20 corridas por metaheurística...");
    try {
        const datos = await apiPost("/api/experimentos", {
            repeticiones: Number(qs("exp-repeticiones").value) || 20,
            semilla: Number(qs("exp-semilla").value) || 42
        });
        renderExperimentos(datos);
        qs("resultados-experimentos").classList.remove("oculto");
        mostrarMensaje("mensaje-experimentos",
            "Experimentos finalizados. CSV y gráficas guardados en experimentos/.", "ok");
        await cargarArchivosExperimentos();
    } catch (error) {
        mostrarMensaje("mensaje-experimentos", "Error: " + error.message, "error");
    } finally {
        ocultarCarga();
    }
}

function renderExperimentos(datos) {
    const resumen = [];
    resumen.push("<h3 class='subtitulo-seccion'>Búsqueda heurística en tres escenarios</h3>");
    resumen.push("<div class='tabla-contenedor'><table class='tabla-datos'>" +
        "<thead><tr><th>Escenario</th><th>Costo Greedy</th><th>Costo A*</th>" +
        "<th>Nodos Greedy</th><th>Nodos A*</th><th>Diferencia</th></tr></thead><tbody>");
    datos.heuristicas.forEach(h => {
        resumen.push("<tr><td>" + esc(h.escenario) + "</td><td>" + num(h.costo_greedy) +
            "</td><td>" + num(h.costo_astar) + "</td><td>" + entero(h.nodos_greedy) +
            "</td><td>" + entero(h.nodos_astar) + "</td><td>" +
            num(h.diferencia_costo) + "</td></tr>");
    });
    resumen.push("</tbody></table></div>");

    const local = datos.busqueda_local;
    resumen.push("<h3 class='subtitulo-seccion'>Hill Climbing</h3>");
    resumen.push("<div class='rejilla-tarjetas'>" +
        tarjetaMetrica("Mejor costo", num(local.mejor.costo), "verde") +
        tarjetaMetrica("Costo promedio", num(local.analisis.costo_promedio)) +
        tarjetaMetrica("Desv. estándar", num(local.analisis.desviacion_estandar)) +
        tarjetaMetrica("Óptimos distintos", entero(local.analisis.optimos_locales_distintos)) +
        tarjetaMetrica("Mesetas", entero(local.analisis.corridas_con_meseta)) +
        tarjetaMetrica("Evaluaciones", entero(local.evaluaciones)) +
        "</div>");

    resumen.push("<h3 class='subtitulo-seccion'>Metaheurísticas (20 ejecuciones)</h3>");
    resumen.push("<div class='tabla-contenedor'><table class='tabla-datos'>" +
        "<thead><tr><th>Método</th><th>Mejor costo</th><th>Promedio</th>" +
        "<th>Desv. estándar</th><th>Peor</th><th>Evaluaciones prom.</th>" +
        "<th>Tiempo prom. (ms)</th></tr></thead><tbody>");
    [["Recocido simulado", datos.recocido_simulado],
        ["Algoritmo genético", datos.algoritmo_genetico]].forEach(([nombre, r]) => {
        resumen.push("<tr><td>" + nombre + "</td><td>" + num(r.mejor_costo) +
            "</td><td>" + num(r.costo_promedio) + "</td><td>" +
            num(r.desviacion_estandar) + "</td><td>" + num(r.peor_costo) +
            "</td><td>" + num(r.evaluaciones_promedio, 1) + "</td><td>" +
            num(r.tiempo_promedio_ms, 3) + "</td></tr>");
    });
    resumen.push("</tbody></table></div>");

    const mm = datos.minimax;
    resumen.push("<h3 class='subtitulo-seccion'>Minimax vs alfa-beta</h3>");
    resumen.push("<p>Valores iguales: <strong>" +
        (mm.valores_iguales ? "Sí" : "No") + "</strong>. Nodos sin poda: " +
        entero(mm.sin_poda.nodos_visitados) + ", con poda: " +
        entero(mm.con_poda.nodos_visitados) + ", podados: " +
        entero(mm.con_poda.nodos_podados) + ".</p>");

    const plan = datos.planificacion_final;
    resumen.push("<h3 class='subtitulo-seccion'>Planificación final</h3>");
    resumen.push("<p>Origen del mejor orden: <strong>" + esc(plan.algoritmo_origen) +
        "</strong> · Costo total integrado: <strong>" +
        num(plan.costo_total_integrado) + "</strong> · Estrategia empresa: <strong>" +
        esc(plan.estrategia_empresa) + "</strong> · Estrategia competidor: <strong>" +
        esc(plan.estrategia_competidor) + "</strong>.</p>");
    resumen.push("<p class='ruta-texto'>" + esc(plan.ruta_nombres.join(" → ")) + "</p>");

    qs("resumen-experimentos").innerHTML = resumen.join("");

    const graficas = datos.graficas_base64 || {};
    qs("graficas-experimentos").innerHTML = Object.entries(graficas).map(([nombre, base64]) =>
        "<div><img src='data:image/png;base64," + base64 + "' alt='" +
        esc(nombre) + "'><p class='ayuda'>" + esc(nombre) + "</p></div>").join("");
}

async function cargarArchivosExperimentos() {
    try {
        const datos = await apiGet("/api/experimentos/archivos");
        const partes = [];
        partes.push("<h3 class='subtitulo-seccion'>Archivos en experimentos/resultados</h3>");
        partes.push(datos.resultados.length
            ? "<ul class='lista-limpia'>" + datos.resultados.map(a =>
                "<li>" + esc(a.nombre) + " (" + entero(a.bytes) + " bytes)</li>").join("") + "</ul>"
            : "<p>No hay archivos CSV todavía.</p>");
        partes.push("<h3 class='subtitulo-seccion'>Gráficas en experimentos/graficas</h3>");
        partes.push(datos.graficas.length
            ? "<ul class='lista-limpia'>" + datos.graficas.map(a =>
                "<li>" + esc(a.nombre) + " (" + entero(a.bytes) + " bytes)</li>").join("") + "</ul>"
            : "<p>No hay gráficas todavía.</p>");
        qs("archivos-experimentos").innerHTML = partes.join("");
    } catch (error) {
        qs("archivos-experimentos").innerHTML =
            "<p class='mensaje error'>No se pudieron listar los archivos: " +
            esc(error.message) + "</p>";
    }
}

/* ------------------------------------------------------------
   Integración final
   ------------------------------------------------------------ */
async function ejecutarPlan() {
    mostrarCarga("Ejecutando integración completa de los cinco módulos...");
    try {
        const datos = await apiPost("/api/integracion", {});
        renderPlan(datos);
        qs("resultados-plan").classList.remove("oculto");
        mostrarMensaje("mensaje-plan",
            "Planificación integrada calculada correctamente.", "ok");
    } catch (error) {
        mostrarMensaje("mensaje-plan", "Error: " + error.message, "error");
    } finally {
        ocultarCarga();
    }
}

function renderPlan(datos) {
    const plan = datos.planificacion_final;
    dibujarMetricas(qs("resumen-plan"), [
        ["Costo total integrado", num(plan.costo_total_integrado), "verde"],
        ["Costo ruta base", num(plan.costo_ruta_base), ""],
        ["Factor competidor", num(plan.factor_competidor, 4), ""],
        ["Penalización recursos", num(plan.penalizacion_recursos), ""],
        ["Algoritmo origen", plan.algoritmo_origen, ""],
        ["Estrategia empresa", plan.estrategia_empresa, ""],
        ["Estrategia competidor", plan.estrategia_competidor, ""],
        ["Factible sin adquisición", plan.factible_sin_adquisicion ? "Sí" : "No",
            plan.factible_sin_adquisicion ? "verde" : "rojo"]
    ]);
    qs("ruta-plan").textContent = plan.ruta_nombres.join(" → ");

    const avisos = plan.advertencias || [];
    qs("avisos-plan").innerHTML = avisos.length
        ? "<div class='mensaje error'>" + avisos.map(esc).join("<br>") + "</div>"
        : "<div class='mensaje ok'>No hay advertencias: la planificación es factible con los recursos asignados.</div>";

    dibujarCuadricula(qs("lienzo-plan"), {
        rutas: [{ puntos: plan.ruta_coordenadas, color: "#7c3aed", ancho: "0.13" }],
        mostrarCostos: false
    });

    qs("tabla-plan-metodos").innerHTML = datos.modulo_c_metaheuristicas.comparacion.map(m =>
        "<tr><td>" + esc(m.metodo) + "</td><td>" + num(m.costo) + "</td><td>" +
        entero(m.evaluaciones) + "</td><td>" + num(m.tiempo_ms, 3) + "</td><td>" +
        (m.mejor ? "Sí" : "") + "</td></tr>").join("") +
        "<tr><td>Mejor orden integrado</td><td>" + num(plan.costo_ruta_base) +
        "</td><td>—</td><td>—</td><td>Seleccionado</td></tr>";

    const detalle = plan.asignacion_recursos.detalle || {};
    const filas = Object.entries(detalle).map(([clave, d]) =>
        "<tr><td>" + esc(clave) + "</td><td>" + num(d.disponible_base) +
        "</td><td>" + num(d.fraccion_conservada, 4) + "</td><td>" +
        num(d.disponible_efectivo) + "</td><td>" + num(d.requerido) +
        "</td><td>" + num(d.deficit) + "</td><td>" +
        num(d.costo_por_deficit) + "</td></tr>").join("");
    qs("recursos-plan").innerHTML =
        "<p><span class='etiqueta-fuerte'>Fracción de recursos conservada:</span> " +
        num(plan.asignacion_recursos.fraccion_recursos_conservada, 4) +
        " · <span class='etiqueta-fuerte'>Déficit total:</span> " +
        num(plan.asignacion_recursos.deficit_total) + "</p>" +
        "<div class='tabla-contenedor'><table class='tabla-datos'><thead><tr>" +
        "<th>Recurso</th><th>Disponible base</th><th>Fracción</th>" +
        "<th>Disponible efectivo</th><th>Requerido</th><th>Déficit</th>" +
        "<th>Costo déficit</th></tr></thead><tbody>" + filas +
        "</tbody></table></div>" +
        "<p class='ayuda' style='margin-top:0.7rem'>Minimax/alfa-beta: " +
        (datos.modulo_e_minimax.valores_iguales ? "valores coincidentes" :
            "discrepancia detectada") + ". La fracción conservada se deriva del " +
        "valor minimax de los contratos de acceso a entregas.</p>";
}

/* ------------------------------------------------------------
   Inicialización
   ------------------------------------------------------------ */
async function iniciar() {
    inicializarPestanas();
    inicializarEditor();

    qs("btn-heuristica").addEventListener("click", ejecutarHeuristica);
    qs("btn-local").addEventListener("click", ejecutarLocal);
    qs("btn-sa").addEventListener("click", ejecutarSA);
    qs("btn-ga").addEventListener("click", ejecutarGA);
    qs("btn-juego").addEventListener("click", ejecutarJuego);
    qs("btn-minimax").addEventListener("click", ejecutarMinimax);
    qs("btn-experimentos").addEventListener("click", ejecutarExperimentos);
    qs("btn-actualizar-archivos").addEventListener("click", cargarArchivosExperimentos);
    qs("btn-plan").addEventListener("click", ejecutarPlan);

    try {
        await cargarEscenario();
        await cargarArchivosExperimentos();
    } catch (error) {
        alert("No se pudo cargar el escenario inicial: " + error.message);
    }
}

document.addEventListener("DOMContentLoaded", iniciar);
