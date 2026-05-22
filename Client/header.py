
from dataclasses import dataclass
from typing import Any
from mclbn256 import Fr, G1, G2


@dataclass
class Header:
    alpha: G1
    beta: list[G1]
    gamma: G1
    credential: G1
    next_hop: G1 | None = None


    @classmethod
    def from_encoded(cls, message: list[Any]) -> "Header":
        alpha, *beta, gamma, credential = [G1().deserialize(m) for m in message]
        return cls(alpha=alpha, beta=beta, gamma=gamma, credential=credential)
    
    def encode(self):
        return [self.alpha.serialize(), self.beta[0].serialize(), self.beta[1].serialize(), self.beta[2].serialize(), 
        self.beta[3].serialize(), self.beta[4].serialize(), self.gamma.serialize(), self.credential.serialize()]

    @classmethod
    def build(cls, destination, mixes, shared_secrets, credential, alpha, G_i):
        beta, gamma = compute_layers(destination, mixes, shared_secrets, G_i)
        return cls(alpha=alpha, beta=beta, gamma=gamma, credential=credential)


def compute_layers(destination, mixes, shared_secrets, G_i):

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