
from mclbn256 import Fr, G1, G2

class Header:
    
    def __init__(self,message=None):
        if message is not None:
            self.decode(message)
    
    def encode(self):
        return [self.alpha] + self.beta + [self.gamma, self.credential]

    def decode(self, message):
        self.alpha, *self.beta, self.gamma, self.credential = message


    def build(self, destination, mixes, shared_secrets, credential, alpha, G_i):
        # self.next_hop = inverse_map(mixes[0]) # ip        
        self.alpha = alpha                 # G1
        self.credential = credential       # G1
        self.beta, self.gamma = self._compute_layers(destination, mixes, shared_secrets, G_i)

    def _compute_layers(self, destination, mixes, shared_secrets, G_i):

        def initial_layer(destination, s): 
            beta = [
                destination + G_i[0] * s[2],
                - (G_i[-4] * s[1] + G_i[-2] * s[0]),
                - (G_i[-3] * s[1] + G_i[-1] * s[0]),
                -  G_i[-2] * s[1],
                -  G_i[-1] * s[1]
            ]
            gamma = G1().base_point() * s[2]
            for i in range(5):
                gamma += beta[i] # TODO: weights
            return (beta, gamma)
    
        def add_layer(N, beta, gamma, s):
            next_beta = [
                N + G_i[0] * s,
                gamma + G_i[1] * s,
                beta[0] + G_i[2] * s,
                beta[1] + G_i[3] * s,
                beta[2] + G_i[4] * s 
            ]
            next_gamma = G1().base_point() * s
            for i in range(5):
                next_gamma += next_beta[i] # TODO: weights
            return (next_beta, next_gamma)
            
        beta, gamma = initial_layer(destination, shared_secrets)                                 # Layer 3
        beta, gamma = add_layer(mixes[2], beta, gamma, shared_secrets[1])      # Layer 2
        beta, gamma = add_layer(mixes[1], beta, gamma, shared_secrets[0])      # Layer 1
        return beta, gamma