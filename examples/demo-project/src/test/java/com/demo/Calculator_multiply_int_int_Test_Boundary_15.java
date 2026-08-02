package com.demo;

import com.demo.Calculator;
import org.junit.Assert;
import org.junit.Test;

public class Calculator_multiply_int_int_Test_Boundary_15 {

    @Test
    public void testMultiplyWithBoundaryValueZero() {
        Calculator calculator = new Calculator();
        int result = calculator.multiply(0, 5);
        Assert.assertEquals(0, result);
    }

}