package com.demo;

import com.demo.Calculator;
import org.junit.Assert;
import org.junit.Test;

public class Calculator_multiply_int_int_Test_Normal_14 {


    @Test
    public void testMultiplyWithRepresentativeValues() {
        Calculator calculator = new Calculator();

        int result1 = calculator.multiply(0, 0);
        Assert.assertEquals(0, result1);

        int result2 = calculator.multiply(1, 1);
        Assert.assertEquals(1, result2);

        int result3 = calculator.multiply(-1, 1);
        Assert.assertEquals(-1, result3);
    }

}
