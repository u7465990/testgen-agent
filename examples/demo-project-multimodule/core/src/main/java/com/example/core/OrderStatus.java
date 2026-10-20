package com.example.core;

/**
 * Deliberately modern syntax: the switch expression is Java 14+ and javalang
 * 0.13 does not parse it. Expected to appear in the M0 skipped-file list.
 */
public enum OrderStatus {
    NEW,
    PAID,
    SHIPPED,
    CANCELLED;

    public String label() {
        return switch (this) {
            case NEW -> "new";
            case PAID -> "paid";
            case SHIPPED -> "shipped";
            case CANCELLED -> "cancelled";
        };
    }
}
