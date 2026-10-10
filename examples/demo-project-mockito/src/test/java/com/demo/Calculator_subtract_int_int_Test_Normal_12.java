package com.demo;

import com.demo.Calculator;
import org.junit.Assert;
import org.junit.Test;

public class Calculator_subtract_int_int_Test_Normal_12 {


    @Test
    public void testSubtractWithTypicalValues() {
        Calculator calculator = new Calculator();

        int result1 = calculator.subtract(1, 1);
        Assert.assertEquals(0, result1);

        int result2 = calculator.subtract(1, 0);
        Assert.assertEquals(1, result2);

        int result3 = calculator.subtract(0, 1);
        Assert.assertEquals(-1, result3);

        int result4 = calculator.subtract(0, 0);
        Assert.assertEquals(0, result4);

        int result5 = calculator.subtract(-1, -1);
        Assert.assertEquals(0, result5);

        int result6 = calculator.subtract(-1, 1);
        Assert.assertEquals(-2, result6);

        int result7 = calculator.subtract(1, -1);
        Assert.assertEquals(2, result7);
    }

}
