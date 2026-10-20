package com.example.core;

/**
 * Deliberately modern syntax: text blocks are Java 15+ and javalang 0.13 does
 * not parse them. Expected to be skipped at M0.
 */
public final class TicketFormatter {

    public static String header() {
        return """
                TESTGEN TICKET
                """;
    }
}
