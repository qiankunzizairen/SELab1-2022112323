import networkx as nx

# 被测函数（放在测试文件中）
def calc_shortest_path(G, word1, word2):
    try:
        return nx.shortest_path(G, word1, word2, weight="weight")
    except nx.NetworkXNoPath:
        return None
    except nx.NodeNotFound:
        return None

# 测试用例 TC3：word1 或 word2 不存在于图中
def test_TC3_node_not_found():
    G = nx.DiGraph()
    G.add_edge("quick", "brown")
    G.add_edge("brown", "fox")

    result = calc_shortest_path(G, "banana", "fox")
    assert result is None