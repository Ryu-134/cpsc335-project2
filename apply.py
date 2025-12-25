import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from tkinter import font as tkfont
import os
import random
import heapq
import math
import json 
from PIL import Image, ImageTk 
from collections import deque
from dataclasses import dataclass
from typing import Optional, FrozenSet, Dict, Tuple, List, Set


@dataclass
class Edge:
    u: str                              
    v: str                              
    distance: int = 1
    time:int = 1
    accessible: bool = True
    closed: bool = False
    line_id: Optional[int] = None      
    text_id: Optional[int] = None      
    
    
    def key(self) -> FrozenSet[str]:
        return frozenset({self.u, self.v})  # use frozen set to ensure immutability --> makes sure each edge unique


    def color(self) -> str:     # choose color based on path logic state
        if self.closed:
            return "red"
        if not self.accessible:
            return "orange"
        return "black"

class Graph:
    def __init__(self):

        self.nodes: Dict[str, Tuple[int, int, Optional[int], Optional[int]]] = {} 
        self.edges: Dict[FrozenSet[str], Edge] = {} 
        self.adj: Dict[str, Dict[str, Edge]] = {} 
        
    def add_node(self, name, x, y):  
        if name in self.nodes:
            raise ValueError(f"Duplicate node '{name}'")    # CHECK --> no duplicate nodes 
        self.nodes[name] = (x, y, None, None)   # oid/lid filled in later by GUI.draw_node()
        self.adj[name] = {} # init empty neighbor dict for this node
        
    def add_edge(self, u, v, distance, time, accessible) -> Edge:
        if u == v:
            raise ValueError("Cannot connect a node to itself")     # CHECK --> no self-looping nodes 
        if u not in self.nodes or v not in self.nodes:
            raise ValueError("Both endpoints must exist")   # CHECK --> both nodes must exist      
        key = frozenset({u, v})
        if key in self.edges:
            raise ValueError("Edge already exists")         # CHECK --> block multiedges between same endpoints
        e = Edge(u, v, distance, time, accessible)
        self.edges[key] = e      # global edge registry
        self.adj[u][v] = e       # symmetric adjacency 
        self.adj[v][u] = e
        return e
    
    
    def remove_edge(self, u, v) -> Edge:    # fully remove an edge from both global registry and adjacency dicts
        key = frozenset({u, v})
        e = self.edges.pop(key, None)
        if not e:
            raise ValueError("Edge does not exist")
        if u in self.adj and v in self.adj[u]:
            del self.adj[u][v]
        if v in self.adj and u in self.adj[v]:
            del self.adj[v][u]
        return e    # return Edge so GUI can also delete the canvas visuals
    
    
    def randomize_edge_weights(self):   # dynamic traffic sim
        for e in self.edges.values():
            e.distance = random.randint(1, 20)
            e.time = random.randint(1, 20)
    
    
    def get_edge(self, u, v):
        return self.edges.get(frozenset({u, v}))
    
    
    def neighbors(self, node, accessible_only):     # ensure deterministic neighbor ordering to get same results so BFS/DFS become predictable and testable
        out = []
        for nbr, e in self.adj.get(node, {}).items():
            if e.closed: 
                continue
            if accessible_only and not e.accessible:
                continue
            out.append((nbr, e))
        out.sort(key=lambda t: t[0])    # stable traversal order so demo is repeatable
        return out
    
    
    def bfs(self, start, goal, accessible_only):
        if start not in self.nodes or goal not in self.nodes:
            raise ValueError("Start and goal must be valid nodes")
        q = deque([start])
        visited: Set[str] = {start}
        parent: Dict[str, Optional[str]] = {start: None}
        order: List[str] = []    # order = full visitation order (when node popped from queue)
        discover: List[str] = []    # helper list to track node pings
        
        while q:
            cur = q.popleft()
            order.append(cur)
            if cur == goal:
                break
            for number, _ in self.neighbors(cur, accessible_only):
                if number not in visited:
                    visited.add(number)
                    parent[number] = cur
                    q.append(number)
                    discover.append(number)
                    
        if goal not in parent:
            return [], order, discover
        
        path = []
        cur: Optional[str] = goal
        while cur is not None:
            path.append(cur)
            cur = parent[cur]
        path.reverse()
        return path, order, discover
 
 
    def dfs(self, start, goal, accessible_only):
        if start not in self.nodes or goal not in self.nodes:
            raise ValueError("Start and goal must be valid nodes")
        visited: Set[str] = set()
        parent: Dict[str, Optional[str]] = {start: None}
        found = False
        order: List[str] = [] 
        discover: List[str] = []
        
        def recurse(u):
            nonlocal found
            if found:
                return
            visited.add(u)
            order.append(u)
            if u == goal:
                found = True 
                return
            for number, _ in self.neighbors(u, accessible_only):
                if number not in visited:
                    parent[number] = u
                    discover.append(number)
                    recurse(number)
        
        recurse(start)
        if not found:
            return [], order, discover
        
        path = []
        cur: Optional[str] = goal
        while cur is not None:
            path.append(cur)
            cur = parent[cur]
        path.reverse()
        return path, order, discover
    
    
    def toggle_closed(self, u, v):
        e = self.get_edge(u, v)
        if not e:
            raise ValueError("Edge does not exist")
        e.closed = not e.closed
        return e
    
    
    def toggle_accessibility(self, u, v):
        e = self.get_edge(u, v)
        if not e:
            raise ValueError("Edge does not exist")
        e.accessible = not e.accessible
        return e
            
    def remove_node(self, name) -> List[Edge]:
        if name not in self.nodes:
            raise ValueError("Node does not exist")

        neighbors = list(self.adj[name].keys())

        removed_edges: List[Edge] = []

        for nbr in neighbors:
            e = self.get_edge(name, nbr)
            if e:
                self.remove_edge(name, nbr)
                removed_edges.append(e)

        del self.adj[name]
        del self.nodes[name]

        return removed_edges
    

    def heuristic(self, u, v, weight_type): # toggle heuristic for simple swap from dijkstra => A*
        x1, y1, _, _ = self.nodes[u]
        x2, y2, _, _ = self.nodes[v]
        return math.hypot(x2 - x1, y2 - y1) if weight_type == "distance" else 0


    def dijkstra(self, start, goal, weight_type, accessible_only):
        return self._weighted_search(start, goal, weight_type, accessible_only, use_heuristic=False)


    def astar(self, start, goal, weight_type, accessible_only):
        return self._weighted_search(start, goal, weight_type, accessible_only, use_heuristic=True)


    def _weighted_search(self, start, goal, weight_type, accessible_only, use_heuristic):
        if start not in self.nodes or goal not in self.nodes:
            raise ValueError("Start and goal must be valid nodes")

        pq = [(0, start)]        
        costs = {start: 0}
        parent = {start: None}        
        visited_order = []      
        discover_order = []     

        while pq:
            cur_priority, u = heapq.heappop(pq)
            if cur_priority > costs.get(u, float('inf')) + (self.heuristic(u, goal, weight_type) if use_heuristic else 0):
                continue
            visited_order.append(u)
            if u == goal:
                break

            for v, edge in self.neighbors(u, accessible_only):
                weight = edge.distance if weight_type == "distance" else edge.time
                new_cost = costs[u] + weight

                if new_cost < costs.get(v, float('inf')):   # relaxation step
                    costs[v] = new_cost
                    parent[v] = u
                    priority = new_cost # Dijkstra: priority = new_cost; A*: priority = new_cost + heuristic(v, goal)

                    if use_heuristic:
                        priority += self.heuristic(v, goal, weight_type)                    
                    heapq.heappush(pq, (priority, v))
                    discover_order.append(v)

        if goal not in parent:
            return [], visited_order, discover_order        
        path = []
        curr = goal
        while curr is not None:
            path.append(curr)
            curr = parent[curr]
        path.reverse()
              
        return path, visited_order, discover_order


    def kruskal(self, weight_type, accessible_only):
        valid_edges = []
        for e in self.edges.values():
            if e.closed: continue
            if accessible_only and not e.accessible: continue
            weight = e.distance if weight_type == "distance" else e.time
            valid_edges.append((weight, e))
            
        valid_edges.sort(key=lambda x: x[0])
        dsu = DisjointSet(self.nodes.keys())
        mst_edges = []
        total_cost = 0
        
        for weight, e in valid_edges:
            if dsu.union(e.u, e.v):
                mst_edges.append(e)
                total_cost += weight
                
        return mst_edges, total_cost

    def prim(self, start_node, weight_type, accessible_only):
        if start_node not in self.nodes:
            raise ValueError("Start node required for Prim's")
            
        mst_edges = []
        visited = {start_node}
        total_cost = 0
        
        pq = []
        for nbr, e in self.neighbors(start_node, accessible_only):
            w = e.distance if weight_type == "distance" else e.time
            heapq.heappush(pq, (w, nbr, e))
            
        while pq:
            weight, u, edge = heapq.heappop(pq)
            
            if u in visited:
                continue
                
            visited.add(u)
            mst_edges.append(edge)
            total_cost += weight
            
            for nbr, e in self.neighbors(u, accessible_only):
                if nbr not in visited:
                    w = e.distance if weight_type == "distance" else e.time
                    heapq.heappush(pq, (w, nbr, e))
                    
        return mst_edges, total_cost


    def to_dict(self):
        """Serialize graph data to a dictionary."""
        return {
            "nodes": [
                {"name": n, "x": data[0], "y": data[1]} 
                for n, data in self.nodes.items()
            ],
            "edges": [
                {
                    "u": e.u, "v": e.v, 
                    "distance": e.distance, "time": e.time, 
                    "accessible": e.accessible, "closed": e.closed
                }
                for e in self.edges.values()
            ]
        }

    def from_dict(self, data):
        """Clear current graph and rebuild from dictionary."""
        self.nodes.clear()
        self.edges.clear()
        self.adj.clear()
        
        for n_data in data["nodes"]:
            self.nodes[n_data["name"]] = (n_data["x"], n_data["y"], None, None)
            self.adj[n_data["name"]] = {}
            
        for e_data in data["edges"]:
            self.add_edge(
                e_data["u"], e_data["v"], 
                e_data["distance"], e_data["time"], 
                e_data["accessible"]
            )
            if e_data.get("closed", False):
                self.edges[frozenset({e_data["u"], e_data["v"]})].closed = True
                
    
