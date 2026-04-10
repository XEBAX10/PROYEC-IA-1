#!/usr/bin/env python3
"""
Escape Room Solver — Búsqueda Híbrida
======================================
Nivel global  : BFS  (búsqueda no informada por amplitud)
Nivel local   : A*   (búsqueda informada con heurística admisible)

Grafo global (DAG):
    A ──► B ──► C* ──► I ──► L ──┐
    A ──► E ──► C*               ├──► M  (meta)
          E ──► G ──► I          │
               G ──► K* ─────────┘
          H ──► J ──► K*        (* = nodo bloqueado)

Puzzle C: sub-grafo con costos, resuelto por A*
Puzzle K: sub-grafo con costos, resuelto por A*
"""

import tkinter as tk
import heapq
import time
from collections import deque

# ═══════════════════════════════════════════════════════════════
#  CONSTANTES VISUALES
# ═══════════════════════════════════════════════════════════════

# Paleta de colores
C = {
    "available": "#4a9eff",   # nodo disponible
    "locked":    "#778899",   # nodo bloqueado
    "solved":    "#ff8c00",   # nodo desbloqueado (puzzle resuelto)
    "current":   "#ff3333",   # nodo siendo expandido ahora
    "expanded":  "#ffd700",   # nodo ya expandido
    "start":     "#00cc55",   # nodo inicial
    "goal":      "#cc2200",   # nodo meta
    "path":      "#00ffaa",   # nodo en la ruta solución
    "bg":        "#1a1a2e",
    "panel":     "#16213e",
    "text":      "#e0e0e0",
    "edge":      "#445566",
    "edge_hi":   "#88ffcc",
    "console_bg":"#0d2137",
    "accent":    "#aaaaff",
}

NODE_R   = 22    # radio del nodo en canvas (px)
ANIM_MS  = 700   # delay por defecto entre pasos (ms)

# Posiciones (x, y) de cada nodo en el canvas global
GPOS = {
    "A": ( 75, 215),
    "B": (190, 115),
    "C": (315, 115),
    "E": (190, 315),
    "G": (315, 265),
    "H": (110, 395),
    "I": (435, 165),
    "J": (300, 395),
    "K": (435, 315),
    "L": (555, 165),
    "M": (555, 315),
}

# ═══════════════════════════════════════════════════════════════
#  MODELO: GRAFOS
# ═══════════════════════════════════════════════════════════════

class GlobalGraph:
    """
    Grafo Dirigido Acíclico (DAG) que representa el escape room.

    Atributos:
        nodes   : dict[str, str]  — nombre → estado ('available'|'locked'|'solved')
        edges   : dict[str, list] — nombre → [(vecino, costo)]
        puzzles : dict[str, PuzzleGraph] — nodo_bloqueado → puzzle asociado
    """

    def __init__(self):
        self.nodes   = {}
        self.edges   = {}
        self.puzzles = {}

    def add_node(self, name, locked=False):
        self.nodes[name] = "locked" if locked else "available"
        self.edges[name] = []

    def add_edge(self, src, dst, cost=1):
        self.edges[src].append((dst, cost))

    def attach_puzzle(self, node_name, puzzle):
        self.puzzles[node_name] = puzzle

    def is_locked(self, name):
        return self.nodes[name] == "locked"

    def unlock(self, name):
        """Desbloquea el nodo permanentemente (para todas las rutas futuras)."""
        self.nodes[name] = "solved"

    def neighbors(self, name):
        return self.edges.get(name, [])




class PuzzleGraph:
    """
    Sub-grafo ponderado independiente asociado a un nodo bloqueado.
    Resuelto por A* con una heurística admisible.

    La heurística h(n) se define manualmente por nodo y representa
    una estimación del costo mínimo restante hasta la meta del puzzle.
    Es admisible porque nunca sobreestima el costo real.

    Atributos:
        label   : str            — nombre descriptivo del puzzle
        start   : str            — nodo inicio del puzzle
        goal    : str            — nodo meta del puzzle
        nodes   : dict[str,(x,y)]— posiciones canvas para visualización
        edges   : dict[str, list]— nombre → [(vecino, costo)]
        h_vals  : dict[str, int] — heurística por nodo (admisible)
    """

    def __init__(self, label, start, goal):
        self.label  = label
        self.start  = start
        self.goal   = goal
        self.nodes  = {}
        self.edges  = {}
        self.h_vals = {}

    def add_node(self, name, pos, h=0):
        self.nodes[name]  = pos
        self.edges[name]  = []
        self.h_vals[name] = h

    def add_edge(self, src, dst, cost):
        self.edges[src].append((dst, cost))

    def h(self, name):
        """Heurística admisible h(n): estimación del costo restante a la meta."""
        return self.h_vals.get(name, 0)

