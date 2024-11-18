from simulator.node import Node
import json
import heapq


class Link_State_Node(Node):
    def __init__(self, id):
        super().__init__(id)
        self.dataBase = {}
        self.sequenceNumbers = {}
        self.neighbors = {}

    # Return a string
    def __str__(self):
        return (
            f"Node {self.id}\n"
            f"Neighbors: {self.neighbors}\n"
            f"Database: {self.dataBase}\n"
            f"Sequence Numbers: {self.sequenceNumbers}\n"
        )


    # Fill in this function
    def link_has_been_updated(self, neighbor, latency):
        # latency = -1 if delete a link
        if latency == -1: #delete the link if -1
            if neighbor in self.neighbors:
                del self.neighbors[neighbor]
            latency = float('inf')
        else:
            self.neighbors[neighbor] = latency #update the cost
        
        sequenceNumber = self.sequenceNumbers.get((self.id, neighbor), 0)
        newSequenceNumber = sequenceNumber +  1
        self.sequenceNumbers[(self.id, neighbor)] = newSequenceNumber
        self.dataBase[(self.id, neighbor)] = latency #update in the database
        link_dict = { #dictionary
            'src' : self.id,
            'dst' : neighbor,
            'cost' : latency,
            'seq_num' : newSequenceNumber
        }
        self.floodToState(link_dict) #flood to other links
        if latency == float('inf'): # handle the infinity
            updateDatabase = {}
            for (source, destination), cost in self.dataBase.items():
                if source != neighbor and destination != neighbor:
                    updateDatabase[(source, destination)] = cost
            self.dataBase = updateDatabase
            updateSequenceNumbers = {}

            for (source, destination), sequenceNumber in self.sequenceNumbers.items():
                if source != neighbor and destination != neighbor:
                    updateSequenceNumbers[(source, destination)] = sequenceNumber
            self.sequenceNumbers  = updateSequenceNumbers
        
        self.refloodToLinks() 


        

    # Fill in this function
    def process_incoming_routing_message(self, m):
        message = json.loads(m)
        source = message['src']
        destination  = message['dst']
        cost = message['cost']
        sequenceNumber = message['seq_num']

        if (source, destination) not in self.sequenceNumbers or sequenceNumber > self.sequenceNumbers[(source, destination)]:
            if cost == float('inf'):
                if (source, destination) in self.dataBase:
                    del self.dataBase[(source, destination)]
            else:
                self.dataBase[(source, destination)] = cost
            self.sequenceNumbers[(source, destination)] = sequenceNumber
            self.floodToState(message)
    
    def floodToState(self, link_dict):
        message = json.dumps(link_dict)
        self.send_to_neighbors(message)

    def refloodToLinks(self):
        for (source, destination), cost in self.dataBase.items():
            sequenceNumber = self.sequenceNumbers.get((source, destination), 0)
            link_dict = {
                'src': source,
                'dst': destination,
                'cost': cost,
                'seq_num': sequenceNumber
            }
            self.floodToState(link_dict)


    def get_next_hop(self, destination):
        visited = set()
        distances = {self.id : 0}
        previousNodes = {self.id : None}
        pq = [(0, self.id)] #heap
        while pq: #iterate until the heap is null
            currentDistance, currentNode = heapq.heappop(pq)

            if currentNode == destination:
                while previousNodes[currentNode] != self.id:
                    currentNode = previousNodes[currentNode]
                return currentNode
            
            visited.add(currentNode)#mark visited
            
            for (source, dst), cost in self.dataBase.items():
                if source == currentNode:
                    neighbor = dst
                elif dst == currentNode:
                    neighbor = source
                else:
                    continue

                if neighbor in visited:
                    continue

                updateDistance = currentDistance + cost

                if neighbor not in distances or updateDistance < distances[neighbor]:
                    distances[neighbor] = updateDistance
                    previousNodes[neighbor] = currentNode
                    heapq.heappush(pq, (updateDistance, neighbor) )

        return -1