class GUI:
    NODE_R = 10     # node size control
    ANIM_TRAVERSAL_MS = 600     # ping interval timing
    ANIM_EDGE_MS = 400          # interval between edges turning green 
    ANIM_PING_FLASH_MS = 600    # duration node stays yellow
    ANIM_NODE_MS = 400          # interval between nodes turning green 
    
    
    def __init__(self, root: tk.Tk):
        self.root = root 
        self.graph = Graph()
        self.mode_place_pending_name: Optional[str] = None
        self.selected_nodes: list[str] = []
        
        self.bg_image_original = None  # stores high-res PIL Image
        self.bg_image_tk = None        # Ttinter-ready image
        self.bg_file_path = None       # file path for saving
        self.map_item: Optional[int] = None              
        self.overlay_var = tk.BooleanVar(value = True) 
        
        self.current_zoom = 1.0  # Track zoom level  
        
        self.ui_font = tkfont.Font(family="Arial", size=11, weight="normal")            
        self.ui_font_bold = tkfont.Font(family="Arial", size=13, weight="bold")  
        self.root.option_add("*Font", self.ui_font)                     
        self.root.option_add("*Text*Font", self.ui_font)
                        
        style = ttk.Style(self.root)  
        available_themes = style.theme_names()   
                                   
        if "aqua" in available_themes:
            style.theme_use("aqua")  # mac
        elif "vista" in available_themes:
            style.theme_use("vista") # windows 
        else:
            for candidate in ("clam", "alt", "default", "classic"): 
                if candidate in available_themes:
                    style.theme_use(candidate)
                    break
                
        style.configure(".", font=self.ui_font)          
        self.root.option_add("*TCombobox*Listbox*Font", self.ui_font)       
        
        self.build_layout() # build all frames and widgets
        self.keybind()  # hook hotkeys
        
        self.animating = False
        self.current_animation_tokens: list[int] = []        
        self.current_popup: Optional[tk.Toplevel] = None
    
    
    def build_layout(self):
        self.root.geometry("1200x950")   
        try:
            self.root.state('zoomed')   
        except:
            try:
                self.root.attributes('-zoomed', True)
            except:
                w = self.root.winfo_screenwidth()
                h = self.root.winfo_screenheight()
                self.root.geometry(f"{w}x{h}+0+0")

        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1) 
        self.root.grid_columnconfigure(1, weight=0) 
        
        self.left = ttk.Frame(self.root)
        self.left.grid(row=0, column=0, sticky="nsew")  
        self.canvas = tk.Canvas(self.left, bg="white")
        self.canvas.pack(fill=tk.BOTH, expand=True)

        self.right = ttk.Frame(self.root) 
        self.right.grid(row=0, column=1, sticky="nsew")


        self.right_canvas = tk.Canvas(self.right, width=500) 
        self.right_scrollbar = ttk.Scrollbar(self.right, orient="vertical", command=self.right_canvas.yview)
        
        self.right_scrollbar.pack(side="right", fill="y")
        self.right_canvas.pack(side="left", fill="both", expand=True)
        self.right_canvas.configure(yscrollcommand=self.right_scrollbar.set)
        box = tk.Frame(self.right_canvas, padx=8, pady=8)
        self.right_canvas_window = self.right_canvas.create_window((0,0), window=box, anchor="nw")

        def on_frame_configure(event):
            self.right_canvas.configure(scrollregion=self.right_canvas.bbox("all"))
        
        def on_canvas_configure(event):
            self.right_canvas.itemconfig(self.right_canvas_window, width=event.width)
            
        box.bind("<Configure>", on_frame_configure)
        self.right_canvas.bind("<Configure>", on_canvas_configure)

        def _on_mousewheel(event):
            try:
                self.right_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
            except:
                pass

        def _bind_wheel(event):
            self.right_canvas.bind_all("<MouseWheel>", _on_mousewheel)
            
        def _unbind_wheel(event):
            self.right_canvas.unbind_all("<MouseWheel>")

        self.right_canvas.bind('<Enter>', _bind_wheel)
        self.right_canvas.bind('<Leave>', _unbind_wheel)
        
        ttk.Label(box, text = "Project Management:", font=self.ui_font_bold).pack(anchor="w", pady=(0,4))
        row_proj = ttk.Frame(box)
        row_proj.pack(fill=tk.X, pady=2)
        ttk.Button(row_proj, text="Save Project", command=self.save_project).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0,2))
        ttk.Button(row_proj, text="Load Project", command=self.load_project).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(2,0))

        ttk.Separator(box, orient='horizontal').pack(fill='x', pady=10)
        ttk.Label(box, text = "Map Background:", font=self.ui_font_bold).pack(anchor="w", pady=(0,3))        
        row_map = ttk.Frame(box)
        row_map.pack(fill=tk.X, pady=2)
        ttk.Button(row_map, text="Load Map Image", command=self.open_background_dialog).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0,5))
        ttk.Checkbutton(row_map, text="Show", variable=self.overlay_var, command=self.refresh_background).pack(side=tk.LEFT)
        
        ttk.Label(
            box, 
            text="Supports: .png, .jpg, .jpeg, .bmp, .gif", 
            font=("Arial", 9, "italic"), 
            foreground="#555555"
        ).pack(anchor="w", pady=(0, 8))
        
        row_zoom = ttk.Frame(box)
        row_zoom.pack(fill=tk.X, pady=(5,0))    
        ttk.Label(row_zoom, text="Zoom:").pack(side=tk.LEFT)  
              
        self.zoom_scale = tk.Scale(
            row_zoom, 
            from_=0.5, to=3.0, 
            resolution=0.1, 
            orient=tk.HORIZONTAL, 
            showvalue=0,                
            command=self.on_zoom_change
        )
        self.zoom_scale.set(1.0) 
        self.zoom_scale.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.zoom_value_lbl = ttk.Label(row_zoom, text="1.0x", width=4)
        self.zoom_value_lbl.pack(side=tk.LEFT)
       
        ttk.Separator(box, orient='horizontal').pack(fill='x', pady=10)          
        ttk.Label(box, text = "Add Point of Interest:", font=self.ui_font_bold).pack(anchor="w", pady=3)
        row = ttk.Frame(box)
        row.pack(fill = tk.X)
        self.node_name_var = tk.StringVar()
        ttk.Entry(row, textvariable = self.node_name_var).pack(side = tk.LEFT, fill = tk.X, expand = True)
        ttk.Button(row, text = "Place Point", command = self.start_node).pack(side = tk.LEFT, padx = (8,0))      
        
        ttk.Separator(box, orient='horizontal').pack(fill='x', pady=10)        
        ttk.Label(box, text = "Connect Points:", font=self.ui_font_bold).pack(anchor="w", pady=3)
        self.selected_label = ttk.Label(box, text = "Currently Selected: ")
        self.selected_label.pack(anchor = "w", pady = (3, 3))      
        r1 = ttk.Frame(box)
        r1.pack(fill = tk.X, pady = (3, 3))        
        ttk.Label(r1, text = "Distance:").pack(side = tk.LEFT)
        self.dist_var = tk.StringVar(value = "1")
        ttk.Entry(r1, width = 5, textvariable = self.dist_var).pack(side = tk.LEFT, padx = (6, 20))        
        ttk.Label(r1, text = "Time:").pack(side = tk.LEFT)
        self.time_var = tk.StringVar(value = "1")
        ttk.Entry(r1, width = 5, textvariable = self.time_var).pack(side = tk.LEFT, padx = (6, 12))        
        self.access_var = tk.BooleanVar(value = True)        
        ttk.Checkbutton(r1, text = "Accessible", variable = self.access_var).pack(side = tk.LEFT, padx = (18, 0))        
        ttk.Button(box, text="Remove Building", command=self.remove_node_gui).pack(fill=tk.X, pady=(6,1))
        ttk.Button(box, text = "Add Path", command = self.add_edge).pack(fill = tk.X, pady = (1,1))
        ttk.Button(box, text= "Remove Path", command=self.remove_edge_gui).pack(fill=tk.X, pady=(1,1))
        ttk.Button(box, text = "Toggle Closure", command = self.toggle_close).pack(fill = tk.X, pady = (1,1))
        ttk.Button(box, text="Toggle Accessibility", command=self.toggle_accessible).pack(fill=tk.X, pady=(1,1))
        ttk.Button(box, text = "Randomize All Edge Weights", command = self.randomize).pack(fill = tk.X, pady = (1, 0))
          
                
        ttk.Separator(box, orient='horizontal').pack(fill='x', pady=10)        
        ttk.Label(box, text = "Route Search:", font=self.ui_font_bold).pack(anchor="w", pady=3)  
        rowS = ttk.Frame(box)
        rowS.pack(fill = tk.X, pady = 4)
        ttk.Label(rowS, text = "Start: ").pack(side = tk.LEFT)
        self.start_var = tk.StringVar(value = "")
        self.start_menu = ttk.Combobox(rowS, textvariable = self.start_var, values = [], state = "readonly")
        self.start_menu.pack(side = tk.LEFT, fill = tk.X, expand = True, padx = 4)   
             
        rowG = ttk.Frame(box) 
        rowG.pack(fill = tk.X, pady = 4)
        ttk.Label(rowG, text = "Goal: ").pack(side = tk.LEFT)
        self.goal_var = tk.StringVar(value = "")
        self.goal_menu = ttk.Combobox(rowG, textvariable = self.goal_var, values = [], state = "readonly")
        self.goal_menu.pack(side = tk.LEFT, fill = tk.X, expand = True, padx = 4)    
        
        rowM = ttk.Frame(box)   # metric selection - dist vs time
        rowM.pack(fill=tk.X, pady=4)
        ttk.Label(rowM, text="Optimize For: ").pack(side=tk.LEFT)
        self.metric_var = tk.StringVar(value="distance")
        ttk.Radiobutton(rowM, text="Distance", variable=self.metric_var, value="distance").pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(rowM, text="Time", variable=self.metric_var, value="time").pack(side=tk.LEFT, padx=5)
        
        self.access_only_var = tk.BooleanVar(value = False)
        ttk.Checkbutton(box, text = "Accessible Only",  variable = self.access_only_var).pack(anchor = "w", pady = (3, 0))
        
        btn_frame = ttk.Frame(box)
        btn_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(btn_frame, text="Unweighted (Hops):", font=("Arial", 10, "italic")).pack(anchor="w", pady=(5,0))
        ttk.Button(btn_frame, text = "BFS (Shortest Hops)", command = lambda: self.execute_search("bfs")).pack(fill = tk.X, pady = 1)
        ttk.Button(btn_frame, text = "DFS (Exploration)", command = lambda: self.execute_search("dfs")).pack(fill = tk.X, pady = 1)

        ttk.Label(btn_frame, text="Weighted (Cost):", font=("Arial", 10, "italic")).pack(anchor="w", pady=(5,0))
        ttk.Button(btn_frame, text = "Dijkstra (Guaranteed Shortest)", command = lambda: self.execute_search("dijkstra")).pack(fill = tk.X, pady = 1)
        ttk.Button(btn_frame, text = "A* Search (Smart/Heuristic)", command = lambda: self.execute_search("astar")).pack(fill = tk.X, pady = 1)


        ttk.Separator(box, orient='horizontal').pack(fill='x', pady=10)        
        ttk.Label(box, text="Network Optimization (MST):", font=self.ui_font_bold).pack(anchor="w", pady=3)        
        btn_frame_mst = ttk.Frame(box)
        btn_frame_mst.pack(fill=tk.X, pady=2)        
        ttk.Button(btn_frame_mst, text="Kruskal's MST (Global Sort)", 
                   command=lambda: self.execute_mst("kruskal")).pack(fill=tk.X, pady=1)
        ttk.Button(btn_frame_mst, text="Prim's MST (Grow Tree)", 
                   command=lambda: self.execute_mst("prim")).pack(fill=tk.X, pady=1)
        
        
        ttk.Separator(box, orient='horizontal').pack(fill='x', pady=10)        
        ttk.Label(box, text = "Output:", font=self.ui_font_bold).pack(anchor="w", pady=3)
        out_frame = ttk.Frame(box)
        out_frame.pack(fill=tk.BOTH, expand=True)
        self.output = tk.Text(out_frame, height=13, width= 55, wrap="word", state="disabled")
        yscroll = ttk.Scrollbar(out_frame, orient="vertical", command=self.output.yview)
        self.output.configure(yscrollcommand=yscroll.set)
        self.output.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        yscroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        
        ttk.Separator(box, orient='horizontal').pack(fill='x', pady=12)
        info_frame = ttk.Frame(box)
        info_frame.pack(fill=tk.X, pady=5)        
        info_frame.grid_columnconfigure(0, weight=1)
        info_frame.grid_columnconfigure(1, weight=1)        
        btn_details = ttk.Button(info_frame, text="Algorithm Encyclopedia", command=self.show_algo_details)
        btn_details.grid(row=0, column=0, padx=2, sticky="ew")        
        btn_help = ttk.Button(info_frame, text="Help", command=self.show_help)
        btn_help.grid(row=0, column=1, padx=2, sticky="ew")
          
            
    def keybind(self):
        self.canvas.bind("<Button-1>", self.click)
        self.root.bind("<Escape>", self.on_escape)  

        
    def text_output(self, str):
        self.output.configure(state="normal")
        self.output.insert(tk.END, str + "\n")
        self.output.see(tk.END)
        self.output.configure(state="disabled")
        
        
    def start_node(self):
        name = self.node_name_var.get().strip()
        if not name:
            messagebox.showerror("Error", "Enter a Point Name")
            return
        if name in self.graph.nodes:
            messagebox.showerror("Error", f"Duplicate node '{name}'")
            return
        self.mode_place_pending_name = name # remember which name will be placed
        self.canvas.configure(cursor = "crosshair")
        self.text_output(f"Click on map to place '{name}'.")
        
        
    def draw_node(self, name, x, y) -> tuple[int, int]:
        r = self.NODE_R
        oid = self.canvas.create_oval(x - r, y - r, x + r, y + r, fill = "black", outline = "black", width = 2, tags = (f"node:{name}", "all_elements"))
        lid = self.canvas.create_text(x, y - r - 10, text = name, font=self.ui_font, tags="all_elements")
        
        self.canvas.scale(oid, 0, 0, self.current_zoom, self.current_zoom)
        self.canvas.scale(lid, 0, 0, self.current_zoom, self.current_zoom)
        return oid, lid
    
    
    def draw_edge(self, edge): 
        x_u, y_u, _, _ = self.graph.nodes[edge.u]
        x_v, y_v, _, _ = self.graph.nodes[edge.v]
        edge.line_id = self.canvas.create_line(x_u, y_u, x_v, y_v, fill=edge.color(), width=2, tags="all_elements")

        lx, ly, ang = self.compute_edge_label_position(edge, offset_px=12) 

        edge.text_id = self.canvas.create_text(  
            lx, ly, text=f"d : {edge.distance},  t : {edge.time}", font=self.ui_font, fill="gray", angle=ang,
            tags="all_elements" # <--- ADDED TAG
        )
        self.canvas.tag_raise(edge.text_id) 

        self.canvas.scale(edge.line_id, 0, 0, self.current_zoom, self.current_zoom)
        self.canvas.scale(edge.text_id, 0, 0, self.current_zoom, self.current_zoom)


    def add_edge(self):
        if len(self.selected_nodes) != 2:
            messagebox.showerror("Error", "Select exactly 2 nodes")
            return
        u, v = self.selected_nodes
        try:
            d = int(self.dist_var.get())
            t = int(self.time_var.get())
            if d <= 0 or t <= 0:
                raise ValueError
        except Exception:
            messagebox.showerror("Error", "Distance and Time must be positive integers")
            return
        acc = bool(self.access_var.get())
        try:
            e = self.graph.add_edge(u, v, d, t, acc)
            self.draw_edge(e)
            self.text_output(f"Added path:  {u} ↔ {v}   (Distance = {d}, Time = {t}, Accessible = {acc})")
        except Exception as ex:
            messagebox.showerror("Error", str(ex))
        
        
    def refresh_node_menu(self):
        names = sorted(self.graph.nodes.keys())
        self.start_menu["values"] = names
        self.goal_menu["values"] = names
  
    
    def click(self, event):
        canvas_x = self.canvas.canvasx(event.x)
        canvas_y = self.canvas.canvasy(event.y)
        
        logical_x = canvas_x / self.current_zoom
        logical_y = canvas_y / self.current_zoom

        if self.mode_place_pending_name is not None:
            name = self.mode_place_pending_name            
            try:
                self.graph.add_node(name, logical_x, logical_y)                
                oid, lid = self.draw_node(name, logical_x, logical_y)                
                x, y, _, _ = self.graph.nodes[name]
                self.graph.nodes[name] = (x, y, oid, lid)                

                self.mode_place_pending_name = None
                self.canvas.configure(cursor="")
                self.node_name_var.set("")
                self.text_output(f"Placed point: '{name}'")
                self.refresh_node_menu()
            except Exception as exc:
                messagebox.showerror("Error", str(exc))
                return
        else:           
            clicked = self.hit_node(canvas_x, canvas_y)
            if clicked:
                self.toggle_select_node(clicked)
                self.refresh_node_menu()

        
    def hit_node(self, x, y) -> Optional[str]:
        for item in self.canvas.find_overlapping(x, y, x, y):
            for i in self.canvas.gettags(item):
                if i.startswith("node:"):
                    return i.split(":", 1)[1]
        return None
    
    
    def toggle_select_node(self, name):
        if name in self.selected_nodes:
            self.selected_nodes.remove(name)
        else:
            if len(self.selected_nodes) == 2:
                self.selected_nodes.pop(0)
            self.selected_nodes.append(name)
            
        for n, (_, _, oid, _) in self.graph.nodes.items():
            if oid:
                self.canvas.itemconfig(
                    oid, 
                    outline = ("blue" if n in self.selected_nodes else "black"), 
                    width = (3 if n in self.selected_nodes else 2),
                ) 
        self.selected_label.config(text = f"Selected: {self.selected_nodes}")
        
        
    def update_visual(self, edge):  # sync canvas after mutating edge state
        if edge.line_id:
            self.canvas.itemconfig(edge.line_id, fill=edge.color(), width=2)
        if edge.text_id:
            lx, ly, ang = self.compute_edge_label_position(edge, offset_px=12)
            screen_x = lx * self.current_zoom
            screen_y = ly * self.current_zoom            
            self.canvas.coords(edge.text_id, screen_x, screen_y)
            self.canvas.itemconfig(edge.text_id, font=self.ui_font, text=f"d : {edge.distance},  t : {edge.time}", angle=ang)
            self.canvas.tag_raise(edge.text_id)
            
    
    def toggle_close(self):
        if len(self.selected_nodes) != 2:
            messagebox.showerror("Error", "Select exactly 2 nodes to toggle")
            return
        u, v = self.selected_nodes
        e = self.graph.get_edge(u, v)        
        if not e:
            messagebox.showerror("Error", "No edge exists between the selected nodes")
            return
        self.graph.toggle_closed(u, v)
        self.update_visual(e)
        state_msg = "CLOSED to routing" if e.closed else "OPEN to routing"
        self.text_output(f"Path status updated:  {u} ↔ {v}  is now {state_msg}")
        
        
    def toggle_accessible(self):
        if len(self.selected_nodes) != 2:
            messagebox.showerror("Error", "Select exactly 2 nodes to toggle")
            return
        u, v = self.selected_nodes
        e = self.graph.get_edge(u, v)
        if not e:
            messagebox.showerror("Error", "No edge exists between the selected nodes")
            return
        self.graph.toggle_accessibility(u, v)
        self.update_visual(e)
        acc_msg = "ACCESSIBLE" if e.accessible else "NOT ACCESSIBLE"
        self.text_output(f"Accessibility updated:  {u} ↔ {v}  is now {acc_msg}")
        
    
    def remove_edge_gui(self):
        if len(self.selected_nodes) != 2:
            messagebox.showerror("Error", "Select exactly 2 nodes to delete edge")
            return

        u, v = self.selected_nodes
        e = self.graph.get_edge(u, v)
        if not e:
            messagebox.showerror("Error", "No edge exists between the selected nodes")
            return

        try:
            e = self.graph.remove_edge(u, v)
        except Exception as ex:
            messagebox.showerror("Error", str(ex))
            return

        if e.line_id:
            self.canvas.delete(e.line_id)
        if e.text_id:
            self.canvas.delete(e.text_id)

        self.clear_selection()
        self.text_output(f"Removed path:  {u} ↔ {v} \n")


    def remove_node_gui(self):
        if len(self.selected_nodes) != 1:
            messagebox.showerror("Error", "Select exactly 1 point")
            return

        name = self.selected_nodes[0]

        if name not in self.graph.nodes:
            messagebox.showerror("Error", "That point no longer exists")
            return

        x, y, oid, lid = self.graph.nodes[name]

        try:
            removed_edges = self.graph.remove_node(name)
        except Exception as ex:
            messagebox.showerror("Error", str(ex))
            return

        if oid:
            self.canvas.delete(oid)
        if lid:
            self.canvas.delete(lid)

        for e in removed_edges:
            if e.line_id:
                self.canvas.delete(e.line_id)
            if e.text_id:
                self.canvas.delete(e.text_id)

        self.clear_selection()
        self.refresh_node_menu()
        self.text_output(f"Removed building '{name}' and its connected paths.")
        self.start_var.set("")
        self.goal_var.set("")
        
            
    def randomize(self):
        self.clear_animation()
        self.graph.randomize_edge_weights()
        for e in self.graph.edges.values():
            self.update_visual(e)
        self.text_output("All path weights have been randomized to simulate dynamic campus traffic.")
        
        
    def clear_animation(self):
        for token in self.current_animation_tokens:
            try:
                self.root.after_cancel(token)
            except Exception: 
                pass
        self.current_animation_tokens.clear()
        for e in self.graph.edges.values():
            if e.line_id:
                self.canvas.itemconfig(e.line_id, fill = e.color(), width = 2)
        for _, (_, _, oid, _) in self.graph.nodes.items():
            if oid:
                self.canvas.itemconfig(oid, fill="black", outline = "black", width = 2)
        self.animating = False
        
        
    def ping_node(self, name):
        _, _, oid, _ = self.graph.nodes[name]
        if not oid:
            return
        self.canvas.itemconfig(oid, outline = "yellow", fill = "yellow", width = 3)
        self.current_animation_tokens.append(self.root.after(self.ANIM_PING_FLASH_MS, lambda: self.canvas.itemconfig(oid, outline = "black", fill = "black", width = 2)))


    def execute_search(self, algo):
        start = self.start_var.get().strip()
        goal = self.goal_var.get().strip()
        weight_type = self.metric_var.get() 
        
        if not start or not goal:
            messagebox.showerror("Error", "Select Start and Goal")
            return
        if start == goal:
            messagebox.showerror("Error", "Start and Goal must differ")
            return
        
        accessible_only = bool(self.access_only_var.get())
        self.text_output(f"Running {algo.upper()} from {start} to {goal} (accessible={accessible_only}, metric={weight_type})...")
        
        try:
            if algo == "bfs":
                path, order, discover = self.graph.bfs(start, goal, accessible_only)
            elif algo == "dfs":
                path, order, discover = self.graph.dfs(start, goal, accessible_only)
            elif algo == "dijkstra":
                path, order, discover = self.graph.dijkstra(start, goal, weight_type, accessible_only)
            elif algo == "astar":
                path, order, discover = self.graph.astar(start, goal, weight_type, accessible_only)
                
        except Exception as e:
            messagebox.showerror("Error", str(e))
            return
        
        if path:
            self.text_output("--------------------------------------------------")
            self.text_output(f"Algorithm: {algo.upper()}")
            self.text_output(f"Metric:    {weight_type}")
            self.text_output(f"Nodes visited: {len(order)}")
            self.text_output(f"Traversal order: {order}") 
            self.text_output(f"Final Path: {' -> '.join(path)}")
            self.text_output(f"Path Cost: {len(path)-1} edges (approx)") 
            self.text_output("--------------------------------------------------\n")
        else:
            self.text_output("--------------------------------------------------")
            self.text_output(f"Traversal order: {order}")
            self.text_output("No valid route was found under current constraints.")
            self.text_output("--------------------------------------------------\n")
                    
        self.clear_animation()
        visit_seq = [start] + list(discover)    # ping nodes by discovery 
        delay = self.ANIM_TRAVERSAL_MS
        
        for i, n in enumerate(visit_seq):
            self.current_animation_tokens.append(self.root.after(delay * i, lambda name = n: self.ping_node(name)))
            
        if path and len(path) >= 2:
            start_after = delay * max(1, len(visit_seq))
            
            for j in range(len(path) - 1):
                u, v = path[j], path[j + 1] 
                e = self.graph.get_edge(u, v)
                if e and e.line_id:
                    self.current_animation_tokens.append(self.root.after(start_after + self.ANIM_EDGE_MS * j, lambda lid = e.line_id: self.canvas.itemconfig(lid, fill = "green", width = 4)))
                    
            node_start = start_after + self.ANIM_EDGE_MS * (len(path) - 1)
            for k, node in enumerate(path):
                oid = self.graph.nodes[node][2]
                if oid:
                    self.current_animation_tokens.append(self.root.after(node_start + self.ANIM_NODE_MS * k,lambda o=oid: self.canvas.itemconfig(o, fill="green", outline="green", width=3)))
                


    def on_escape(self, event = None):              
        self.clear_selection()


    def clear_selection(self):                     
        self.selected_nodes.clear()
        for _, (_, _, oid, _) in self.graph.nodes.items():
            if oid:
                self.canvas.itemconfig(oid, outline = "black", width = 2)
        self.selected_label.config(text = f"Selected: {self.selected_nodes}")
        self.mode_place_pending_name = None
        self.canvas.configure(cursor = "")


    def compute_edge_label_position(self, edge, offset_px: int = 12): #  helper to position distance/time label
        # take midpoint of  edge segment -> find perpendicular unit normal-> nudge label 'offset_px' along normal so its not on top of line -> find angle for nice orientation
        x_u, y_u, _, _ = self.graph.nodes[edge.u]
        x_v, y_v, _, _ = self.graph.nodes[edge.v]
        mid_x, mid_y = (x_u + x_v) / 2.0, (y_u + y_v) / 2.0
        dx, dy = (x_v - x_u), (y_v - y_u)
        
        angle_draw = -math.degrees(math.atan2(dy, dx))
        if angle_draw <= -90:
            angle_draw += 180
        elif angle_draw > 90:
            angle_draw -= 180
            
        length = math.hypot(dx, dy) or 1.0
        nx, ny = (-dy / length, dx / length)
        
        label_x = mid_x + nx * offset_px
        label_y = mid_y + ny * offset_px
        
        return label_x, label_y, angle_draw

    def execute_mst(self, algo):
        weight_type = self.metric_var.get()
        accessible_only = bool(self.access_only_var.get())
        
        start_node = self.start_var.get().strip() # prim's needs start node => choose arbitrarily choose first or user choice
        if algo == "prim" and not start_node:
            if self.graph.nodes:
                start_node = list(self.graph.nodes.keys())[0]
            else:
                messagebox.showerror("Error", "Graph is empty")
                return

        self.text_output(f"Running {algo.upper()} optimization (metric={weight_type})...")
        
        try:
            if algo == "kruskal":
                edges, cost = self.graph.kruskal(weight_type, accessible_only)
            elif algo == "prim":
                edges, cost = self.graph.prim(start_node, weight_type, accessible_only)
        except Exception as e:
            messagebox.showerror("Error", str(e))
            return

        self.text_output("--------------------------------------------------")
        self.text_output(f"Algorithm: {algo.upper()}")
        self.text_output(f"Total Network Cost: {cost}")
        self.text_output(f"Edges in MST: {len(edges)}")
        self.text_output("--------------------------------------------------\n")
        
        self.clear_animation()
        delay = self.ANIM_EDGE_MS
        
        for i, e in enumerate(edges): # turn line Blue to distinguish from pathfinding (green)
            if e.line_id:
                self.current_animation_tokens.append(
                    self.root.after(delay * i, 
                                  lambda lid=e.line_id: self.canvas.itemconfig(lid, fill="blue", width=4))
                )
                
                
    def create_popup(self, title, content_text):
        if self.current_popup is not None and self.current_popup.winfo_exists():
            self.current_popup.lift()
            self.current_popup.focus_force()
            return

        top = tk.Toplevel(self.root)
        top.title(title)
        top.geometry("750x1200")
        top.transient(self.root) 
        self.current_popup = top
        
        def on_close():
            self.current_popup = None
            top.destroy()
            
        top.protocol("WM_DELETE_WINDOW", on_close)

        lbl = ttk.Label(top, text=title, font=("Arial", 18, "bold"))
        lbl.pack(pady=15)
        
        frame = ttk.Frame(top)
        frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)
        
        txt = tk.Text(frame, wrap="word", padx=15, pady=15, relief="flat", highlightthickness=0)
        vsb = ttk.Scrollbar(frame, orient="vertical", command=txt.yview)
        txt.configure(yscrollcommand=vsb.set)
        
        txt.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        
        txt.tag_configure("header", font=("Arial", 14, "bold"), spacing1=20, spacing3=5)
        txt.tag_configure("subheader", font=("Arial", 12, "bold"), spacing1=10, spacing3=2)
        txt.tag_configure("normal", font=("Arial", 11), spacing1=5, spacing2=2)
        
        for item in content_text:
            tag = item[0]
            text = item[1]
            txt.insert(tk.END, text + "\n", tag)
            
        txt.configure(state="disabled")


    def show_algo_details(self):
        content = [
            ("header", "1. Breadth-First Search (BFS)"),
            ("subheader", "Type: Unweighted Traversal"),
            ("normal", "• Time Complexity: O(V + E)\n• Space Complexity: O(V)"),
            ("normal", "BFS explores the graph layer by layer. It guarantees the shortest path in an unweighted graph (fewest hops). It treats a 100-mile highway and a 1-mile driveway as equal 'hops'."),
            ("subheader", "Best Used For:"),
            ("normal", "Peer-to-Peer networks, GPS (fewest turns), Web Crawlers."),
            
            ("header", "2. Depth-First Search (DFS)"),
            ("subheader", "Type: Unweighted Exploration"),
            ("normal", "• Time Complexity: O(V + E)\n• Space Complexity: O(V) (Recursion Stack)"),
            ("normal", "DFS dives deep into a branch before backtracking. It does NOT guarantee the shortest path. It is often used to explore or check if a path exists, rather than finding the best one."),
            ("subheader", "Best Used For:"),
            ("normal", "Maze solving, Cycle detection in code dependencies, Topological Sorting."),

            ("header", "3. Dijkstra's Algorithm"),
            ("subheader", "Type: Weighted Shortest Path (Greedy)"),
            ("normal", "• Time Complexity: O(E + V log V) (with Binary Heap)"),
            ("normal", "Dijkstra's algorithm finds the true shortest path by respecting edge weights (Distance/Time). It expands outward from the start like a ripple, always choosing the cheapest known node next."),
            ("subheader", "Key Constraint:"),
            ("normal", "Cannot handle negative edge weights."),
            
            ("header", "4. A* Search (A-Star)"),
            ("subheader", "Type: Weighted Shortest Path (Heuristic)"),
            ("normal", "• Time Complexity: O(E) (Best case) to O(E + V log V) (Worst case)"),
            ("normal", "A* is an optimization of Dijkstra. It adds a 'Heuristic' (h) to the cost function: f(n) = g(n) + h(n). In this app, h(n) is the straight-line distance to the goal. This pulls the search towards the destination, making it much faster."),
            ("subheader", "Best Used For:"),
            ("normal", "Video Game pathfinding, Google Maps, Robotics."),

            ("header", "5. Kruskal's Algorithm"),
            ("subheader", "Type: Minimum Spanning Tree (MST)"),
            ("normal", "• Time Complexity: O(E log E)"),
            ("normal", "Kruskal's sorts all edges by weight globally and adds them one by one if they don't form a cycle. It uses the 'Union-Find' data structure."),
            ("subheader", "Real World Use:"),
            ("normal", "Laying down LAN cables, piping systems, or power grids where you want to connect everyone with the least material possible."),

            ("header", "6. Prim's Algorithm"),
            ("subheader", "Type: Minimum Spanning Tree (MST)"),
            ("normal", "• Time Complexity: O(E + V log V)"),
            ("normal", "Prim's grows a single tree from a starting node. It always adds the cheapest connection from the tree to the outside world."),
            ("subheader", "Fun Fact:"),
            ("normal", "Prim's is faster than Kruskal's for 'Dense Graphs' (graphs with many edges), while Kruskal's is better for 'Sparse Graphs'."),
        ]
        self.create_popup("Algorithm Encyclopedia", content)


    def show_help(self):
        content = [
            ("header", "User Guide & Controls"),
            
            ("subheader", "1. Setup & Navigation"),
            ("normal", "• Load Map: Import a PNG/JPG floorplan or map. It will center at (0,0)."),
            ("normal", "• Zoom: Use the slider to zoom in/out (0.5x to 3.0x)."),
            ("normal", "• Pan: If the map is larger than the window, use your mouse wheel or trackpad to scroll."),

            ("subheader", "2. Building the Graph"),
            ("normal", "• Place Node: Enter a name (e.g., 'Library'), click 'Place Point', then click on the map."),
            ("normal", "• Connect Nodes: Click two nodes (they turn blue), enter Distance/Time, and click 'Add Path'."),
            ("normal", "• Edit: Select nodes to Remove, Toggle Closed (block path), or Toggle Accessibility (stairs/elevators)."),
            
            ("subheader", "3. Project Management"),
            ("normal", "• Save Project: Saves your nodes, connections, and background reference to a .json file."),
            ("normal", "• Load Project: Wipes the current canvas and restores a previously saved state."),
            
            ("subheader", "4. Algorithms"),
            ("normal", "• Select Start/Goal nodes and click an algorithm (BFS, Dijkstra, etc.)."),
            ("normal", "• Green Lines = The calculated path."),
            ("normal", "• Yellow Flashes = The computer 'thinking' (scanning nodes)."),
            
            ("header", "Tips & Tricks"),
            ("normal", "• The 'Show' checkbox hides the background image if you want to see just the abstract graph."),
            ("normal", "• 'Accessible Only' tells the algorithms to ignore paths marked as 'Not Accessible' (e.g., finding a wheelchair route)."),
            ("normal", "• Saving works best if you keep the background image in the same folder as the .json file."),
        ]
        self.create_popup("User Guide & Instructions", content)


    def open_background_dialog(self):
        file_path = filedialog.askopenfilename(
            title="Select Map Image",
            filetypes=[("Images", "*.png *.jpg *.jpeg *.bmp *.gif"), ("All Files", "*.*")]
        )
        if file_path:
            self.set_background(file_path)

    def set_background(self, file_path):
        try:
            self.bg_image_original = Image.open(file_path) # Load via PIL
            self.bg_file_path = file_path
            self.refresh_background()
            self.text_output(f"Loaded map: {os.path.basename(file_path)}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load image: {e}")

    def refresh_background(self):
        """Redraws the background image based on current zoom and visibility."""
        if self.map_item:
            self.canvas.delete(self.map_item)
            self.map_item = None
                        
        if not self.overlay_var.get() or not self.bg_image_original:
            return

        orig_w, orig_h = self.bg_image_original.size
        new_w = int(orig_w * self.current_zoom)
        new_h = int(orig_h * self.current_zoom)
        
        resized = self.bg_image_original.resize((new_w, new_h), Image.LANCZOS)
        self.bg_image_tk = ImageTk.PhotoImage(resized)        
       
        self.map_item = self.canvas.create_image(0, 0, image=self.bg_image_tk, anchor="nw")
        self.canvas.tag_lower(self.map_item) # Push behind nodes


    def save_project(self):
        file_path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON Files", "*.json")]
        )
        if not file_path:
            return
            
        data = {
            "graph": self.graph.to_dict(),
            "background_path": self.bg_file_path,
            "zoom": self.current_zoom
        }
        
        try:
            with open(file_path, 'w') as f:
                json.dump(data, f, indent=4)
            self.text_output(f"Project saved to {os.path.basename(file_path)}")
        except Exception as e:
            messagebox.showerror("Error", f"Save failed: {e}")

    def load_project(self):
        file_path = filedialog.askopenfilename(filetypes=[("JSON Files", "*.json")])
        
        if not file_path:
            return            
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)            
            self.clear_selection()
            self.graph.from_dict(data["graph"])            
            bg_path = data.get("background_path")            
            if bg_path and os.path.exists(bg_path):
                self.set_background(bg_path)
            elif bg_path:
                self.text_output(f"Warning: Original background file not found at {bg_path}")
            
            self.current_zoom = data.get("zoom", 1.0)
            self.zoom_scale.set(self.current_zoom)            
            self.canvas.delete("all") 
            self.refresh_background() 
            
            for name, (x, y, _, _) in self.graph.nodes.items():
                oid, lid = self.draw_node(name, x, y)
                self.graph.nodes[name] = (x, y, oid, lid)    
                            
            for e in self.graph.edges.values():
                self.draw_edge(e)
                                
            self.refresh_node_menu()
            self.text_output(f"Project loaded from {os.path.basename(file_path)}")
            
        except Exception as e:
            messagebox.showerror("Error", f"Load failed: {e}")


    def on_zoom_change(self, value):
        new_zoom = float(value)
        if hasattr(self, 'zoom_value_lbl'):
            self.zoom_value_lbl.config(text=f"{new_zoom:.1f}x")
            
        scale_factor = new_zoom / self.current_zoom 
        self.current_zoom = new_zoom        
        self.canvas.scale("all_elements", 0, 0, scale_factor, scale_factor)
        self.refresh_background()
        base_size = 13
        new_size = max(8, int(base_size * self.current_zoom)) 
        new_font = (self.ui_font.cget("family"), new_size)

        for _, _, _, lid in self.graph.nodes.values():
            if lid:
                self.canvas.itemconfig(lid, font=new_font)
        
        for e in self.graph.edges.values():
            if e.text_id:
                self.canvas.itemconfig(e.text_id, font=new_font)

class DisjointSet:  # helper for kruskal
    def __init__(self, nodes):
        self.parent = {n: n for n in nodes}
    
    def find(self, i):
        if self.parent[i] != i:
            self.parent[i] = self.find(self.parent[i])
        return self.parent[i]
    
    def union(self, i, j):  # parent swap
        root_i = self.find(i)
        root_j = self.find(j)
        if root_i != root_j:
            self.parent[root_i] = root_j
            return True 
        return False 

    
def main():
    root = tk.Tk()
    root.title("GraphAlgo Visualizer - Universal Pathfinding Tool")
    root.geometry("1200x900") 
    try:
        root.state('zoomed') 
    except:
        root.attributes('-zoomed', True)
    GUI(root)
    root.mainloop()

    
if __name__ == "__main__":
    main()