# ═══════════════════════════════════════════════════════════════
#  ALGORITMOS DE BÚSQUEDA
# ═══════════════════════════════════════════════════════════════

def run_astar(puzzle):
    """
    Búsqueda A* sobre un PuzzleGraph.

    Función de evaluación:  f(n) = g(n) + h(n)
        g(n) : costo acumulado desde el inicio hasta n
        h(n) : heurística admisible — estimación del costo restante hasta la meta
               (admisible = nunca sobreestima → garantiza optimalidad)

    Implementación:
        - Cola de prioridad (min-heap) ordenada por f(n)
        - Conjunto cerrado (closed set) para evitar re-expansión
        - Desempate por contador para estabilidad

    Retorna:
        steps   : list[dict] — eventos paso a paso para la GUI
        metrics : dict       — métricas finales
    """
    steps = []
    t0    = time.perf_counter()
    tie   = 0  # desempate en el heap

    # Entrada del heap: (f, tie, g, nodo, camino)
    heap = []
    heapq.heappush(heap, (puzzle.h(puzzle.start), tie, 0, puzzle.start, [puzzle.start]))
    closed = set()

    while heap:
        f, _, g, cur, path = heapq.heappop(heap)

        if cur in closed:
            continue
        closed.add(cur)

        h_val = puzzle.h(cur)
        steps.append({
            "type": "expand",
            "node": cur,
            "path": list(path),
            "g": g, "h": h_val, "f": f,
            "msg": f"> Expandiendo nodo {cur}  [g={g}  h={h_val}  f={f}]"
        })

        if cur == puzzle.goal:
            elapsed = time.perf_counter() - t0
            steps.append({
                "type": "solved",
                "node": cur,
                "path": list(path),
                "msg": f"-- Puzzle resuelto!  Costo optimo={g}  ({elapsed*1000:.1f} ms)"
            })
            return steps, {
                "nodes_expanded": len(closed),
                "total_cost":     g,
                "time":           elapsed,
                "path":           path,
            }

        # Generar sucesores
        for neighbor, cost in puzzle.edges.get(cur, []):
            if neighbor not in closed:
                tie  += 1
                new_g = g + cost
                new_f = new_g + puzzle.h(neighbor)
                heapq.heappush(heap, (new_f, tie, new_g, neighbor, path + [neighbor]))

    elapsed = time.perf_counter() - t0
    return steps, {"nodes_expanded": len(closed), "total_cost": 0, "time": elapsed, "path": []}


