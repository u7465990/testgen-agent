package com.example.core;

/**
 * Deliberately modern syntax. javalang 0.13 cannot parse records, so at M0
 * this whole file is expected to be reported as a parse failure.
 */
public record Money(long cents) {

    public Money plus(Money other) {
        return new Money(cents + other.cents);
    }

    public boolean isZero() {
        return cents == 0;
    }
}
