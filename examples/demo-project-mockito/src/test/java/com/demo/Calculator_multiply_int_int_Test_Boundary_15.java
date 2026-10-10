package com.demo;

import com.demo.Calculator;
import org.junit.Assert;
import org.junit.Test;

public class Calculator_multiply_int_int_Test_Boundary_15 {


    @Test
    public void testMultiplyWithZeroFirstParameter() {
        Calculator calculator = new Calculator();
        int a = 0;
        int b = 5;
        int expected = 0;
        int actual = calculator.multiply(a, b);
        Assert.assertEquals(expected, actual);
    }

}