def solve_hybrid(graph, start, goal):
    """
    Solver híbrido: BFS global + A* local para nodos bloqueados.

    Lógica de integración:
        1. BFS explora el grafo global con una cola FIFO (por amplitud).
        2. Al encontrar un nodo bloqueado (no visitado aún):
           a. Emite evento 'locked' en el log.
           b. Lanza A* sobre el puzzle de ese nodo.
           c. Los pasos de A* se insertan en el log de eventos.
           d. Se desbloquea el nodo globalmente (para todas las rutas futuras).
        3. BFS continúa desde donde se detuvo.

    BFS garantiza encontrar el camino con menor número de saltos (profundidad mínima)
    porque explora por niveles: primero todos los nodos a distancia 1, luego 2, etc.

    Retorna:
        events  : list[dict] — todos los eventos (globales + locales) en orden
        metrics : dict       — métricas globales y locales
    """
    events     = []
    g_expanded = 0
    l_expanded = 0
    l_cost     = 0
    l_time     = 0.0
    t0         = time.perf_counter()

    # Cola BFS: cada elemento es el camino completo hasta el nodo actual
    queue    = deque([[start]])
    visited  = {start}
    unlocked = set()   # nodos ya desbloqueados (no requieren puzzle de nuevo)
    final_path = []

    while queue:
        path = queue.popleft()
        cur  = path[-1]
        g_expanded += 1
        depth = len(path) - 1

        events.append({
            "phase": "global", "type": "expand",
            "node": cur, "path": list(path), "depth": depth,
            "msg": f"> Expandiendo nodo {cur}"
        })

        if cur == goal:
            final_path = path
            events.append({
                "phase": "global", "type": "goal",
                "node": cur, "path": list(path),
                "msg": f"[OK] Meta alcanzada: {goal}!   Ruta: {' -> '.join(path)}"
            })
            break

        # Expandir vecinos
        for nb, _ in graph.neighbors(cur):
            if nb in visited:
                continue

            if graph.is_locked(nb) and nb not in unlocked:
                # ── Nodo bloqueado: activar A* ──────────────────
                events.append({
                    "phase": "global", "type": "locked",
                    "node": nb, "path": list(path),
                    "msg": f"> Nodo bloqueado encontrado: {nb}"
                })
                events.append({
                    "phase": "global", "type": "puzzle_start",
                    "node": nb, "path": list(path),
                    "msg": f"— Iniciando búsqueda informada (A*) para Puzzle en nodo {nb}"
                })

                puzzle = graph.puzzles.get(nb)
                if puzzle:
                    p_steps, p_met = run_astar(puzzle)
                    # Insertar todos los pasos del puzzle en el log global
                    for ps in p_steps:
                        events.append({
                            "phase":       "local",
                            "puzzle_node": nb,
                            "puzzle":      puzzle,
                            **ps
                        })
                    l_expanded += p_met["nodes_expanded"]
                    l_cost     += p_met["total_cost"]
                    l_time     += p_met["time"]

                # Desbloquear permanentemente
                graph.unlock(nb)
                unlocked.add(nb)

            visited.add(nb)
            queue.append(path + [nb])

    g_time  = time.perf_counter() - t0
    metrics = {
        "global": {
            "nodes_expanded": g_expanded,
            "depth":          len(final_path) - 1 if final_path else 0,
            "cost":           len(final_path) - 1 if final_path else 0,
            "time":           g_time,
        },
        "local": {
            "nodes_expanded": l_expanded,
            "total_cost":     l_cost,
            "time":           l_time,
        },
        "path": final_path,
    }
    return events, metrics

# ═══════════════════════════════════════════════════════════════
#  DEFINICIÓN DEL MUNDO
# ═══════════════════════════════════════════════════════════════

def build_world():
    """
    Construye el grafo global y los puzzles asociados a nodos bloqueados.

    ── Grafo Global ─────────────────────────────────────────────
    Nodos: A B C E G H I J K L M
    Nodos bloqueados: C, K (requieren resolver un puzzle para desbloquearse)
    Nodo inicio: A   |   Nodo meta: M

    ── Puzzle C ─────────────────────────────────────────────────
    Sub-grafo ponderado con nodos S, X1, X2, X3, G.
    Heurística h(n): costo mínimo restante estimado (admisible).

    Rutas posibles:
        S→X1→G     costo = 7+3 = 10
        S→X2→G     costo = 2+4 = 6
        S→X2→X3→G  costo = 2+1+2 = 5  ← óptima (A* la encontrará)

    A* elige S→X2→X3→G porque f(X2)=2+3=5 < f(X1)=7+3=10

    ── Puzzle K ─────────────────────────────────────────────────
    Sub-grafo ponderado con nodos S, Y1, Y2, Y3, G.

    Rutas posibles:
        S→Y1→Y3→G  costo = 3+2+1 = 6  ← óptima
        S→Y2→G     costo = 5+4 = 9
    """
    g = GlobalGraph()

    # ── Nodos globales ──────────────────────────────────────────
    for name in "A B C E G H I J K L M".split():
        g.add_node(name, locked=(name in ("C", "K")))

    # ── Aristas globales ────────────────────────────────────────
    for src, dst in [
        ("A", "B"), ("A", "E"),
        ("B", "C"), ("E", "C"), ("E", "G"),
        ("C", "I"), ("G", "I"), ("G", "K"),
        ("H", "J"), ("J", "K"),
        ("I", "L"), ("K", "M"), ("L", "M"),
    ]:
        g.add_edge(src, dst)

    # ── Puzzle para el nodo C ───────────────────────────────────
    # h(n): estimación admisible del costo mínimo restante a G
    #   h(S)=5 porque el camino óptimo S→X2→X3→G tiene costo 5
    #   h(X1)=3, h(X2)=3, h(X3)=2, h(G)=0
    pC = PuzzleGraph("Puzzle C", start="S", goal="G")
    pC.add_node("S",  pos=(55, 135), h=5)
    pC.add_node("X1", pos=(165, 60), h=3)
    pC.add_node("X2", pos=(165, 205), h=3)
    pC.add_node("X3", pos=(275, 205), h=2)
    pC.add_node("G",  pos=(375, 135), h=0)
    pC.add_edge("S",  "X1", 7)
    pC.add_edge("S",  "X2", 2)
    pC.add_edge("X1", "G",  3)
    pC.add_edge("X2", "G",  4)
    pC.add_edge("X2", "X3", 1)
    pC.add_edge("X3", "G",  2)
    g.attach_puzzle("C", pC)

    # ── Puzzle para el nodo K ───────────────────────────────────
    # Camino óptimo: S→Y1→Y3→G con costo 6
    pK = PuzzleGraph("Puzzle K", start="S", goal="G")
    pK.add_node("S",  pos=(55, 135), h=6)
    pK.add_node("Y1", pos=(165, 65),  h=3)
    pK.add_node("Y2", pos=(165, 205), h=4)
    pK.add_node("Y3", pos=(275, 65),  h=1)
    pK.add_node("G",  pos=(375, 135), h=0)
    pK.add_edge("S",  "Y1", 3)
    pK.add_edge("S",  "Y2", 5)
    pK.add_edge("Y1", "Y3", 2)
    pK.add_edge("Y2", "G",  4)
    pK.add_edge("Y3", "G",  1)
    g.attach_puzzle("K", pK)

    return g

