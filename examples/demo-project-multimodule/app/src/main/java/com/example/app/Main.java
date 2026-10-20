package com.example.app;

import com.example.core.MathUtil;

public final class Main {

    public static String describe(boolean charged) {
        if (charged) {
            return "charged";
        }
        return "declined";
    }

    public static int clamped(int value) {
        return MathUtil.clamp(value, 0, 100);
    }
}
