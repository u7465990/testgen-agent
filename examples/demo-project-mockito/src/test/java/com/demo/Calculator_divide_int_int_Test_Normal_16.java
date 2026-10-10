package com.demo;

import com.demo.Calculator;
import org.junit.Assert;
import org.junit.Test;

public class Calculator_divide_int_int_Test_Normal_16 {


    @Test
    public void testDivideWithValidInputs() {
        Calculator calculator = new Calculator();

        int result1 = calculator.divide(6, 2);
        Assert.assertEquals(3, result1);

        int result2 = calculator.divide(1, 1);
        Assert.assertEquals(1, result2);

        int result3 = calculator.divide(-1, 1);
        Assert.assertEquals(-1, result3);

        int result4 = calculator.divide(0, 1);
        Assert.assertEquals(0, result4);

        int result5 = calculator.divide(1, -1);
        Assert.assertEquals(-1, result5);

        int result6 = calculator.divide(-6, -2);
        Assert.assertEquals(3, result6);
    }

}
