package com.example.core;

/**
 * Deliberately modern syntax: pattern matching for instanceof is Java 16+ and
 * javalang 0.13 does not parse it. Expected to be skipped at M0.
 */
public final class TypeChecks {

    public static boolean isLongText(Object value) {
        return value instanceof String text && text.length() > 10;
    }
}
