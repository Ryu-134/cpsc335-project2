# Student Name: Casey Dane  
# Titan Email: crdane@csu.fullerton.edu
# Project: CPSC 335 – Interactive Campus Navigation System
# Date: 10/24/2025


import tkinter as tk
from tkinter import ttk, messagebox
from dataclasses import dataclass
from typing import Optional, FrozenSet, Dict, Tuple

@dataclass
class Edge:
    u: str
    v: str
    distance: int = 1
    time:int = 1
    accessible: bool = True
    closed: bool = False
    line_id: Optional[int] = None   # line
    text_id: Optional[int] = None   # label
    
    
    def key(self) -> FrozenSet[str]:
        return frozenset({self.u, self.v})  # make sure each edge unique

    def color(self) -> str:
        if self.closed:
            return "red"
        if not self.accessible:
            return "orange"
        return "gray"

class Graph:
    def __init__(self):
        self.nodes: Dict[str, Tuple[int, int, Optional[int], Optional[int]]] = {}
        self.edges: Dict[FrozenSet[str], Edge] = {}
        self.adj: Dict[str, Dict[str, Edge]] = {}
        
    def add_node(self, name, x, y):
        if name in self.nodes:
            raise ValueError(f"Duplicate node '{name}'")    # CHECK --> no duplicate nodes 
        self.nodes[name] = (x, y, None, None)
        self.adj[name] = {}
        
    def add_edge(self, u, v, distance, time, accessible) -> Edge:
        if u == v:
            raise ValueError("Cannot connect a node to itself")     # CHECK --> no self-looping nodes 
        if u not in self.nodes or v not in self.nodes:
            raise ValueError("Both endpoints must exist")   # CHECK --> both nodes must exist      
        key = frozenset({u, v})
        if key in self.edges:
            raise ValueError("Edge already exists")     
        e = Edge(u, v, distance, time, accessible)
        self.edges[key] = e
        self.adj[u][v] = e
        self.adj[v][u] = e
        return e
    
    def get_edge(self, u, v):
        return self.edges.get(frozenset({u, v}))



def main():
    root = tk.Tk()
    root.title("CPSC 335 - Interactive Campus Navigation System (BFS/DFS)")
    tk.Canvas(root, bg = "white", width = 800, height = 600).pack(fill = tk.BOTH, expand = True)
    root.mainloop()

    
if __name__ == "__main__":
    main()
