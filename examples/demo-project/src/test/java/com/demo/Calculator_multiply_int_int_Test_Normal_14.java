package com.demo;

import com.demo.Calculator;
import org.junit.Assert;
import org.junit.Test;

public class Calculator_multiply_int_int_Test_Normal_14 {


    @Test
    public void testMultiplyWithRepresentativeInputs() {
        Calculator calculator = new Calculator();

        Assert.assertEquals(0, calculator.multiply(0, 0));
        Assert.assertEquals(0, calculator.multiply(0, 1));
        Assert.assertEquals(0, calculator.multiply(1, 0));
        Assert.assertEquals(1, calculator.multiply(1, 1));
        Assert.assertEquals(-1, calculator.multiply(-1, 1));
        Assert.assertEquals(-1, calculator.multiply(1, -1));
        Assert.assertEquals(1, calculator.multiply(-1, -1));
        Assert.assertEquals(6, calculator.multiply(2, 3));
    }

}