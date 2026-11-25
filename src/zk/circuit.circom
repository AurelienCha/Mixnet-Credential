pragma circom 2.1.6;

include "01_ip.circom";
include "02_candidate.circom";
include "03_curve.circom";

// CIRCOM notations:
// x <-- expression | Assign witness value: Yes | Adds a proof constraint: No 
// x <== expression | Assign witness value: Yes | Adds a proof constraint: Yes 
// x === expression | Assign witness value: No | Adds a proof constraint: Yes 

/*
 * Main proof statement
 * --------------------
 * PRIVATE INPUTS (not in public declaration):
 *   ip           32-bit IPv4 integer.
 *   nonce        253-bit nonzero blinding scalar .
 *   valid[64]    per-candidate residue status y.
 *   root[64]     square roots for valid candidates, zero otherwise.
 *   nonRoot[64]  roots of 5*rhs for invalid candidates, zero otherwise.
 *
 * PUBLIC INPUTS:
 *   blindedX     x-coordinate of the blinded point.
 *   blindedY     y-coordinate of the blinded point.
 *
 * BLACKLIST: hardcoded [1,2,3,4,5].
 *
 * 1. Check ip range and blacklist exclusion.
 * 2. Generate candidate x-coordinates (ip * 2^221) + i, i=0..N-1
 * 3. Compute the right hand side (rhs) of the curve for the candidates 
 * 4. Evaluate if point on the curve (i.e. if valid candidate)
 * 5. Select the firstValid valid candidate.
 * 6. Require even y-coordinate for selected point.
 * 7. Check public blinded point = nonce * selected point.
 */

// Prove knowledge of an allowed IPv4 integer and a nonzero 253-bit scalar
// whose product with the first valid encoded point equals the public point.
template Main() {
    var N = 64;
    signal input ip;
    signal input nonce;
    signal input valid[N];
    signal input root[N];
    signal input nonRoot[N];
    signal input blindedX;
    signal input blindedY;

    // 1. Check ip range and blacklist exclusion.
    component range = CheckIPv4();
    range.ip <== ip;
    component blacklist = ExcludeFiveIPs();
    blacklist.ip <== ip;

    component candidate[N];
    component rhsCalc[N];
    component status[N];
    signal firstValid[N];
    signal notYetFound[N+1];
    notYetFound[0] <== 1;
    // Keep track of the firstValid valid candidate. Exactly one firstValid[i] is 1 because notYetFound[64]=0.
    // firstValid[i]=1 means i is the firstValid valid candidate.
    // notYetFound[i]=1 means every candidate BEFORE i was invalid.

    for (var i = 0; i < N; i++) {
        
        // 2. Generate candidate x-coordinates (ip * 2^221) + i, i=0..N-1
        // Multiply by 2^221 is a zero padding (left shift of 221 bits).
        // Each index i represents one try-and-increment attempt.
        candidate[i] = CandidateX(i);
        candidate[i].ip <== ip;

        // 3. Compute the right hand side (rhs) of the curve with this x-coordinate candidate 
        rhsCalc[i] = BabyJubCandidateRHS();
        rhsCalc[i].x <== candidate[i].x;

        // 4. Evaluate if point on the curve (i.e. if valid candidate)
        status[i] = ProveCandidateStatus();
        status[i].rhs <== rhsCalc[i].rhs;
        status[i].valid <== valid[i];
        status[i].root <== root[i];
        status[i].nonRoot <== nonRoot[i];

        firstValid[i] <== notYetFound[i]*valid[i];
        notYetFound[i+1] <== notYetFound[i]-firstValid[i];
    }
    notYetFound[N] === 0; // At least one of the N candidates should be valid.

    // 5. Select the firstValid valid candidate.
    // Accumulate the one selected coordinate pair.
    // Exactly one firstValid[i] is 1 because notYetFound[64]=0.
    signal selectedIndex[N+1];
    signal selectedY[N+1];
    selectedIndex[0] <== 0;
    selectedY[0] <== 0;
    for (var k = 0; k < N; k++) {
        selectedIndex[k+1] <== selectedIndex[k] + k*firstValid[k]; // [0, 0, ..., k, k, ..., k]
        selectedY[k+1] <== selectedY[k] + firstValid[k]*root[k]; // [0, 0, ..., y_k, y_k, ..., y_k]
    }
    signal selectedX; // Selected point is saved at the last index: (selectedX[N], selectedY[N])
    selectedX <== ip * 2**221 + selectedIndex[N];

    // 6. Require even y-coordinate for selected point.
    component yBits = Num2Bits_strict();
    yBits.in <== selectedY[N];
    yBits.out[0] === 0; // Deterministic sign: choose the EVEN canonical integer y (first bit at 0).

    // 7. Check public blinded point = nonce * selected point.
    component blind = BlindedScalarMultiplication(253);
    blind.baseX <== selectedX;
    blind.baseY <== selectedY[N];
    blind.nonce <== nonce;
    blind.x === blindedX;
    blind.y === blindedY;
}

component main {public [blindedX, blindedY]} = Main();
