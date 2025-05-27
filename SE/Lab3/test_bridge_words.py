import networkx as nx
from main import bridge_words 

# 构建用于测试的图（根据已有文本模拟）
def build_sample_graph():
    G = nx.DiGraph()
    words = ["the", "quick", "brown", "fox", "jumps", "over", "the", "lazy", "dog"]
    for a, b in zip(words, words[1:]):
        G.add_edge(a, b)
    return G

# === 测试用例 ===

def test_TC1():
    """有效等价类 (1): 存在桥接词"""
    G = build_sample_graph()
    result = bridge_words(G, "quick", "fox")
    assert "brown" in result

def test_TC2():
    """有效等价类 (2): 没有桥接词"""
    G = build_sample_graph()
    result = bridge_words(G, "lazy", "dog")
    assert result == []

def test_TC3():
    """有效等价类 (3): 方向不通"""
    G = build_sample_graph()
    result = bridge_words(G, "fox", "quick")
    assert result == []

def test_TC4():
    """无效等价类 (4): w2 不存在"""
    G = build_sample_graph()
    result = bridge_words(G, "quick", "banana")
    assert result == []

def test_TC5():
    """无效等价类 (5): w1 不存在"""
    G = build_sample_graph()
    result = bridge_words(G, "banana", "quick")
    assert result == []

def test_TC6():
    """无效等价类 (6): w1 和 w2 都不存在"""
    G = build_sample_graph()
    result = bridge_words(G, "apple", "banana")
    assert result == []