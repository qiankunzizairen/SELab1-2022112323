import networkx as nx

# 被测函数，直接定义在测试文件中
def calc_shortest_path(G, word1, word2):
    try:
        return nx.shortest_path(G, word1, word2, weight="weight")
    except nx.NetworkXNoPath:
        return None
    except nx.NodeNotFound:
        return None

# 测试用例 TC2：节点存在但不可达
def test_TC2_no_path():
    G = nx.DiGraph()
    G.add_edge("quick", "brown")
    G.add_edge("brown", "fox")
    G.add_edge("lazy", "dog")  # lazy 与 quick 无连接

    result = calc_shortest_path(G, "lazy", "quick")
    assert result is None