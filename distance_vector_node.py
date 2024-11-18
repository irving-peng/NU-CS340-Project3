import json
from simulator.node import Node

# Helper class for storing and managing distance vector information.
class Distance_Vector:
    def __init__(self, cost: int, path: list):
        self.cost = cost
        self.path = path if isinstance(path, list) else []

    def from_str(self, message: str):
        try:
            data = json.loads(message)
            self.from_map(data)
        except json.JSONDecodeError:
            print("Error: Invalid JSON format in from_str.")

    def from_map(self, json_value: dict):
        if not isinstance(json_value, dict):
            raise ValueError("Input must be a dictionary.")
        
        self.cost = int(json_value.get("cost", float('inf')))
        self.path = json_value.get("path", [])
        if not isinstance(self.path, list):
            self.path = []

    def __str__(self):
        return json.dumps(self.as_dict())

    def __repr__(self):
        return self.__str__()

    def __eq__(self, other):
        if not isinstance(other, Distance_Vector):
            return False
        return self.cost == other.cost and self.path == other.path

    def as_dict(self):
        return {"cost": self.cost, "path": self.path}


class Distance_Vector_Node(Node):
    def __init__(self, node_id):
        super().__init__(node_id)
        self.my_dvs = {}  
        self.neighbor_dvs = {}  
        self.neighbor_seq_nums = {}  # Tracks sequence numbers for neighbors
        self.link_costs = {}  
        self.seq_num = 0  # Sequence number for this node's messages

    def __str__(self):
        message = {dst: dv.as_dict() for dst, dv in self.my_dvs.items()}  
        message[-1] = self.seq_num
        # Increment the sequence number for the next message
        self.seq_num += 1
        return json.dumps(message)

    def link_has_been_updated(self, neighbor, latency):
        if latency == -1:
            self.link_costs.pop(neighbor, None)
            self.neighbor_dvs.pop(neighbor, None)
        else:
            self.link_costs[neighbor] = latency
        # Recompute the distance vectors after updating the link
        self.recompute_dvs()

    def recompute_dvs(self):
        old_dvs = self.my_dvs.copy()
        self.my_dvs.clear()
        for neighbor, link_cost in self.link_costs.items():
            self.my_dvs[neighbor] = Distance_Vector(cost=link_cost, path=[self.id, neighbor])
        # Update the distance vectors using information from neighbors
        for source, dvs in self.neighbor_dvs.items():
            for destination, dv in dvs.items():
                self.recompute_single_dv(src=source, dst=destination, dv=dv)
        # Broadcast the updated distance vectors if any changes were detected
        if self.my_dvs != old_dvs:
            self.broadcast_to_neighbors()

    def recompute_single_dv(self, src: int, dst: int, dv: Distance_Vector):
        # Ensure the source neighbor exists in the link costs
        link_cost = self.link_costs.get(src)
        if link_cost is None:
            return
        new_cost = dv.cost + link_cost
        # Check if we need to update the current distance vector for the destination
        current_dv = self.my_dvs.get(dst)
        if current_dv is None or new_cost < current_dv.cost:
            # Update the distance vector with a new path
            new_path = [self.id] + dv.path
            self.my_dvs[dst] = Distance_Vector(cost=new_cost, path=new_path)

    def broadcast_to_neighbors(self):
        message = str(self)
        self.send_to_neighbors(message)

    def process_incoming_routing_message(self, m):
        neighbor_dvs = json.loads(m)
        seq_num = neighbor_dvs.pop("-1")
        changed = False
        neighbor = int(neighbor_dvs[next(iter(neighbor_dvs))]['path'][0])
        if neighbor not in self.neighbor_dvs:
            self.neighbor_dvs[neighbor] = {}
        # Ignore the message if the sequence number is outdated
        if neighbor in self.neighbor_seq_nums and seq_num <= self.neighbor_seq_nums[neighbor]:
            return
        to_delete = list(self.neighbor_dvs[neighbor].keys())
        # Process each destination in the incoming message
        for dst_str, value in neighbor_dvs.items():
            dst = int(dst_str)
            # Remove the destination from the deletion list if it's in the incoming message
            if dst in to_delete:
                to_delete.remove(dst)
            link = Distance_Vector(cost=value['cost'], path=value['path'])
            # Update the DV table and track changes
            if self.process_neighbor_dv(src=neighbor, dst=dst, dv=link, seq_num=seq_num):
                changed = True
        # Delete any remaining destinations not in the incoming message
        for dst in to_delete:
            del self.neighbor_dvs[neighbor][dst]
            changed = True
        self.neighbor_seq_nums[neighbor] = seq_num
        # Recompute DVs if there were any changes
        if changed:
            self.recompute_dvs()

    def process_neighbor_dv(self, src: int, dst: int, dv: Distance_Vector, seq_num: int):
        if dst in self.neighbor_dvs[src]:
            # Loop prevention: if the current node ID is in the path, delete the entry
            if self.id in dv.path:
                del self.neighbor_dvs[src][dst]
                return True
            self.neighbor_dvs[src][dst] = dv
            return True
        else:
            if self.id in dv.path:
                return False
            # Add the new entry to the neighbor's DV table
            self.neighbor_dvs[src][dst] = dv
            return True

    def get_next_hop(self, destination):
        # Check if the destination is in the current distance vectors
        if destination in self.my_dvs:
            dv = self.my_dvs[destination]
            if dv.cost < float('inf'):
                # Return the next hop from the path (second element)
                return dv.path[1]
        #no valid next hop
        return -1
