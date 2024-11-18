from simulator.node import Node
import json

class Distance_Vector_Node(Node):
    def __init__(self, id):
        super().__init__(id)
        self.distance_vector = {self.id: (0, self.id, [self.id])}
        self.neighbors = {}

    def __str__(self):
        dv_str = ", ".join([f"{d}: (cost={c}, next_hop={h}, path={p})"
                            for d, (c, h, p) in self.distance_vector.items()])
        return f"Node {self.id} - Distance Vector: [{dv_str}]"

    def link_has_been_updated(self, neighbor, latency):
        neighbor = int(neighbor)

        if latency == -1:
            if neighbor in self.neighbors:
                self.logging.debug(f"Deleting link to neighbor {neighbor} at Node {self.id}")
                del self.neighbors[neighbor]
                self.invalidate_paths(neighbor)
        else:
            self.logging.debug(f"Updating link to neighbor {neighbor} with latency {latency} at Node {self.id}")
            old_latency = self.neighbors.get(neighbor, float('inf'))
            self.neighbors[neighbor] = latency

            # If the link cost increased, invalidate affected paths
            if latency > old_latency:
                self.invalidate_paths(neighbor)

        # Update the distance vector for this direct neighbor
        updated = False
        if neighbor not in self.distance_vector or self.distance_vector[neighbor][0] > latency:
            self.distance_vector[neighbor] = (latency, neighbor, [self.id, neighbor])
            updated = True

        if updated:
            self.flood_distance_vector()

    def invalidate_paths(self, neighbor):
        updated = False
        to_remove = []

        for destination, (cost, next_hop, path) in self.distance_vector.items():
            if neighbor in path and next_hop == neighbor:
                to_remove.append(destination)

        # Remove invalid paths
        for destination in to_remove:
            del self.distance_vector[destination]
            updated = True
            self.logging.debug(f"Invalidated path to {destination} via {neighbor} at Node {self.id}")

        if updated:
            self.flood_distance_vector()

    def process_incoming_routing_message(self, m):
        message = json.loads(m)
        sender = int(message["sender"])
        incoming_vector = message["distance_vector"]
        self.logging.debug(f"Received routing message from {sender}: {incoming_vector}")
        updated = False

        if sender not in self.neighbors:
            self.logging.warning(f"Unknown sender {sender}, adding with infinite cost")
            self.neighbors[sender] = float('inf')

        for destination, (cost_to_dest, next_hop, path) in incoming_vector.items():
            destination = int(destination)
            cost_to_dest = float(cost_to_dest)
            next_hop = int(next_hop)
            path = [int(node) for node in path]

            if self.id in path:
                self.logging.debug(f"Detected loop for destination {destination}, skipping update")
                continue

            link_cost = self.neighbors.get(sender, float('inf'))
            new_cost = cost_to_dest + link_cost
            new_path = path + [self.id]

            if destination not in self.distance_vector:
                self.distance_vector[destination] = (new_cost, sender, new_path)
                updated = True
            else:
                current_cost, current_hop, current_path = self.distance_vector[destination]
                if new_cost < current_cost:
                    self.distance_vector[destination] = (new_cost, sender, new_path)
                    updated = True

        if updated:
            self.flood_distance_vector()

    def get_next_hop(self, destination):
        destination = int(destination)
        if destination in self.distance_vector:
            next_hop = self.distance_vector[destination][1]
            return next_hop
        return -1

    def flood_distance_vector(self):
        message = json.dumps({
            "sender": self.id,
            "distance_vector": {str(dest): [cost, next_hop, path]
                                for dest, (cost, next_hop, path) in self.distance_vector.items()}
        })
        self.send_to_neighbors(message)
