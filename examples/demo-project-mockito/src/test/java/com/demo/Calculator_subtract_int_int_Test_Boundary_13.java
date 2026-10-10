package com.demo;

import com.demo.Calculator;
import org.junit.Assert;
import org.junit.Test;

public class Calculator_subtract_int_int_Test_Boundary_13 {


    @Test
    public void testSubtractWithZeroAsFirstParameter() {
        Calculator calculator = new Calculator();
        int a = 0;
        int b = 5;
        int expected = -5;

        int actual = calculator.subtract(a, b);

        Assert.assertEquals(expected, actual);
    }

}
