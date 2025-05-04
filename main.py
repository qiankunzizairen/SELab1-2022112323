#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Text → Directed-Graph GUI Analyzer · Ver. 2025-05-02 (＋Shortest-Path Highlight)
"""

import re
import random
import math
import threading
from pathlib import Path
from typing import Optional, Set, Tuple, Iterable

import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, scrolledtext

import networkx as nx
import matplotlib

matplotlib.use("TkAgg")
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from pkg_resources import parse_version   # 仅作版本判断，可自行替换

# ─────────────────────────────────────────────────────────────────────────────
# 实用函数
# ─────────────────────────────────────────────────────────────────────────────
ALPHA_PATTERN = re.compile(r"[^A-Za-z]+")


def tokenize(text: str) -> list[str]:
    text = text.lower()
    clean = ALPHA_PATTERN.sub(" ", text)
    return clean.split()


def bridge_words(G: nx.DiGraph, w1: str, w2: str) -> list[str]:
    """两词 w1→w2 的桥接中介词"""
    if w1 not in G or w2 not in G:
        return []
    return [mid for mid in G.successors(w1) if G.has_edge(mid, w2)]


def pagerank_with_dangling(
    G: nx.DiGraph, d: float = 0.85, tol: float = 1e-10, max_iter: int = 100
) -> dict[str, float]:
    """含悬挂节点修正的 PageRank 实现"""
    if len(G) == 0:
        return {}
    N = len(G)
    nodes = list(G)
    succ = {u: list(G.successors(u)) for u in nodes}
    pr = {u: 1.0 / N for u in nodes}

    for _ in range(max_iter):
        prev = pr.copy()
        dangling = sum(prev[u] for u in nodes if len(succ[u]) == 0)
        for u in nodes:
            s = dangling / N + sum(prev[v] / len(succ[v]) for v in G.predecessors(u))
            pr[u] = (1 - d) / N + d * s
        if sum(abs(pr[u] - prev[u]) for u in nodes) < tol:
            break
    return pr


# ─────────────────────────────────────────────────────────────────────────────
# 主应用
# ─────────────────────────────────────────────────────────────────────────────
class TextGraphApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Text Graph Analyzer")
        self.geometry("1280x900")

        # ── 图数据与高亮信息
        self.G: nx.DiGraph = nx.DiGraph()
        self._hl_edges: Set[Tuple[str, str]] = set()
        self._hl_nodes: Set[str] = set()

        # ── 画布
        self.figure = Figure(figsize=(8, 8), dpi=100)
        self.ax = self.figure.add_subplot(111)
        self.canvas = FigureCanvasTkAgg(self.figure, master=self)
        self.canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=1)

        # ── 状态栏
        self.status_var = tk.StringVar(value="请先『文件 → 打开文本』")
        tk.Label(self, textvariable=self.status_var, relief=tk.SUNKEN).pack(
            side=tk.BOTTOM, fill=tk.X
        )

        # 随停随机游走
        self._walk_stop_event: threading.Event | None = None

        self._build_menu()

    # ═══════════════════════════════════════════════════════════════════════
    # GUI 菜单
    # ═══════════════════════════════════════════════════════════════════════
    def _build_menu(self):
        menubar = tk.Menu(self)

        file_menu = tk.Menu(menubar, tearoff=False)
        file_menu.add_command(label="打开文本文件…", command=self.load_file)
        file_menu.add_command(label="保存当前图像…", command=self.save_graph_png)
        file_menu.add_separator()
        file_menu.add_command(label="退出", command=self.destroy)
        menubar.add_cascade(label="文件", menu=file_menu)

        func_menu = tk.Menu(menubar, tearoff=False)
        func_menu.add_command(label="桥接词查询", command=self.func_bridge)
        func_menu.add_command(label="插入桥接词生成新文本", command=self.func_transform_sentence)
        func_menu.add_command(label="最短路径查询并高亮", command=self.func_shortest_path)
        func_menu.add_command(label="PageRank 计算", command=self.func_pagerank)
        func_menu.add_command(label="随机游走", command=self.func_random_walk)
        menubar.add_cascade(label="功能", menu=func_menu)

        layout_menu = tk.Menu(menubar, tearoff=False)
        layout_menu.add_command(label="重新布局", command=self.draw_graph)
        menubar.add_cascade(label="布局", menu=layout_menu)

        self.config(menu=menubar)

    # ═══════════════════════════════════════════════════════════════════════
    # 文件读入
    # ═══════════════════════════════════════════════════════════════════════
    def load_file(self):
        path = filedialog.askopenfilename(
            title="选择英文文本文件",
            filetypes=[("Text files", "*.txt *.md *.log"), ("All files", "*.*")]
        )
        if not path:
            return

        words: list[str] = []
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                words.extend(tokenize(line))

        self.G.clear()
        for a, b in zip(words, words[1:]):
            if a and b:
                self.G.add_edge(
                    a, b,
                    weight=self.G[a][b]["weight"] + 1 if self.G.has_edge(a, b) else 1
                )

        self._hl_edges.clear(); self._hl_nodes.clear()
        self.status_var.set(f"文件载入成功：{len(self.G)} 节点，{self.G.size()} 条边")
        self.draw_graph()

    # ═══════════════════════════════════════════════════════════════════════
    # 多级回退布局
    # ═══════════════════════════════════════════════════════════════════════
    def _compute_layout(self):
        if len(self.G) == 0:
            return {}

        # 1) Graphviz-dot（优先）
        for backend in ("nx_agraph", "nx_pydot"):
            try:
                if hasattr(nx, backend):
                    return getattr(nx, backend).graphviz_layout(self.G, prog="dot")
            except Exception:
                pass

        # 2) Kamada–Kawai（中小图）
        try:
            return nx.kamada_kawai_layout(self.G, scale=2.5)
        except Exception:
            pass

        # 3) 加强版 spring_layout
        k = 2.2 / math.sqrt(len(self.G))
        return nx.spring_layout(self.G, k=k, iterations=400, seed=42, scale=2.5)

    # ═══════════════════════════════════════════════════════════════════════
    # 绘图：支持路径高亮
    # ═══════════════════════════════════════════════════════════════════════
    def draw_graph(
        self,
        highlight_edges: Optional[Iterable[Tuple[str, str]]] = None,
        highlight_nodes: Optional[Iterable[str]] = None,
    ):
        """重新绘制整图；可选高亮边/点"""
        if highlight_edges is not None:
            self._hl_edges = set(highlight_edges)
        if highlight_nodes is not None:
            self._hl_nodes = set(highlight_nodes)

        self.ax.clear()

        if len(self.G) == 0:
            self.ax.text(
                0.5, 0.5,
                "当前无图数据，请先加载文本文件。",
                ha="center", va="center", fontsize=14
            )
            self.canvas.draw()
            return

        pos = self._compute_layout()

        # ── 1. 节点
        node_colors = [
            "#ff6347" if n in self._hl_nodes else "#ffc966"   # Tomato / 默认
            for n in self.G.nodes()
        ]
        node_artist = nx.draw_networkx_nodes(
            self.G, pos, ax=self.ax,
            node_size=650, node_color=node_colors, edgecolors="#333333", linewidths=0.8
        )
        node_artist.set_zorder(2)

        # ── 2. 边
        use_margin = parse_version(nx.__version__) >= parse_version("3.1")
        for u, v in self.G.edges():
            is_hl = (u, v) in self._hl_edges
            kwargs = dict(
                edge_color="#ff6347" if is_hl else "#6c81d9",
                width=2.4 if is_hl else 1.0,
                arrows=True, arrowstyle="-|>", arrowsize=14,
                connectionstyle=f"arc3,rad={0.15 if self.G.has_edge(v,u) and u!=v else 0.0}"
            )
            if use_margin:
                kwargs.update(min_source_margin=12, min_target_margin=18)

            ec = nx.draw_networkx_edges(self.G, pos, edgelist=[(u, v)], ax=self.ax, **kwargs)
            (ec if isinstance(ec, list) else [ec])[0].set_zorder(3)

        # ── 3. 标签
        text_nodes = nx.draw_networkx_labels(self.G, pos, ax=self.ax, font_size=9)
        for t in text_nodes.values():
            t.set_zorder(4)

        edge_labels = {(u, v): d["weight"] for u, v, d in self.G.edges(data=True)}
        text_edges = nx.draw_networkx_edge_labels(
            self.G, pos, edge_labels=edge_labels, ax=self.ax,
            font_size=8,
            bbox=dict(boxstyle="round,pad=0.1", fc="white", alpha=0.7)
        )
        for t in text_edges.values():
            t.set_zorder(4)

        self.ax.axis("off")
        self.figure.tight_layout()
        self.canvas.draw()

    # ═══════════════════════════════════════════════════════════════════════
    # 其余功能
    # ═══════════════════════════════════════════════════════════════════════
    def save_graph_png(self):
        if len(self.G) == 0:
            messagebox.showwarning("提示", "当前没有可保存的图形，请先加载文本。")
            return
        out = filedialog.asksaveasfilename(
            title="保存 PNG", defaultextension=".png", filetypes=[("PNG Image", "*.png")]
        )
        if out:
            self.figure.savefig(out, dpi=300)
            messagebox.showinfo("保存成功", f"图像已保存至\n{Path(out).resolve()}")

    # ── 桥接词
    def func_bridge(self):
        if len(self.G) == 0:
            messagebox.showwarning("提示", "请先加载文本。")
            return
        w1 = simpledialog.askstring("桥接词查询", "输入 word1：")
        if not w1:
            return
        w2 = simpledialog.askstring("桥接词查询", "输入 word2：")
        if not w2:
            return
        w1, w2 = w1.lower(), w2.lower()
        bridges = bridge_words(self.G, w1, w2)
        msg = "无桥接关系！" if not bridges else "桥接词：" + ", ".join(sorted(set(bridges)))
        messagebox.showinfo("桥接词查询", msg)

    # ── 插入桥接词生成句子
    def func_transform_sentence(self):
        if len(self.G) == 0:
            messagebox.showwarning("提示", "请先加载文本。")
            return

        top = tk.Toplevel(self)
        top.title("插入桥接词生成新文本")
        tk.Label(top, text="输入待处理英文句子：").pack(anchor="w", padx=6, pady=4)
        entry = scrolledtext.ScrolledText(top, width=80, height=5, wrap=tk.WORD)
        entry.pack(padx=6, pady=4)
        outbox = scrolledtext.ScrolledText(top, width=80, height=7, wrap=tk.WORD, state=tk.DISABLED)
        outbox.pack(padx=6, pady=4)

        def process():
            text = entry.get("1.0", tk.END).strip()
            words = tokenize(text)
            if len(words) < 2:
                messagebox.showwarning("提示", "句子至少含两个单词。")
                return
            res = []
            for a, b in zip(words, words[1:]):
                res.append(a)
                mids = bridge_words(self.G, a, b)
                if mids:
                    res.append(random.choice(mids))
            res.append(words[-1])
            new_sentence = " ".join(res)
            outbox.configure(state=tk.NORMAL)
            outbox.delete("1.0", tk.END)
            outbox.insert(tk.END, new_sentence)
            outbox.configure(state=tk.DISABLED)

        tk.Button(top, text="生成", command=process, width=10).pack(pady=4)
        tk.Button(top, text="关闭", command=top.destroy, width=10).pack(pady=2)

    # ── 最短路径并高亮
    def func_shortest_path(self):
        if len(self.G) == 0:
            messagebox.showwarning("提示", "请先加载文本。")
            return
        w1 = simpledialog.askstring("最短路径", "输入源单词：")
        if not w1:
            return
        w2 = simpledialog.askstring("最短路径", "输入目标单词：")
        if not w2:
            return
        w1, w2 = w1.lower(), w2.lower()
        if w1 not in self.G or w2 not in self.G:
            messagebox.showwarning("提示", "源或目标单词不存在图中！")
            return
        try:
            path = nx.shortest_path(self.G, w1, w2, weight="weight")
            path_edges = set(zip(path, path[1:]))
            length = sum(self.G[u][v]["weight"] for u, v in path_edges)
            self.draw_graph(path_edges, path)    # ← 高亮
            messagebox.showinfo(

                "最短路径",
                f"{' → '.join(path)}\n路径权值和 = {length}"
            )
        except nx.NetworkXNoPath:
            messagebox.showinfo("最短路径", "两节点不可达。")

    # ── PageRank
    def func_pagerank(self):
        if len(self.G) == 0:
            messagebox.showwarning("提示", "请先加载文本。")
            return
        pr = pagerank_with_dangling(self.G)
        ranked = sorted(pr.items(), key=lambda x: x[1], reverse=True)
        top = tk.Toplevel(self)
        top.title("PageRank 结果")
        box = scrolledtext.ScrolledText(top, width=50, height=25)
        box.pack(padx=6, pady=6)
        for i, (w, score) in enumerate(ranked, 1):
            box.insert(tk.END, f"{i:>3}. {w:<20} {score:.6f}\n")
        box.configure(state=tk.DISABLED)
        tk.Button(top, text="关闭", command=top.destroy).pack(pady=4)

    # ── 随机游走
    def func_random_walk(self):
        if len(self.G) == 0:
            messagebox.showwarning("提示", "请先加载文本。")
            return
        top = tk.Toplevel(self)
        top.title("随机游走")
        tk.Label(top, text="随机游走结果：").pack(anchor="w", padx=6, pady=4)
        outbox = scrolledtext.ScrolledText(top, width=80, height=20, state=tk.DISABLED)
        outbox.pack(padx=6, pady=4)

        save_path = filedialog.asksaveasfilename(
            title="保存游走路径 (TXT)", defaultextension=".txt",
            filetypes=[("Text file", "*.txt")]
        )
        if not save_path:
            top.destroy()
            return

        self._walk_stop_event = threading.Event()

        def start_walk():
            outbox.configure(state=tk.NORMAL); outbox.delete("1.0", tk.END); outbox.configure(state=tk.DISABLED)
            self._walk_stop_event.clear()
            threading.Thread(target=walk_thread, daemon=True).start()

        def stop_walk():
            if self._walk_stop_event:
                self._walk_stop_event.set()

        def walk_thread():
            node = random.choice(list(self.G))
            visited, edges = [node], set()
            with open(save_path, "w", encoding="utf-8") as f:
                f.write(f"{node}\n")
                while not self._walk_stop_event.is_set():
                    succ = list(self.G.successors(node))
                    if not succ:
                        break
                    next_node = random.choice(succ)
                    if (node, next_node) in edges:  # 第一次遇到重复边即停止
                        break
                    edges.add((node, next_node))
                    node = next_node
                    visited.append(node)
                    f.write(f"{node}\n")
                    outbox.configure(state=tk.NORMAL)
                    outbox.insert(tk.END, f"{node}\n"); outbox.see(tk.END)
                    outbox.configure(state=tk.DISABLED)
            messagebox.showinfo(
                "随机游走",
                f"结束，共访问 {len(visited)} 节点。\n结果已保存至 {Path(save_path).resolve()}"
            )

        btn = tk.Frame(top); btn.pack(pady=4)
        tk.Button(btn, text="开始", command=start_walk, width=8).pack(side=tk.LEFT, padx=4)
        tk.Button(btn, text="停止", command=stop_walk, width=8).pack(side=tk.LEFT, padx=4)
        tk.Button(btn, text="关闭", command=top.destroy, width=8).pack(side=tk.LEFT, padx=4)


# ─────────────────────────────────────────────────────────────────────────────
# main
# ─────────────────────────────────────────────────────────────────────────────
def main():
    TextGraphApp().mainloop()


if __name__ == "__main__":
    main()