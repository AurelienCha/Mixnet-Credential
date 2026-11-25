pragma circom 2.1.6;

// For a checked 32-bit ip and index < 64, x < 2^253 < the field prime.
template CandidateX(index) {
    assert(index >= 0 && index < 64);
    signal input ip;
    signal output x;
    x <== ip * 2**221 + index;
}

// BabyJubJub: y^2 = (1 - 168700*x^2) / (1 - 168696*x^2).
// RHS = Right Hand Side of the BabyJubJub curve equation.
template BabyJubCandidateRHS() {
    signal input x;
    signal output rhs;
    signal xSquared;
    signal numerator;
    signal denominator;

    xSquared <== x*x;
    numerator <== 1 - 168700*xSquared;
    denominator <== 1 - 168696*xSquared;

    rhs <-- numerator/denominator;
    denominator*rhs === numerator;
}

// 5 is a quadratic nonresidue in the circuit's field used by Circom (i.e. there is no x such that x² = 5).
template ProveCandidateStatus() {
    signal input rhs;
    signal input valid;
    signal input root;
    signal input nonRoot;
    signal y;
    signal scaledRhs;
    signal inverseWhenInvalid;

    valid*(valid-1) === 0;
    // Keep unused witnesses zero for simpler debugging.
    (1-valid)*root === 0;
    valid*nonRoot === 0;

    y <== root + nonRoot; // Exactly one is active (root * nonRoot = 0). 
    // Check its square once, with the correct multiplier: 1 when valid, 5 when invalid.
    scaledRhs <== (5 - 4*valid)*rhs; 
    y*y === scaledRhs;

    // An invalid y must have rhs != 0; zero IS a square.
    inverseWhenInvalid <-- rhs == 0 ? 0 : (1-valid)/rhs;
    rhs*inverseWhenInvalid === 1-valid;
}
