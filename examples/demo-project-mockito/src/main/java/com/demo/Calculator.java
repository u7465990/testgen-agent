package com.demo;

/** Simple arithmetic calculator with boundary and exception behavior. */
public class Calculator {

    public int add(int a, int b) {
        return a + b;
    }

    public int subtract(int a, int b) {
        return a - b;
    }

    public int multiply(int a, int b) {
        return a * b;
    }

    public int divide(int a, int b) {
        if (b == 0) {
            throw new IllegalArgumentException("Cannot divide by zero");
        }
        return a / b;
    }

    public int max(int a, int b) {
        return a >= b ? a : b;
    }

    public int min(int a, int b) {
        return a <= b ? a : b;
    }

    public int abs(int a) {
        return a < 0 ? -a : a;
    }
}