# ═══════════════════════════════════════════════════════════════
#  INTERFAZ GRÁFICA (TKINTER)
# ═══════════════════════════════════════════════════════════════

class App(tk.Tk):
    """
    Aplicación principal.

    Layout:
        ┌─────────────────────────┬──────────────────────┐
        │   Canvas Global (BFS)   │  Canvas Puzzle (A*)  │
        │                         │  + Estadísticas      │
        ├─────────────────────────┼──────────────────────┤
        │   Log Búsqueda Global   │  Log Puzzle Solver   │
        └─────────────────────────┴──────────────────────┘
    """

    def __init__(self):
        super().__init__()
        self.title("Escape Room Solver — BFS + A*")
        self.configure(bg=C["bg"])
        self.minsize(1120, 720)

        # Construir mundo y ejecutar el solver (pre-computa todos los eventos)
        self.world  = build_world()
        self.events, self.metrics = solve_hybrid(self.world, "A", "M")

        # Estado visual de cada nodo (independiente del estado interno del solver)
        self.vstate = {}
        for n in self.world.nodes:
            self.vstate[n] = "locked" if n in ("C", "K") else "available"

        # Estado de la animación
        self.ev_idx        = 0
        self.delay         = ANIM_MS
        self.cur_puzzle    = None       # puzzle activo en el canvas derecho
        self.puz_expanded  = set()     # nodos expandidos del puzzle actual
        self.puz_path      = []        # camino solución del puzzle actual
        self.puz_current   = None      # nodo actual del puzzle
        self.running       = False

        self._build_ui()
        self._draw_global()
        self._draw_puzzle_placeholder()

    # ── Construcción de la UI ────────────────────────────────────

    def _build_ui(self):
        self.columnconfigure(0, weight=3)
        self.columnconfigure(1, weight=2)
        self.rowconfigure(0, weight=3)
        self.rowconfigure(1, weight=2)

        # ── Panel superior izquierdo: grafo global ───────────────
        lf = tk.Frame(self, bg=C["panel"])
        lf.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

        hdr_l = tk.Frame(lf, bg=C["panel"])
        hdr_l.pack(fill="x", padx=6, pady=(6, 2))
        tk.Label(hdr_l, text="Grafo Global — Búsqueda No Informada (BFS)",
                 bg=C["panel"], fg=C["accent"],
                 font=("Consolas", 11, "bold")).pack(side="left")

        self.gcanvas = tk.Canvas(lf, bg=C["bg"], highlightthickness=0)
        self.gcanvas.pack(fill="both", expand=True, padx=4, pady=2)

        self._build_legend(lf)
        self._build_controls(lf)

        # ── Panel superior derecho: puzzle solver ────────────────
        rf = tk.Frame(self, bg=C["panel"])
        rf.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)

        self.right_title = tk.Label(
            rf, text="Puzzle Solver — Búsqueda Informada (A*)",
            bg=C["panel"], fg=C["accent"],
            font=("Consolas", 11, "bold"))
        self.right_title.pack(anchor="w", padx=8, pady=(6, 2))

        self.pcanvas = tk.Canvas(rf, bg=C["bg"], highlightthickness=0)
        self.pcanvas.pack(fill="both", expand=True, padx=4, pady=2)

        self._build_stats(rf)

        # ── Panel inferior izquierdo: log global ─────────────────
        blf = tk.Frame(self, bg=C["panel"])
        blf.grid(row=1, column=0, sticky="nsew", padx=5, pady=(0, 5))
        tk.Label(blf, text="Log — Búsqueda Global (BFS)",
                 bg=C["panel"], fg=C["accent"],
                 font=("Consolas", 9, "bold")).pack(anchor="w", padx=6, pady=(4, 0))

        sb_g = tk.Scrollbar(blf)
        sb_g.pack(side="right", fill="y")
        self.glog = tk.Text(blf, bg=C["console_bg"], fg="#aaffaa",
                            font=("Consolas", 9), state="disabled",
                            wrap="word", height=7, yscrollcommand=sb_g.set)
        self.glog.pack(fill="both", expand=True, padx=(4, 0), pady=4)
        sb_g.config(command=self.glog.yview)

        # ── Panel inferior derecho: log puzzle ───────────────────
        brf = tk.Frame(self, bg=C["panel"])
        brf.grid(row=1, column=1, sticky="nsew", padx=5, pady=(0, 5))
        tk.Label(brf, text="Log — Puzzle Solver (A*)",
                 bg=C["panel"], fg=C["accent"],
                 font=("Consolas", 9, "bold")).pack(anchor="w", padx=6, pady=(4, 0))

        sb_p = tk.Scrollbar(brf)
        sb_p.pack(side="right", fill="y")
        self.plog = tk.Text(brf, bg=C["console_bg"], fg="#ffffaa",
                            font=("Consolas", 9), state="disabled",
                            wrap="word", height=7, yscrollcommand=sb_p.set)
        self.plog.pack(fill="both", expand=True, padx=(4, 0), pady=4)
        sb_p.config(command=self.plog.yview)

    def _build_legend(self, parent):
        f = tk.Frame(parent, bg=C["panel"])
        f.pack(pady=3)
        items = [
            ("start",    "Inicio"),
            ("available","Disponible"),
            ("locked",   "Bloqueado"),
            ("solved",   "Desbloqueado"),
            ("expanded", "Expandido"),
            ("current",  "Actual"),
        ]
        for tag, label in items:
            row = tk.Frame(f, bg=C["panel"])
            row.pack(side="left", padx=5)
            tk.Canvas(row, width=13, height=13, bg=C[tag],
                      highlightthickness=1,
                      highlightbackground="#555577").pack(side="left", padx=2)
            tk.Label(row, text=label, bg=C["panel"],
                     fg=C["text"], font=("Consolas", 8)).pack(side="left")

    def _build_controls(self, parent):
        """Botones de control y slider de velocidad."""
        cf = tk.Frame(parent, bg=C["panel"])
        cf.pack(fill="x", padx=6, pady=4)

        btn_kw = dict(font=("Consolas", 9, "bold"), relief="flat",
                      padx=10, pady=3, cursor="hand2")

        self.btn_start = tk.Button(
            cf, text="[>] Iniciar", bg="#226622", fg="white",
            command=self._start_animation, **btn_kw)
        self.btn_start.pack(side="left", padx=4)

        self.btn_step = tk.Button(
            cf, text="[>>] Paso", bg="#224466", fg="white",
            command=self._step, **btn_kw)
        self.btn_step.pack(side="left", padx=4)

        self.btn_reset = tk.Button(
            cf, text="[R] Reiniciar", bg="#663322", fg="white",
            command=self._reset, **btn_kw)
        self.btn_reset.pack(side="left", padx=4)

        tk.Label(cf, text="Velocidad:", bg=C["panel"],
                 fg=C["text"], font=("Consolas", 9)).pack(side="left", padx=(12, 2))

        self.spd_var = tk.IntVar(value=ANIM_MS)
        tk.Scale(cf, from_=100, to=2000, orient="horizontal",
                 variable=self.spd_var, bg=C["panel"],
                 fg=C["text"], troughcolor="#334455",
                 length=130, showvalue=False,
                 command=lambda v: setattr(self, "delay", int(v))
                 ).pack(side="left")

        tk.Label(cf, text="< Rapido  Lento >",
                 bg=C["panel"], fg="#667799",
                 font=("Consolas", 7)).pack(side="left", padx=4)

    def _build_stats(self, parent):
        """Panel de estadísticas con métricas de ambas búsquedas."""
        sf = tk.Frame(parent, bg=C["panel"])
        sf.pack(fill="x", padx=8, pady=6)

        tk.Label(sf, text="── Estadísticas ──", bg=C["panel"],
                 fg=C["accent"], font=("Consolas", 9, "bold")).grid(
                     row=0, column=0, columnspan=4, pady=(2, 6))

        # Cabeceras
        for col, txt in enumerate(["Búsqueda Global", "", "Puzzle Local", ""]):
            tk.Label(sf, text=txt, bg=C["panel"], fg="#cccccc",
                     font=("Consolas", 8, "bold")).grid(row=1, column=col, padx=6)

        self.sv = {k: tk.StringVar(value="—") for k in
                   ("g_exp", "g_dep", "l_exp", "l_cost", "time")}

        def stat_row(r, ll, lv, rl, rv):
            kw = dict(bg=C["panel"], font=("Consolas", 9))
            tk.Label(sf, text=ll, fg="#cccccc", **kw).grid(row=r, column=0, sticky="e", padx=4)
            tk.Label(sf, textvariable=lv, fg="#00ffaa", **kw).grid(row=r, column=1, sticky="w")
            tk.Label(sf, text=rl, fg="#cccccc", **kw).grid(row=r, column=2, sticky="e", padx=4)
            tk.Label(sf, textvariable=rv, fg="#00ffaa", **kw).grid(row=r, column=3, sticky="w")

        stat_row(2, "Nodos Exp.:", self.sv["g_exp"],
                    "Nodos Exp.:", self.sv["l_exp"])
        stat_row(3, "Profundidad:", self.sv["g_dep"],
                    "Costo Total:", self.sv["l_cost"])

        tk.Label(sf, text="Tiempo Total:", bg=C["panel"],
                 fg="#cccccc", font=("Consolas", 9)).grid(row=4, column=0, sticky="e", padx=4)
        tk.Label(sf, textvariable=self.sv["time"], bg=C["panel"],
                 fg="#ffdd44", font=("Consolas", 9, "bold")).grid(
                     row=4, column=1, columnspan=3, sticky="w")

    # ── Dibujo del grafo global ──────────────────────────────────

    def _node_color(self, name):
        """Determina el color de un nodo según su estado visual actual."""
        vs = self.vstate.get(name, "available")
        if vs == "path":     return C["path"]
        if vs == "current":  return C["current"]
        if vs == "expanded": return C["expanded"]
        if vs == "solved":   return C["solved"]
        if vs == "locked":   return C["locked"]
        if name == "M":      return C["goal"]
        if name == "A":      return C["start"]
        return C["available"]

    def _draw_arrow(self, canvas, x1, y1, x2, y2, color, width=1.5):
        """Dibuja una flecha entre dos puntos, terminando en el borde del nodo destino."""
        dx, dy = x2 - x1, y2 - y1
        dist   = (dx * dx + dy * dy) ** 0.5
        if dist == 0:
            return
        # Retroceder NODE_R px desde el centro destino para llegar al borde
        ex = x2 - (dx / dist) * NODE_R
        ey = y2 - (dy / dist) * NODE_R
        canvas.create_line(x1, y1, ex, ey,
                           fill=color, width=width,
                           arrow="last", arrowshape=(10, 12, 5))

    def _draw_global(self, path_hi=None):
        """Redibuja el canvas del grafo global completo."""
        cv = self.gcanvas
        cv.delete("all")

        path_edges = set()
        if path_hi:
            for i in range(len(path_hi) - 1):
                path_edges.add((path_hi[i], path_hi[i + 1]))

        # Aristas
        for src, neighbors in self.world.edges.items():
            if src not in GPOS:
                continue
            x1, y1 = GPOS[src]
            for dst, _ in neighbors:
                if dst not in GPOS:
                    continue
                x2, y2 = GPOS[dst]
                on     = (src, dst) in path_edges
                self._draw_arrow(cv, x1, y1, x2, y2,
                                 C["edge_hi"] if on else C["edge"],
                                 width=3.0 if on else 1.5)

        # Nodos
        for name, (x, y) in GPOS.items():
            col = self._node_color(name)
            # Anillo extra para la meta
            if name == "M":
                cv.create_oval(x - NODE_R - 7, y - NODE_R - 7,
                               x + NODE_R + 7, y + NODE_R + 7,
                               outline="#ff4444", width=3)
            cv.create_oval(x - NODE_R, y - NODE_R,
                           x + NODE_R, y + NODE_R,
                           fill=col, outline="#cccccc", width=2)
            cv.create_text(x, y, text=name,
                           fill="white", font=("Consolas", 12, "bold"))

    # ── Dibujo del puzzle ────────────────────────────────────────

    def _draw_puzzle_placeholder(self):
        self.pcanvas.delete("all")
        self.pcanvas.create_text(
            200, 130,
            text="Sin puzzle activo",
            fill="#334466", font=("Consolas", 13))

    def _draw_puzzle(self):
        """Redibuja el canvas del puzzle activo con el estado actual de A*."""
        cv = self.pcanvas
        cv.delete("all")
        pz = self.cur_puzzle

        if pz is None:
            self._draw_puzzle_placeholder()
            return

        OX, OY = 40, 30   # offset del canvas

        path_edges = set()
        for i in range(len(self.puz_path) - 1):
            path_edges.add((self.puz_path[i], self.puz_path[i + 1]))

        # Aristas con etiquetas de costo
        for src, neighbors in pz.edges.items():
            if src not in pz.nodes:
                continue
            px1, py1 = pz.nodes[src]
            px1 += OX; py1 += OY
            for dst, cost in neighbors:
                if dst not in pz.nodes:
                    continue
                px2, py2 = pz.nodes[dst]
                px2 += OX; py2 += OY
                on = (src, dst) in path_edges
                self._draw_arrow(cv, px1, py1, px2, py2,
                                 C["edge_hi"] if on else C["edge"],
                                 width=2.5 if on else 1.5)
                # Etiqueta del costo
                mx = (px1 + px2) // 2 + 8
                my = (py1 + py2) // 2 - 10
                cv.create_text(mx, my, text=str(cost),
                               fill="#ddeeff", font=("Consolas", 9, "bold"))

        # Nodos del puzzle
        for name, (px, py) in pz.nodes.items():
            x, y = px + OX, py + OY

            if name == self.puz_current:
                col = C["current"]
            elif name == pz.start:
                col = C["start"]
            elif name == pz.goal:
                col = C["goal"]
            elif name in self.puz_expanded:
                col = C["expanded"]
            else:
                col = C["available"]

            cv.create_oval(x - NODE_R, y - NODE_R,
                           x + NODE_R, y + NODE_R,
                           fill=col, outline="#cccccc", width=2)
            cv.create_text(x, y, text=name,
                           fill="white", font=("Consolas", 11, "bold"))

            # Valor heurístico bajo el nodo
            h_val = pz.h(name)
            cv.create_text(x, y + NODE_R + 12,
                           text=f"h={h_val}",
                           fill="#8899bb", font=("Consolas", 8))

    # ── Log ──────────────────────────────────────────────────────

    def _log(self, widget, msg):
        widget.configure(state="normal")
        widget.insert("end", msg + "\n")
        widget.see("end")
        widget.configure(state="disabled")

    # ── Animación ────────────────────────────────────────────────

    def _start_animation(self):
        if not self.running:
            self.running = True
            self.btn_start.configure(text="[||] Pausar",
                                     command=self._pause_animation)
            self._tick()

    def _pause_animation(self):
        self.running = False
        self.btn_start.configure(text="[>] Continuar",
                                 command=self._start_animation)

    def _step(self):
        """Avanzar un solo paso."""
        if self.ev_idx < len(self.events):
            self._process_event(self.events[self.ev_idx])
            self.ev_idx += 1
            if self.ev_idx >= len(self.events):
                self._finish()

    def _reset(self):
        """Reiniciar la visualización desde el principio."""
        self.running = False
        self.btn_start.configure(text="[>] Iniciar",
                                 command=self._start_animation)
        # Reconstruir mundo y solver
        self.world   = build_world()
        self.events, self.metrics = solve_hybrid(self.world, "A", "M")
        # Resetear estado visual
        for n in self.world.nodes:
            self.vstate[n] = "locked" if n in ("C", "K") else "available"
        self.ev_idx       = 0
        self.cur_puzzle   = None
        self.puz_expanded = set()
        self.puz_path     = []
        self.puz_current  = None
        # Resetear estadísticas
        for v in self.sv.values():
            v.set("—")
        # Resetear logs
        for w in (self.glog, self.plog):
            w.configure(state="normal")
            w.delete("1.0", "end")
            w.configure(state="disabled")
        self.right_title.configure(text="Puzzle Solver — Búsqueda Informada (A*)")
        self._draw_global()
        self._draw_puzzle_placeholder()

    def _tick(self):
        """Callback periódico que procesa un evento por llamada."""
        if not self.running:
            return
        if self.ev_idx >= len(self.events):
            self._finish()
            return

        self._process_event(self.events[self.ev_idx])
        self.ev_idx += 1
        self.after(self.delay, self._tick)

    def _process_event(self, ev):
        """Despacha un evento al canvas y log correspondiente."""
        if ev["phase"] == "global":
            self._handle_global(ev)
        else:
            self._handle_local(ev)

    def _handle_global(self, ev):
        t    = ev["type"]
        node = ev["node"]
        self._log(self.glog, ev["msg"])

        if t == "expand":
            # El nodo previamente marcado como "current" pasa a "expanded"
            for n, vs in list(self.vstate.items()):
                if vs == "current":
                    self.vstate[n] = "expanded"
            # Marcar el nodo actual (no sobreescribir "solved")
            if self.vstate.get(node) != "solved":
                self.vstate[node] = "current"
            self._draw_global()

        elif t == "locked":
            self._draw_global()

        elif t == "puzzle_start":
            pz = self.world.puzzles.get(node)
            self.cur_puzzle   = pz
            self.puz_expanded = set()
            self.puz_path     = []
            self.puz_current  = None
            if pz:
                self.right_title.configure(text=f"{pz.label} — A*")
            self._draw_puzzle()

        elif t == "goal":
            path = ev["path"]
            # Quitar marcas de current/expanded; resaltar la ruta solución
            for n in self.vstate:
                if self.vstate[n] in ("current", "expanded"):
                    self.vstate[n] = "available"
            for n in path:
                if self.vstate.get(n) != "solved":
                    self.vstate[n] = "path"
            self._draw_global(path_hi=path)

    def _handle_local(self, ev):
        t = ev["type"]
        self._log(self.plog, ev["msg"])

        if t == "expand":
            self.puz_current = ev["node"]
            self.puz_expanded.add(ev["node"])
            self._draw_puzzle()

        elif t == "solved":
            # Mostrar camino óptimo del puzzle
            self.puz_path    = ev.get("path", [])
            self.puz_current = None
            self._draw_puzzle()
            # Actualizar el nodo global correspondiente
            locked_node = ev.get("puzzle_node")
            if locked_node:
                self.vstate[locked_node] = "solved"
            self._draw_global()

    def _finish(self):
        """Mostrar métricas finales al terminar la animación."""
        self.running = False
        self.btn_start.configure(text="[>] Iniciar",
                                 command=self._start_animation)
        m = self.metrics
        self.sv["g_exp"].set(str(m["global"]["nodes_expanded"]))
        self.sv["g_dep"].set(str(m["global"]["depth"]))
        self.sv["l_exp"].set(str(m["local"]["nodes_expanded"]))
        self.sv["l_cost"].set(str(m["local"]["total_cost"]))
        self.sv["time"].set(f"{m['global']['time'] * 1000:.1f} ms")

        sep = "═" * 38
        self._log(self.glog, f"\n{sep}")
        self._log(self.glog, f"  SOLUCION: {' -> '.join(m['path'])}")
        self._log(self.glog, f"  Profundidad: {m['global']['depth']}   Costo: {m['global']['cost']}")
        self._log(self.glog, f"{sep}\n")

# ═══════════════════════════════════════════════════════════════
#  PUNTO DE ENTRADA
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    app = App()
    app.mainloop()
