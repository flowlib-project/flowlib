import networkx as nx
import random

from flowlib.exceptions import FlowLibException
from nipyapi.nifi import PositionDTO

TOP_LEVEL_PG_LOCATION = (300, 100)
DEFAULT_POSITION = PositionDTO(x=float(100), y=float(100))

def generate_top_level_pg_positions(elements):
    n = 400
    x, y = 1, 1
    positions = dict()
    for i, el in enumerate(elements):
        positions[el.component.name] = PositionDTO(x=float(x*n), y=float(y*n))

        if x % 4 == 0:
            x = 1
            y += 1
        else:
            x += 1

    return positions


def generate_layout(elements, layout_type="spring"):
    """
    Generate a set of x,y positions given a set of elements and connections
    :param elements: The elements to deploy
    :type elements: list(model.FlowElement)
    :param layout_type: The type of layout (e.g., spring, planar)
    :type layout_type: str
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

    scale = 125 * len(G.nodes)  # Make the canvas size scale with the total number of elements

    if layout_type == "spring":
        positions = nx.spring_layout(G, scale=scale, center=TOP_LEVEL_PG_LOCATION, pos=initial_positions, k=100)
    elif layout_type == "planar":
        positions = nx.planar_layout(G, scale=scale, center=TOP_LEVEL_PG_LOCATION)
    elif layout_type == "spectral":
        positions = nx.spectral_layout(G, scale=scale, center=TOP_LEVEL_PG_LOCATION)
    else:
        raise FlowLibException("Unsupported Graph Layout Type: {}".format(type))

    # Convert [x,y] to (x,y) since nipyapi expects a tuple
    for name, pos in positions.items():
        positions[name] = tuple(pos)

    return positions
