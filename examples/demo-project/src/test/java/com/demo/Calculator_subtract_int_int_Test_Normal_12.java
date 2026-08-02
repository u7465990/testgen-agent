package com.demo;

import com.demo.Calculator;
import org.junit.Assert;
import org.junit.Test;

public class Calculator_subtract_int_int_Test_Normal_12 {

    @Test
    public void testSubtractNormal() {
        Calculator calculator = new Calculator();

        Assert.assertEquals(0, calculator.subtract(0, 0));
        Assert.assertEquals(1, calculator.subtract(1, 0));
        Assert.assertEquals(-1, calculator.subtract(0, 1));
        Assert.assertEquals(-1, calculator.subtract(-1, 0));
        Assert.assertEquals(1, calculator.subtract(0, -1));
        Assert.assertEquals(2, calculator.subtract(1, -1));
        Assert.assertEquals(-2, calculator.subtract(-1, 1));
    }
}