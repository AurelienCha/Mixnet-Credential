from mclbn256 import Fr, G1, G2
import secrets, hashlib
################################################################
##########
## FROM ##
##########
def from_G1(self, other=None):
    return Fr(int(hashlib.sha256(self.serialize()).hexdigest(), 16) >> 3)
G1.__rshift__ = from_G1
def from_G2(self, other=None):
    return Fr(int(hashlib.sha256(self.serialize()).hexdigest(), 16) >> 3)
G2.__rshift__ = from_G2
def from_Fr(self, other):
    return other.mapfrom(self)
Fr.__rshift__ = from_Fr

# 253 bits (not 256, because BN uses a prime of 254 bits)
def encode_ip(ip): 
    a, b, c, d = map(int, ip.split('.'))
    ip = (a << 24) | (b << 16) | (c << 8) | d
    return G1().mapfrom(Fr((ip << (221))))# + secrets.randbits(221))) # padding: 221 = (256 - 3) - 32 # TODO

def decode_ip(G): # IP-Point to IPv6
    n = int(G.tostr().split()[1].decode(), 16) >> 221 # unpadding
    return f"{(n>>24)&255}.{(n>>16)&255}.{(n>>8)&255}.{n&255}"
#################################################################

class Header:

    def __init__(self, generators, message=None):
        self.G_i = generators
        if message is not None:
            self.decode(message)
    
    def __repr__(self):
        return f"""
            alpha = {self.alpha}
            beta = {self.beta[0]}
                   {self.beta[1]}
                   {self.beta[2]}
                   {self.beta[3]}
                   {self.beta[4]}
            gamma = {self.gamma}
            cred = {self.credential}
        """
    
    def encode(self):
        return [self.alpha] + self.beta + [self.gamma, self.credential]

    def decode(self, message): # TODO
        self.alpha, *self.beta, self.gamma, self.credential = message
    
    def build(self, destination, mixes, shared_secrets, credential, alpha):
        # self.next_hop = inverse_map(mixes[0]) # ip        
        self.alpha = alpha                 # G1
        self.credential = credential       # G1
        self.beta, self.gamma = self._compute_layers(destination, mixes, shared_secrets)

    def _compute_layers(self, destination, mixes, shared_secrets):

        def initial_layer(destination, s): 
            beta = [
                destination + self.G_i[0] * s[2],
                - (self.G_i[-4] * s[1] + self.G_i[-2] * s[0]),
                - (self.G_i[-3] * s[1] + self.G_i[-1] * s[0]),
                -  self.G_i[-2] * s[1],
                -  self.G_i[-1] * s[1]
            ]
            gamma = G1().base_point() * s[2]
            for i in range(5):
                gamma += beta[i] # TODO: weights
            return (beta, gamma)
    
        def add_layer(N, beta, gamma, s):
            next_beta = [
                N + self.G_i[0] * s,
                gamma + self.G_i[1] * s,
                beta[0] + self.G_i[2] * s,
                beta[1] + self.G_i[3] * s,
                beta[2] + self.G_i[4] * s 
            ]
            next_gamma = G1().base_point() * s
            for i in range(5):
                next_gamma += next_beta[i] # TODO: weights
            return (next_beta, next_gamma)
            
        beta, gamma = initial_layer(destination, shared_secrets)                                 # Layer 3
        beta, gamma = add_layer(mixes[2], beta, gamma, shared_secrets[1])      # Layer 2
        beta, gamma = add_layer(mixes[1], beta, gamma, shared_secrets[0])      # Layer 1
        return beta, gamma

    def verify_credential(self, authority_PK):
        X = self.beta[0] + self.beta[2] + self.beta[4]
        print("X:", X)
        print()
        print("PK:", authority_PK)
        print("C:", self.credential)
        assert (X @ authority_PK) == (self.credential @ G2().base_point())

    def compute_shared_secret(self, sk):
        return (self.alpha * sk) >> Fr()

    def verify_integrity(self, s):
        Gamma = G1().base_point() * s
        for i in range(5):
            Gamma += self.beta[i]
        assert self.gamma == Gamma

    def decrypt_beta(self, s):
        beta = self.beta + [G1().clear(), G1().clear()]
        for i in range(len(beta)):                       
            beta[i] = beta[i] - self.G_i[i] * s
        self.next_hop, self.gamma, *self.beta = beta
        # self.next_hop = inverse_map(next_hop)

    def update_alpha(self, s):
        self.alpha =  self.alpha * s

    def update_credential(self, s, sign_gen_sum, mixnodes):
        sign_next_hop = next((node["sign_PK"] for node in mixnodes.values() if node["PK"] == str(self.next_hop)), None)
        if sign_next_hop is None:
            print("FINAL DESTINATION", self.next_hop)
            #self.credential = G1() # TODO (default val to not crash)
        else:
            try:
                print("s_G", sign_gen_sum)
                self.credential = self.credential - sign_gen_sum * s - G1().fromstr(sign_next_hop.encode())
            except KeyError:
                print("Key error: ignore if last iteration of the loop")
