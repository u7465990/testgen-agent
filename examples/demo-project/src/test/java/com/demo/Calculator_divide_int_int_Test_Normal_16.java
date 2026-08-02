package com.demo;

import com.demo.Calculator;
import org.junit.Assert;
import org.junit.Test;

public class Calculator_divide_int_int_Test_Normal_16 {


    @Test
    public void divide_typicalValues_returnsQuotient() {
        Calculator calculator = new Calculator();

        Assert.assertEquals(0, calculator.divide(0, 1));
        Assert.assertEquals(0, calculator.divide(0, -1));
        Assert.assertEquals(1, calculator.divide(1, 1));
        Assert.assertEquals(-1, calculator.divide(1, -1));
        Assert.assertEquals(-1, calculator.divide(-1, 1));
        Assert.assertEquals(1, calculator.divide(-1, -1));
    }

}
