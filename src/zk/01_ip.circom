pragma circom 2.1.6;

include "circomlib/circuits/bitify.circom";
include "circomlib/circuits/comparators.circom";

// IPv4 range: 0 <= ip < 2^32.
template CheckIPv4() {
    signal input ip;
    component bits = Num2Bits(32);
    bits.in <== ip;
}

// Protype: Hardcoded blacklist of 5 IP addresses
// A fixed blacklist is part of the circuit, so changing it needs new keys.
template ExcludeFiveIPs() {
    signal input ip;
    var blacklist[5] = [1, 2, 3, 4, 5];
    component eq[5];
    for (var i = 0; i < 5; i++) {
        eq[i] = IsEqual();
        eq[i].in[0] <== ip;
        eq[i].in[1] <== blacklist[i];
        eq[i].out === 0;
    }
}
