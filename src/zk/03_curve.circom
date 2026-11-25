pragma circom 2.1.6;

include "circomlib/circuits/bitify.circom";
include "circomlib/circuits/babyjub.circom";

/*
 * EdwardsAdd
 * ----------
 * INPUT (x1,y1): first BabyJubJub point.
 * INPUT (x2,y2): second BabyJubJub point.
 * OUTPUT (x3,y3): sum of those points.
 *
 * Relies on circom lib for BabyJub curve's point addition
 */template EdwardsAdd() {
    signal input x1;
    signal input y1;
    signal input x2;
    signal input y2;
    signal output x3;
    signal output y3;
    component add = BabyAdd();
    add.x1 <== x1;
    add.y1 <== y1;
    add.x2 <== x2;
    add.y2 <== y2;
    x3 <== add.xout;
    y3 <== add.yout;
}

// Perform a BabyJub scalar multiplication with a nonce of nBits bits
template BlindedScalarMultiplication(nBits) {
    assert(nBits > 0 && nBits <= 253);
    signal input baseX;
    signal input baseY;
    signal input nonce;
    signal output x;
    signal output y;

    component bits = Num2Bits(nBits);
    bits.in <== nonce;
    signal nonceInverse;
    nonceInverse <-- nonce == 0 ? 0 : 1/nonce;
    nonce*nonceInverse === 1;

    signal accX[nBits+1];
    signal accY[nBits+1];
    signal powX[nBits];
    signal powY[nBits];
    accX[0] <== 0;
    accY[0] <== 1;
    powX[0] <== baseX;
    powY[0] <== baseY;

    component sum[nBits];
    component dbl[nBits-1];
    for (var j = 0; j < nBits; j++) {
        sum[j] = EdwardsAdd();
        sum[j].x1 <== accX[j];
        sum[j].y1 <== accY[j];
        sum[j].x2 <== powX[j];
        sum[j].y2 <== powY[j];
        accX[j+1] <== accX[j] + bits.out[j]*(sum[j].x3-accX[j]);
        accY[j+1] <== accY[j] + bits.out[j]*(sum[j].y3-accY[j]);

        // The final doubled point would never be used.
        if (j < nBits-1) {
            dbl[j] = EdwardsAdd();
            dbl[j].x1 <== powX[j];
            dbl[j].y1 <== powY[j];
            dbl[j].x2 <== powX[j];
            dbl[j].y2 <== powY[j];
            powX[j+1] <== dbl[j].x3;
            powY[j+1] <== dbl[j].y3;
        }
    }
    x <== accX[nBits];
    y <== accY[nBits];
}
