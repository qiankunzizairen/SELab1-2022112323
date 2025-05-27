import networkx as nx

# 在测试文件中直接定义要测试的逻辑函数
def calc_shortest_path(G, word1, word2):
    try:
        return nx.shortest_path(G, word1, word2, weight="weight")
    except nx.NetworkXNoPath:
        return None
    except nx.NodeNotFound:
        return None

# 测试用例 TC1：存在最短路径
def test_TC1_path_exists():
    G = nx.DiGraph()
    G.add_edge("quick", "brown")
    G.add_edge("brown", "fox")

    result = calc_shortest_path(G, "quick", "fox")
    assert result == ["quick", "brown", "fox"]