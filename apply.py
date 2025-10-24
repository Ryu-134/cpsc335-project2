# Student Name: Casey Dane  
# Titan Email: crdane@csu.fullerton.edu
# Project: CPSC 335 – Interactive Campus Navigation System
# Date: 10/24/2025


import tkinter as tk
from tkinter import ttk, messagebox
from tkinter import font as tkfont
import os
import random
import math
from collections import deque
from dataclasses import dataclass
from typing import Optional, FrozenSet, Dict, Tuple, List, Set


DEFAULT_MAP_PATH = os.path.join(os.path.dirname(__file__), "csuf_map.png")

@dataclass
class Edge:
    u: str                              # endpoint A
    v: str                              # endpoint B
    distance: int = 1
    time:int = 1
    accessible: bool = True
    closed: bool = False
    line_id: Optional[int] = None       # to alter elements on canvas later
    text_id: Optional[int] = None       # to track edge weight labels
    
    
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
        # nodes[name] = (x, y, oid, lid), x,y = screen coords for drawing, oid = canvas oval id (circle for node), lid = canvas label id (text for node name) 
        self.nodes: Dict[str, Tuple[int, int, Optional[int], Optional[int]]] = {} 
        self.edges: Dict[FrozenSet[str], Edge] = {} # edges[frozenset({u,v})] = Edge(...)  --> canonical store for each undirected edge
        self.adj: Dict[str, Dict[str, Edge]] = {} # adj[u][v] = Edge(...)  --> adjacency map for traversal (quick neighbor lookup); duplicated in both directions for undirected behavior
        
        
    def add_node(self, name, x, y):  # build a node entry before drawing it on canvas; enforce uniqueness of building names --> building name IS the node id
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
                
    
class GUI:
    NODE_R = 12     # node size control
    ANIM_TRAVERSAL_MS = 600     # ping interval timing
    ANIM_EDGE_MS = 400          # interval between edges turning green 
    ANIM_PING_FLASH_MS = 600    # duration node stays yellow
    ANIM_NODE_MS = 400          # interval between nodes turning green 
    
    def __init__(self, root: tk.Tk):
        self.root = root 
        self.graph = Graph()
        self.mode_place_pending_name: Optional[str] = None
        self.selected_nodes: list[str] = []
        
        self.map_image: Optional[tk.PhotoImage] = None   # cached campus map bitap
        self.map_item: Optional[int] = None              # canvas item id for the map image (to hide/show)
        self.overlay_var = tk.BooleanVar(value = False)   
        
        self.ui_font = tkfont.Font(family="Arial", size=12, weight="normal")            
        self.ui_font_bold = tkfont.Font(family="Arial", size=15, weight="bold")  
        self.root.option_add("*Font", self.ui_font)                     
        self.root.option_add("*Text*Font", self.ui_font)
                        
        style = ttk.Style(self.root)                                    
        style.configure(".", font=self.ui_font)                        
        style.configure("TCombobox", font=self.ui_font)        
        style.theme_use("vista")    # utilize a built-in theme for UI experience        
        self.root.option_add("*TCombobox*Listbox*Font", self.ui_font)          
        
        self.build_layout() # build all frames and widgets
        self.keybind()  # hook hotkeys
        
        self.animating = False
        self.current_animation_tokens: list[int] = []        
        
    
    def build_layout(self):
        self.root.geometry("1200x1030")   

        # grid config so left side expands with window resize           
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_columnconfigure(1, weight=0, minsize=240)
        
        # LEFT SIDE: canvas frame
        self.left = ttk.Frame(self.root)
        self.left.grid(row=0, column=0, sticky="nsew")  
        self.canvas = tk.Canvas(self.left, bg="white")
        self.canvas.pack(fill=tk.BOTH, expand=True)

        # RIGHT SIDE: sidebar
        self.right = ttk.Frame(self.root, width=410)
        self.right.grid(row=0, column=1, sticky="nsw")
        self.right.pack_propagate(False)    # keep fixed width instead of shrinking to children

        box = tk.Frame(self.right, padx=8, pady=8)
        box.pack(fill=tk.Y)
        
        ttk.Label(box, text = "CSUF Default Map Overlay:", font=self.ui_font_bold).pack(anchor="w", pady=(0,4))  # HEADING          
        ttk.Checkbutton(box, text = "Show Map", variable=self.overlay_var, command = self.toggle_map).pack(anchor = "w")   
        
        ttk.Label(box, text = "Add Building:", font=self.ui_font_bold).pack(anchor="w", pady=(29,4))      # HEADING: node controls
        row = ttk.Frame(box)
        row.pack(fill = tk.X)
        self.node_name_var = tk.StringVar()
        ttk.Entry(row, textvariable = self.node_name_var).pack(side = tk.LEFT, fill = tk.X, expand = True)
        ttk.Button(row, text = "Place", command = self.start_node).pack(side = tk.LEFT, padx = (8,0))      
    
        ttk.Label(box, text = "Connect Buildings:", font=self.ui_font_bold).pack(anchor="w", pady=(30, 0))    # HEADING: edge controls
        
        self.selected_label = ttk.Label(box, text = "Currently Selected: ")
        self.selected_label.pack(anchor = "w", pady = (4, 4))
      
        r1 = ttk.Frame(box)
        r1.pack(fill = tk.X, pady = (4, 4))        
        ttk.Label(r1, text = "Distance:").pack(side = tk.LEFT)
        self.dist_var = tk.StringVar(value = "1")
        ttk.Entry(r1, width = 5, textvariable = self.dist_var).pack(side = tk.LEFT, padx = (6, 20))
        
        ttk.Label(r1, text = "Time:").pack(side = tk.LEFT)
        self.time_var = tk.StringVar(value = "1")
        ttk.Entry(r1, width = 5, textvariable = self.time_var).pack(side = tk.LEFT, padx = (6, 12))
        
        self.access_var = tk.BooleanVar(value = True)        
        ttk.Checkbutton(r1, text = "Accessible", variable = self.access_var).pack(side = tk.LEFT, padx = (18, 0))
        
        ttk.Button(box, text="Remove Building", command=self.remove_node_gui).pack(fill=tk.X, pady=(6,3))
        ttk.Button(box, text = "Add Path", command = self.add_edge).pack(fill = tk.X, pady = (3,3))
        ttk.Button(box, text= "Remove Path", command=self.remove_edge_gui).pack(fill=tk.X, pady=(3,3))
        ttk.Button(box, text = "Toggle Closure", command = self.toggle_close).pack(fill = tk.X, pady = (3,3))
        ttk.Button(box, text="Toggle Accessibility", command=self.toggle_accessible).pack(fill=tk.X, pady=(3,3))
        ttk.Button(box, text = "Randomize All Edge Weights", command = self.randomize).pack(fill = tk.X, pady = (3, 0))
                
 
        ttk.Label(box, text = "Route Search:", font=self.ui_font_bold).pack(anchor="w", pady=(30, 4))  # HEADING: route search control

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
        
        self.access_only_var = tk.BooleanVar(value = False)
        ttk.Checkbutton(box, text = "Accessible Only",  variable = self.access_only_var).pack(anchor = "w", pady = (6, 0))
        ttk.Button(box, text = "Run BFS", command = lambda: self.execute_search("bfs")).pack(fill = tk.X, pady = (6, 6))
        ttk.Button(box, text = "Run DFS", command = lambda: self.execute_search("dfs")).pack(fill = tk.X)

        ttk.Label(box, text = "Output:", font=self.ui_font_bold).pack(anchor="w", pady=(30, 4))
        out_frame = ttk.Frame(box)
        out_frame.pack(fill=tk.BOTH, expand=True)
        self.output = tk.Text(out_frame, height=14, wrap="word", state="disabled")
        yscroll = ttk.Scrollbar(out_frame, orient="vertical", command=self.output.yview)
        self.output.configure(yscrollcommand=yscroll.set)
        self.output.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        yscroll.pack(side=tk.RIGHT, fill=tk.Y)
          
            
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
            messagebox.showerror("Error", "Enter a building name")
            return
        if name in self.graph.nodes:
            messagebox.showerror("Error", f"Duplicate node '{name}'")
            return
        self.mode_place_pending_name = name # remember which name will be placed
        self.canvas.configure(cursor = "crosshair")
        self.text_output(f"Click on map to place '{name}'.")
        
        
    def draw_node(self, name, x, y) -> tuple[int, int]:
        r = self.NODE_R
        oid = self.canvas.create_oval(x - r, y - r, x + r, y + r, fill = "black", outline = "black", width = 2, tags = (f"node:{name}",))
        lid = self.canvas.create_text(x, y - r - 10, text = name, font=self.ui_font)
        return oid, lid
    
    
    def draw_edge(self, edge): # draw line between edge.u and edge.v; also draw distance/time label offset from line so its readable
        x_u, y_u, _, _ = self.graph.nodes[edge.u]
        x_v, y_v, _, _ = self.graph.nodes[edge.v]
        edge.line_id = self.canvas.create_line(x_u, y_u, x_v, y_v, fill=edge.color(), width=2)

        lx, ly, ang = self.compute_edge_label_position(edge, offset_px=12) # compute label position slightly off the midpoint normal to the segment

        edge.text_id = self.canvas.create_text(  # draw "d : X,  t : Y" text angled to roughly follow the segment orientation
            lx, ly,
            text=f"d : {edge.distance},  t : {edge.time}",
            font=self.ui_font,
            fill="gray",
            angle=ang,
        )
        self.canvas.tag_raise(edge.text_id) # ensure label not hidden behind line


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
  
    
    def click(self, event): # canvas click handler
        if self.mode_place_pending_name is not None:
            name = self.mode_place_pending_name
            self.mode_place_pending_name = None
            self.canvas.configure(cursor = "")
            try:
                self.graph.add_node(name, event.x, event.y)
                oid, lid = self.draw_node(name, event.x, event.y)              
                x, y, _, _ = self.graph.nodes[name]
                self.graph.nodes[name] = (x, y, oid, lid)
                self.node_name_var.set("")
                self.text_output(f"Added building:  '{name}'")
                self.refresh_node_menu()
            except Exception as exc:
                messagebox.showerror("Error", str(exc))
            return 
        clicked = self.hit_node(event.x, event.y)
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
            self.canvas.coords(edge.text_id, lx, ly)
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
            messagebox.showerror("Error", "Select exactly 1 building to remove")
            return

        name = self.selected_nodes[0]

        if name not in self.graph.nodes:
            messagebox.showerror("Error", "That building no longer exists")
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
        if not start or not goal:
            messagebox.showerror("Error", "Select Start and Goal")
            return
        if start == goal:
            messagebox.showerror("Error", "Start and Goal must differ")
            return
        accessible_only = bool(self.access_only_var.get())
        if algo == "bfs":
            self.text_output(
                f"Navigation System executing Breadth-First Search "
                f"from {start} to {goal} "
                f"(accessible_only = {accessible_only})"
            )
        else:
            self.text_output(
                f"Navigation System executing Depth-First Search "
                f"from {start} to {goal} "
                f"(accessible_only = {accessible_only})"
            )
        try:
            if algo == "bfs":
                path, order, discover = self.graph.bfs(start, goal, accessible_only)
            else:
                path, order, discover = self.graph.dfs(start, goal, accessible_only)
        except Exception as e:
            messagebox.showerror("Error", str(e))
            return
        
        if path:
            self.text_output(
                "Traversal order: "
                f"{order}\n"
                "Computed route: "
                f"{path}\n"
                "Route length (edges): "
                f"{len(path) - 1}\n"
            )
        else:
            self.text_output(
                "Traversal order: "
                f"{order}\n"
                "No valid route was found under current constraints.\n"
            )
            
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
                
                
    def toggle_map(self):
        if self.overlay_var.get():
            # lazy-load once
            if self.map_image is None:
                if not os.path.exists(DEFAULT_MAP_PATH):
                    messagebox.showerror("Error", f"Missing map image:\n{DEFAULT_MAP_PATH}")
                    self.overlay_var.set(False)
                    return
                try:
                    self.map_image = tk.PhotoImage(file = DEFAULT_MAP_PATH)
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to load map: {e}")
                    self.overlay_var.set(False)
                    return
            if self.map_item:
                self.canvas.delete(self.map_item)
            self.map_item = self.canvas.create_image(0, 0, image = self.map_image, anchor = "nw")
            self.canvas.tag_lower(self.map_item)
        else:
            if self.map_item:
                self.canvas.delete(self.map_item)
                self.map_item = None


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

    
def main():
    root = tk.Tk()
    root.title("CPSC 335 - Interactive Campus Navigation System (BFS/DFS)")
    GUI(root)
    root.mainloop()

    
if __name__ == "__main__":
    main()
