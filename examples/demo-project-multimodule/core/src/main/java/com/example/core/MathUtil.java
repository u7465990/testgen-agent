package com.example.core;

public final class MathUtil {

    public static int clamp(int value, int min, int max) {
        if (min > max) {
            throw new IllegalArgumentException("min > max");
        }
        if (value < min) {
            return min;
        }
        if (value > max) {
            return max;
        }
        return value;
    }

    public static long sum(int[] values) {
        long total = 0;
        for (int value : values) {
            total += value;
        }
        return total;
    }
}
