package com.demo;

import com.demo.Calculator;
import org.junit.Assert;
import org.junit.Test;

public class Calculator_min_int_int_Test_Normal_20 {


    @Test
    public void testMinWithRepresentativeValues() {
        Calculator calculator = new Calculator();

        // a = 0, b = 1 -> 0
        Assert.assertEquals(0, calculator.min(0, 1));

        // a = 1, b = 0 -> 0
        Assert.assertEquals(0, calculator.min(1, 0));

        // a = -1, b = 0 -> -1
        Assert.assertEquals(-1, calculator.min(-1, 0));

        // a = 0, b = -1 -> -1
        Assert.assertEquals(-1, calculator.min(0, -1));

        // a = 1, b = -1 -> -1
        Assert.assertEquals(-1, calculator.min(1, -1));

        // a = -1, b = 1 -> -1
        Assert.assertEquals(-1, calculator.min(-1, 1));

        // equal values -> a (both equal)
        Assert.assertEquals(0, calculator.min(0, 0));
        Assert.assertEquals(1, calculator.min(1, 1));
        Assert.assertEquals(-1, calculator.min(-1, -1));
    }

}
