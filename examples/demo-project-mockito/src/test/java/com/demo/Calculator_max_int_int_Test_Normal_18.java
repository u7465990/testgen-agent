package com.demo;

import com.demo.Calculator;
import org.junit.Test;
import org.junit.Assert;

public class Calculator_max_int_int_Test_Normal_18 {


    @Test
    public void testMaxWithTypicalValues() {
        Calculator calculator = new Calculator();

        Assert.assertEquals(1, calculator.max(0, 1));
        Assert.assertEquals(0, calculator.max(0, -1));
        Assert.assertEquals(1, calculator.max(1, 0));
        Assert.assertEquals(0, calculator.max(-1, 0));
        Assert.assertEquals(1, calculator.max(1, -1));
        Assert.assertEquals(-1, calculator.max(-1, -1));
        Assert.assertEquals(0, calculator.max(0, 0));
    }

}
