import math
import networkx as nx
import random

TOP_LEVEL_PG_LOCATION = (300, 100)

def generate_layout(elements):
    """
    Generate a set of x,y positions given a set of elements and connections
    :param elements: The elements to deploy
    :type elements: list(model.FlowElement)
    """
    G = nx.Graph()  # Initialize an empty graph

    initial_positions = {}  # Maintain a set of starting positions. Used to optimize graph layout. 
    for el in elements.values():
        G.add_node(el.name)  # Add a node to the graph
        if len(G) == 1:  # is this the first node? If so, fix it to the top of the canvas
            initial_positions[el.name] = TOP_LEVEL_PG_LOCATION

    # Add all connections as edges
    for el in elements.values():
        if el.connections:
            for c in el.connections:
                G.add_edge(el.name, c.name)

    scale = 100 * len(G.nodes)  # Make the canvas size scale with the total number of elements

    # Run the force directed layout algorithm
    positions = nx.spring_layout(G, scale=scale, center=TOP_LEVEL_PG_LOCATION, pos=initial_positions, k=100)

    # Convert [x,y] to (x,y) since nipyapi expects a tuple
    for name, pos in positions.items():
        positions[name] = tuple(pos)

    return positions
