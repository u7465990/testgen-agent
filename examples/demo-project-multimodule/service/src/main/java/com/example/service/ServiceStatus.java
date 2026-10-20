package com.example.service;

/**
 * Another modern-syntax file, this time in the service module: it proves the
 * M0 skipped-file report attributes a failure to the right module.
 */
public final class ServiceStatus {

    public static String describe(int code) {
        return switch (code) {
            case 200 -> "ok";
            case 404 -> "missing";
            default -> "error";
        };
    }
}
